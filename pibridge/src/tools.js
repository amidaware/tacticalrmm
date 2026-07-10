import { defineTool } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { trmm } from "./trmm.js";

// Builds the device-scoped toolset.
//
// Single-machine mode (machines.length === 1): identical behavior/shape to the
// original implementation - tools are hard-bound to the one agentId and have
// NO `machine` parameter.
//
// Multi-machine mode (machines.length > 1): every device-facing tool gains a
// REQUIRED `machine` parameter (the hostname label shown in the system prompt)
// so the model explicitly targets one of the session's machines per call. The
// model can never reach a machine outside the session's set.
//
// Mutating tools go through `gate(summary)` which resolves to true (approved)
// or false (denied).
export function buildTools({
  machines: machinesIn,
  // legacy single-machine call shape
  agentId,
  plat,
  gate,
  includeReport = false,
  readonly = false,
}) {
  const machines = (machinesIn && machinesIn.length
    ? machinesIn
    : [{ agentId, hostname: "", plat, role: "" }]
  ).map((m) => ({
    agentId: m.agentId,
    hostname: m.hostname || "",
    plat: m.plat,
    role: m.role || "",
  }));
  const multi = machines.length > 1;

  // Unique label per machine (hostname, deduped with #N when two machines
  // share a hostname). These labels are what the model passes as `machine`.
  const seen = new Map();
  for (const m of machines) {
    const base = (m.hostname || m.agentId).trim();
    const n = (seen.get(base.toLowerCase()) || 0) + 1;
    seen.set(base.toLowerCase(), n);
    m.label = n === 1 ? base : `${base}#${n}`;
  }
  const byLabel = new Map(machines.map((m) => [m.label.toLowerCase(), m]));
  const byAgentId = new Map(machines.map((m) => [m.agentId, m]));
  const labels = machines.map((m) => m.label);

  const anyWindows = machines.some((m) => m.plat === "windows");
  const allWindows = machines.every((m) => m.plat === "windows");
  const isWindows = machines[0].plat === "windows"; // single-machine semantics

  const verdict = { status: null, summary: "", details: "" };

  const text = (s) => ({ content: [{ type: "text", text: s }], details: {} });
  const denied = () =>
    text("The operator DENIED this action. Do not retry it; ask what to do instead.");

  // Resolve the `machine` param to a machine entry, or throw a model-friendly error.
  function target(p) {
    if (!multi) return machines[0];
    const raw = String(p.machine || "").trim();
    const m = byLabel.get(raw.toLowerCase()) || byAgentId.get(raw);
    if (!m) {
      throw new Error(
        `Unknown machine '${raw}'. Valid machines in this session: ${labels.join(", ")}`,
      );
    }
    return m;
  }

  // Prefix approval summaries with the target hostname in multi mode.
  const gateFor = (m, summary) => gate(multi ? `[${m.label}] ${summary}` : summary);

  // Adds the required `machine` param in multi mode.
  function params(shape = {}) {
    if (!multi) return Type.Object(shape);
    return Type.Object({
      machine: Type.String({
        description: `Target machine for this call. One of: ${labels.join(", ")}`,
      }),
      ...shape,
    });
  }

  const forThis = multi ? "the TARGETED machine" : "THIS device";

  const get_device_details = defineTool({
    name: "get_device_details",
    label: "Get device details",
    description: `Get full details about ${forThis} (hardware, OS, disks, IPs, checks status, custom fields).`,
    parameters: params({}),
    execute: async (_id, p, signal) => {
      const a = await trmm.getAgent(target(p).agentId, { signal });
      return text(JSON.stringify(a, null, 2));
    },
  });

  const winShellNote = [
    "On Windows machines each call is a FRESH, non-interactive shell (cmd or powershell);",
    "combine steps with ';' (powershell) or '&' (cmd).",
  ].join(" ");
  const nixShellNote = [
    "On Linux/Unix machines each call is a FRESH, non-interactive /bin/bash shell (usually root);",
    "chain steps with ';' or '&&', use 'cd /path && ...', multi-line scripts and heredocs are fine, add 2>&1 to capture errors.",
  ].join(" ");
  const shellDescription = multi
    ? [
        "Run a command on ONE of this session's machines (pick it with the required 'machine' parameter).",
        "Working directory and environment are NOT preserved between calls.",
        allWindows ? winShellNote : anyWindows ? `${winShellNote} ${nixShellNote}` : nixShellNote,
      ].join(" ")
    : isWindows
      ? [
          "Run a command on THIS Windows device. Each call is a FRESH, non-interactive shell",
          "(cmd or powershell) - working directory and environment are NOT preserved between calls.",
          "Combine multiple steps in one call. For powershell use ';' between statements; for cmd use '&'.",
          "You can send multi-line scripts. Prefer powershell for anything non-trivial.",
        ].join(" ")
      : [
          "Run a command on THIS device in a FRESH, non-interactive /bin/bash shell (runs as the",
          "agent's service account, typically root). Working directory and environment are NOT",
          "preserved between calls, so treat each call as a standalone script: chain steps with",
          "';' or '&&', use 'cd /path && ...' when you need a directory, and you may send full",
          "multi-line scripts or heredocs. Redirect stderr with 2>&1 when you want to see errors.",
        ].join(" ");

  const run_command_on_device = defineTool({
    name: "run_command_on_device",
    label: "Run command on device",
    description: shellDescription,
    parameters: params({
      command: Type.String({
        description:
          "The full command or script to execute. May contain pipes, redirects, multiple" +
          " statements, and multiple lines.",
      }),
      shell: Type.Optional(
        Type.String({
          description: anyWindows
            ? "'cmd' or 'powershell' (default powershell); ignored on non-Windows machines"
            : "ignored on this platform (always /bin/bash)",
        }),
      ),
      run_as_user: Type.Optional(
        Type.Boolean({
          description:
            "Run as the currently logged-in interactive user instead of the service account" +
            " (default false). Only works when a user is logged in.",
        }),
      ),
      timeout: Type.Optional(
        Type.Number({ description: "Max seconds to wait (default 60, max 900)" }),
      ),
    }),
    execute: async (_id, p, signal) => {
      const m = target(p);
      const win = m.plat === "windows";
      const shell = win ? (p.shell === "cmd" ? "cmd" : "powershell") : "/bin/bash";
      const timeout = p.timeout && p.timeout > 0 ? Math.min(p.timeout, 900) : 60;
      const ok = await gateFor(m, `Run on device [${shell}]: ${p.command}`);
      if (!ok) return denied();
      // On Linux, self-terminate the command with `timeout` so a hung command
      // (e.g. a stuck Proxmox `qm list`/pmxcfs) returns promptly with partial
      // output instead of blocking the whole chat until the transport timeout.
      let cmd = p.command;
      if (!win) {
        const q = "'" + p.command.replace(/'/g, "'\\''") + "'";
        const note =
          `[pi] command did not finish within ${timeout}s and was terminated (partial output above; the command or the device is hung)`;
        cmd =
          `timeout --preserve-status --signal=TERM -k 5 ${timeout}s /bin/bash -c ${q}; ` +
          `__ec=$?; if [ $__ec -eq 124 ] || [ $__ec -eq 143 ]; then echo ${"'" + note + "'"}; fi`;
      }
      const out = await trmm.sendCmd(
        m.agentId,
        {
          shell,
          cmd,
          timeout: timeout + 10,
          runAsUser: !!p.run_as_user,
        },
        { signal },
      );
      const s = typeof out === "string" ? out : JSON.stringify(out);
      return text(s.length ? s : "(command produced no output; exit assumed success)");
    },
  });

  const list_scripts = defineTool({
    name: "list_scripts",
    label: "List scripts",
    description: "List scripts available in the TRMM script library (id, name, shell, description).",
    parameters: Type.Object({}),
    execute: async (_id, _p, signal) => {
      const scripts = await trmm.listScripts({ signal });
      const slim = (Array.isArray(scripts) ? scripts : []).map((s) => ({
        id: s.id,
        name: s.name,
        shell: s.shell,
        description: s.description,
      }));
      return text(JSON.stringify(slim, null, 2));
    },
  });

  const run_script_on_device = defineTool({
    name: "run_script_on_device",
    label: "Run library script on device",
    description: `Run a saved TRMM library script on ${forThis} by its numeric script id (use list_scripts first).`,
    parameters: params({
      script_id: Type.Number({ description: "Numeric id of the library script" }),
      args: Type.Optional(Type.Array(Type.String(), { description: "Script arguments" })),
      timeout: Type.Optional(Type.Number({ description: "Seconds (default 90)" })),
    }),
    execute: async (_id, p, signal) => {
      const m = target(p);
      const timeout = p.timeout && p.timeout > 0 ? Math.min(p.timeout, 900) : 90;
      const ok = await gateFor(m, `Run library script #${p.script_id} on device`);
      if (!ok) return denied();
      const out = await trmm.runScript(
        m.agentId,
        {
          script: p.script_id,
          args: p.args || [],
          timeout,
          output: "wait",
        },
        { signal },
      );
      return text(typeof out === "string" ? out : JSON.stringify(out));
    },
  });

  const list_processes = defineTool({
    name: "list_processes",
    label: "List processes",
    description: `List running processes on ${forThis}.`,
    parameters: params({}),
    execute: async (_id, p, signal) => {
      const procs = await trmm.listProcesses(target(p).agentId, { signal });
      return text(JSON.stringify(procs, null, 2));
    },
  });

  const kill_process = defineTool({
    name: "kill_process",
    label: "Kill process",
    description: `Kill a process on ${forThis} by PID.`,
    parameters: params({ pid: Type.Number({ description: "Process id to kill" }) }),
    execute: async (_id, p, signal) => {
      const m = target(p);
      const ok = await gateFor(m, `Kill process PID ${p.pid} on device`);
      if (!ok) return denied();
      const out = await trmm.killProcess(m.agentId, p.pid, { signal });
      return text(typeof out === "string" ? out : JSON.stringify(out));
    },
  });

  const get_event_logs = defineTool({
    name: "get_event_logs",
    label: "Get Windows event logs",
    description: multi
      ? "Get Windows event logs from a Windows machine in this session."
      : "Get Windows event logs from THIS device.",
    parameters: params({
      log_type: Type.String({ description: "Application, System, or Security" }),
      days: Type.Optional(Type.Number({ description: "How many days back (default 1)" })),
    }),
    execute: async (_id, p, signal) => {
      const m = target(p);
      if (m.plat !== "windows") {
        throw new Error(`${m.label} is not a Windows machine; event logs are Windows-only.`);
      }
      const out = await trmm.eventLog(m.agentId, p.log_type, p.days && p.days > 0 ? p.days : 1, { signal });
      return text(JSON.stringify(out, null, 2));
    },
  });

  const list_software = defineTool({
    name: "list_software",
    label: "List installed software",
    description: `List installed software on ${forThis}.`,
    parameters: params({}),
    execute: async (_id, p, signal) =>
      text(JSON.stringify(await trmm.listSoftware(target(p).agentId, { signal }), null, 2)),
  });

  const get_checks = defineTool({
    name: "get_checks",
    label: "Get checks",
    description: `Get monitoring checks and their status for ${forThis}.`,
    parameters: params({}),
    execute: async (_id, p, signal) =>
      text(JSON.stringify(await trmm.getChecks(target(p).agentId, { signal }), null, 2)),
  });

  const get_tasks = defineTool({
    name: "get_tasks",
    label: "Get automated tasks",
    description: `Get automated tasks for ${forThis}.`,
    parameters: params({}),
    execute: async (_id, p, signal) =>
      text(JSON.stringify(await trmm.getTasks(target(p).agentId, { signal }), null, 2)),
  });

  const reboot_device = defineTool({
    name: "reboot_device",
    label: "Reboot device",
    description: multi ? "Reboot the targeted machine now." : "Reboot THIS device now.",
    parameters: params({}),
    execute: async (_id, p, signal) => {
      const m = target(p);
      const ok = await gateFor(m, `REBOOT the device now`);
      if (!ok) return denied();
      const out = await trmm.reboot(m.agentId, { signal });
      return text(typeof out === "string" ? out : JSON.stringify(out));
    },
  });

  const send_email = defineTool({
    name: "send_email",
    label: "Send email",
    description:
      "Send a plain-text email through the RMM server's configured SMTP (the same" +
      " mail settings Tactical RMM uses for alerts). Use this when the operator asks" +
      " for results, findings, or alerts to be emailed (e.g. to alerts@ or support@)." +
      " Write a clear subject and put the full findings in the body. Only send email" +
      " when the operator/task instructions ask for it.",
    parameters: Type.Object({
      to: Type.String({
        description:
          "Recipient email address(es), comma-separated for multiple" +
          " (e.g. 'alerts@example.com' or 'alerts@example.com, support@example.com')",
      }),
      subject: Type.String({ description: "Email subject line" }),
      body: Type.String({ description: "Plain-text email body with the full details" }),
    }),
    execute: async (_id, p, signal) => {
      const ok = await gate(`Send email to ${p.to}: "${p.subject}"`);
      if (!ok) return denied();
      const out = await trmm.sendEmail(
        { to: p.to, subject: p.subject, body: p.body },
        { signal },
      );
      return text(typeof out === "string" ? out : JSON.stringify(out));
    },
  });

  // For scheduled/unattended runs: a tool the AI calls once to report its verdict.
  const report_result = defineTool({
    name: "report_result",
    label: "Report result",
    description:
      "Call this EXACTLY ONCE at the very end to report your verdict for this scheduled" +
      " check. status='ok' when everything is healthy, 'warning' for minor/degraded issues," +
      " 'alert' for serious problems that need attention. summary is a one-line headline;" +
      " details is the supporting evidence.",
    parameters: Type.Object({
      status: Type.String({ description: "'ok' | 'warning' | 'alert'" }),
      summary: Type.String({ description: "One-line headline of the finding" }),
      details: Type.Optional(Type.String({ description: "Supporting details / evidence" })),
    }),
    execute: async (_id, p) => {
      const s = (p.status || "").toLowerCase();
      verdict.status = ["ok", "warning", "alert"].includes(s) ? s : "warning";
      verdict.summary = p.summary || "";
      verdict.details = p.details || "";
      return text("Result recorded.");
    },
  });

  let tools = [
    get_device_details,
    run_command_on_device,
    list_scripts,
    run_script_on_device,
    list_processes,
    kill_process,
    list_software,
    get_checks,
    get_tasks,
    reboot_device,
    send_email,
  ];
  if (anyWindows) tools.push(get_event_logs);

  if (readonly) {
    // unattended without mutation rights: keep diagnostics + run_command (admin-authored
    // prompt) but drop the destructive actions.
    const drop = new Set(["run_script_on_device", "kill_process", "reboot_device"]);
    tools = tools.filter((t) => !drop.has(t.name));
  }
  if (includeReport) tools.push(report_result);

  // Names that require approval when approval mode is on.
  const mutating = new Set([
    "run_command_on_device",
    "run_script_on_device",
    "kill_process",
    "reboot_device",
    "send_email",
  ]);

  return { tools, mutating, verdict, machines };
}
