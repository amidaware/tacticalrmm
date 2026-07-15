import { defineTool } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { trmm } from "./trmm.js";
import { loadHelpdesk } from "./helpdesk-runtime.js";

// Best-effort classification of a shell/powershell command as "mutating" (i.e.
// it changes the system) so a READ-ONLY session can refuse it. This is a
// guardrail, not a sandbox: arbitrary shell can be obfuscated. The hard
// guarantee for read-only sessions is at the TOOL level (write-only tools are
// removed); this adds a strong deterrent for run_command_on_device.
const NIX_MUTATE = [
  /\brm\b/, /\brmdir\b/, /\bunlink\b/, /\bshred\b/, /\bdd\b/, /\bmkfs\.?\w*/,
  /\bfdisk\b/, /\bparted\b/, /\bwipefs\b/, /\bmkswap\b/, /\btruncate\b/,
  /\bchmod\b/, /\bchown\b/, /\bchattr\b/, /\bsetfacl\b/,
  /\bmv\b/, /\bcp\b/, /\bln\b/, /\btee\b/,
  /\bsystemctl\s+(start|stop|restart|reload|enable|disable|mask|unmask|kill)/,
  /\bservice\s+\S+\s+(start|stop|restart|reload)/, /\binvoke-rc\.d\b/,
  /\b(apt|apt-get|aptitude|dpkg|yum|dnf|rpm|zypper|apk|snap|flatpak|pip|pip3|npm|yarn|gem|cargo)\b[^\n]*\b(install|remove|purge|erase|autoremove|upgrade|dist-upgrade|add|del|delete|uninstall)\b/,
  /\b(reboot|shutdown|halt|poweroff|telinit|init)\b/,
  /\b(kill|pkill|killall)\b/,
  /\b(useradd|userdel|usermod|groupadd|groupdel|passwd|chpasswd|adduser|deluser)\b/,
  /\bcrontab\b/, /\b(iptables|ip6tables|nft|ufw|firewall-cmd)\b/,
  /\b(mount|umount|swapon|swapoff)\b/,
  /\bsed\b[^|]*\s-\w*i/, /\bperl\b[^|]*\s-\w*i/,
  /\beval\b/, /\|\s*(sh|bash|zsh)\b/,
  /\b(qm|pct|pvesm|pveceph|ha-manager|pvecm)\s+(create|destroy|set|start|stop|delete|remove|add|migrate|rollback)/,
];
const WIN_MUTATE = [
  /\bRemove-\w+/i, /\bSet-\w+/i, /\bNew-\w+/i, /\bStop-\w+/i, /\bRestart-\w+/i,
  /\bSuspend-\w+/i, /\bStart-(Service|Process|ScheduledTask)\b/i,
  /\bDisable-\w+/i, /\bEnable-\w+/i, /\bClear-\w+/i, /\bRename-\w+/i,
  /\bMove-\w+/i, /\bCopy-Item\b/i, /\b(Install|Uninstall|Update|Register|Unregister)-\w+/i,
  /\b(Add|Set)-Content\b/i, /\bOut-File\b/i, /\bExport-\w+/i,
  /\bFormat-Volume\b/i, /\b(Restart|Stop)-Computer\b/i,
  /\b(del|erase|rd|rmdir|move|ren|rename|xcopy|robocopy|copy)\b/i,
  /\breg(\.exe)?\s+(add|delete|import)\b/i,
  /\bsc(\.exe)?\s+(create|config|delete|stop|start|failure)\b/i,
  /\bnet(\.exe)?\s+(stop|start|user|localgroup|group)\b/i,
  /\b(shutdown|bcdedit|diskpart|fsutil|takeown|icacls|cacls|attrib)\b/i,
  /\bformat\b(?!-)/i, /\bschtasks\b[^\n]*\/(create|delete|change)/i,
  /\bmsiexec\b/i, /\b(winget|choco)\s+(install|uninstall|upgrade|remove)\b/i,
];
function mutatingMatch(command, isWindows) {
  for (const re of isWindows ? WIN_MUTATE : NIX_MUTATE) {
    const m = command.match(re);
    if (m) return m[0];
  }
  return null;
}

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
  // Whether this session is allowed to write at all (role/super). When false the
  // write-only tools are removed entirely (hard read-only).
  mutateAllowed = true,
  // Live read-only state. Even when mutateAllowed, the operator can start (and
  // toggle) read-only; write tools + destructive run_command refuse while true.
  // Back-compat: callers may pass `readonly` (fixed) instead.
  readonly = undefined,
  isReadonly = undefined,
  jobRef = null,
  // Global-Settings-defined ticketing API: {base_url, api_key}. When set, the
  // generic helpdesk_api_request tool is exposed (and the legacy env-based
  // create_ticket is not). The admin HELPDESK POLICY prompt documents usage.
  helpdeskApi = null,
  helpdeskCode = "",
}) {
  if (readonly !== undefined && isReadonly === undefined) {
    // fixed read-only (headless): map onto the new model
    mutateAllowed = !readonly;
    isReadonly = () => readonly;
  }
  if (isReadonly === undefined) isReadonly = () => !mutateAllowed;
  const hardReadonly = !mutateAllowed;
  const machines = (machinesIn && machinesIn.length
    ? machinesIn
    : [{ agentId, hostname: "", plat, role: "" }]
  ).map((m) => ({
    agentId: m.agentId,
    hostname: m.hostname || "",
    plat: m.plat,
    role: m.role || "",
    // preserve device_facts so the helpdesk context (deviceUrl for the ticket
    // "jump to device" link, client/site) survives into hdContext below.
    facts: m.facts || null,
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
  const roDenied = () =>
    text(
      "This session is currently READ-ONLY, so this action is not allowed right now. " +
        (mutateAllowed
          ? "Tell the operator they can toggle write mode on to apply changes."
          : "An operator with write (mutate) rights must make changes."),
    );

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
      if (isReadonly()) {
        const hit = mutatingMatch(p.command, win);
        if (hit) {
          return text(
            `BLOCKED: this session is currently READ-ONLY, but the command appears to modify the system ` +
              `(matched "${hit}"). Only read-only/diagnostic commands are permitted right now. ` +
              `${mutateAllowed ? "The operator can enable write mode to apply changes." : "An operator with write (mutate) rights must make changes."}`,
          );
        }
      }
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
      if (isReadonly()) return roDenied();
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
      if (isReadonly()) return roDenied();
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
      if (isReadonly()) return roDenied();
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
      " when the operator/task instructions ask for it." +
      " The From address defaults to a unique job-associated address on the server's" +
      " mail domain; only set from_address if the operator explicitly wants a specific" +
      " sender.",
    parameters: Type.Object({
      to: Type.String({
        description:
          "Recipient email address(es), comma-separated for multiple" +
          " (e.g. 'alerts@example.com' or 'alerts@example.com, support@example.com')",
      }),
      subject: Type.String({ description: "Email subject line" }),
      body: Type.String({ description: "Plain-text email body with the full details" }),
      from_address: Type.Optional(
        Type.String({
          description:
            "Optional sender. A full address (with '@') is used as-is; a bare word" +
            " is used as the local part on the server's mail domain. Leave empty to" +
            " auto-generate a unique job-associated sender on the server's domain.",
        }),
      ),
      from_name: Type.Optional(
        Type.String({ description: "Optional sender display name" }),
      ),
    }),
    execute: async (_id, p, signal) => {
      const ok = await gate(`Send email to ${p.to}: "${p.subject}"`);
      if (!ok) return denied();
      const out = await trmm.sendEmail(
        {
          to: p.to,
          subject: p.subject,
          body: p.body,
          from_address: p.from_address,
          from_name: p.from_name,
          job_ref: jobRef,
        },
        { signal },
      );
      return text(typeof out === "string" ? out : JSON.stringify(out));
    },
  });

  // Deterministic, system-AGNOSTIC ticketing. The integration is defined by the
  // admin in Global Settings -> "Helpdesk Integration Code" (helpdesk.js), which
  // exports named operations (create_ticket, reply_to_ticket, add_note,
  // submit_report, resolve_customer, ...). This tool lets the model invoke those
  // operations by name; ALL API mechanics live in that code. The policy prompt
  // documents WHEN to use each operation and with what args.
  // Single-device sessions expose a deep link to the device so the integration
  // can put a "jump to device" link in the ticket (multi-device -> ambiguous, omit).
  const hdContext =
    machines.length === 1
      ? {
          deviceUrl: machines[0]?.facts?.device_url || "",
          hostname: machines[0]?.hostname || machines[0]?.facts?.hostname || "",
          client: machines[0]?.facts?.client || "",
          site: machines[0]?.facts?.site || "",
          agentId: machines[0]?.agentId || "",
        }
      : {};
  let hd = null, hdError = "";
  try { hd = loadHelpdesk(helpdeskCode, helpdeskApi, hdContext); }
  catch (e) { hdError = e.message; }
  const hdOps = hd ? hd.names : [];
  // Tracks whether a ticketing operation actually FAILED (API/exception), so the
  // headless caller can raise an RMM alert only in that (shouldn't-happen) case.
  const helpdeskState = { error: false, detail: "" };
  const opList = hdOps
    .map((n) => `  - ${n}${hd.meta[n] ? ": " + hd.meta[n] : ""}`)
    .join("\n");
  const helpdesk_call = defineTool({
    name: "helpdesk_call",
    label: "Helpdesk operation",
    description:
      "Perform a helpdesk/ticketing operation (create ticket, reply to the " +
      "customer, add an internal note, look up a customer, etc.). Exactly WHEN " +
      "and HOW to use each operation (and its args) is defined in the HELPDESK " +
      "POLICY in your instructions - follow it. Available operations:\n" +
      (opList || "  (none configured)"),
    parameters: Type.Object({
      operation: Type.String({ description: "Operation name (one listed above)" }),
      args: Type.Optional(
        Type.String({
          description:
            "JSON object of arguments for the operation, e.g. " +
            '{"ticket":"TICKET/123","message":"..."}',
        }),
      ),
      summary: Type.String({
        description: "One-line summary of what this does (shown to the operator for approval)",
      }),
    }),
    execute: async (_id, p) => {
      if (!hd)
        return text(
          `Helpdesk integration code is not configured or failed to load${hdError ? ": " + hdError : ""}.`,
        );
      const op = String(p.operation || "").trim();
      if (!hd.operations[op])
        return text(`Unknown helpdesk operation "${op}". Available: ${hdOps.join(", ")}.`);
      let args = {};
      if (p.args) {
        try { args = JSON.parse(p.args); }
        catch (e) { return text(`args must be valid JSON: ${e.message}`); }
      }
      if (hd.mutating.has(op)) {
        const ok = await gate(`Helpdesk: ${p.summary || op}`);
        if (!ok) return denied();
      }
      try {
        const result = await hd.operations[op](args);
        let out = typeof result === "string" ? result : JSON.stringify(result, null, 2);
        if (hd.apiKey) out = out.split(hd.apiKey).join("***");
        return text(out || "(done)");
      } catch (e) {
        let msg = e && e.message ? e.message : String(e);
        if (hd.apiKey) msg = msg.split(hd.apiKey).join("***");
        helpdeskState.error = true; helpdeskState.detail = `${op}: ${msg}`;
        return text(`Helpdesk operation "${op}" failed: ${msg}`);
      }
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

  // Durable per-device memory. NOT gated and allowed in read-only mode: it writes
  // to the device's Pi.dev memory in RMM, never to the device itself.
  const save_device_note = defineTool({
    name: "save_device_note",
    label: "Save device note",
    description:
      "Save a durable note about " + forThis + " to its Pi.dev memory so FUTURE " +
      "Pi runs start with this context. Record ONLY stable, reusable facts that make " +
      "future work faster: the device's role/purpose, key install paths, service/" +
      "container names, disk/volume layout, where credentials live (NOT the secrets " +
      "themselves), vendor/model quirks, and fixes that worked. One or two sentences " +
      "per note. Do NOT save transient state, secrets, or personal data.",
    parameters: params({
      note: Type.String({ description: "One concise, durable fact about this device." }),
    }),
    execute: async (_id, p, signal) => {
      const m = target(p);
      try {
        await trmm.saveDeviceNote(m.agentId, p.note, { signal });
        return text("Saved to device memory.");
      } catch (e) {
        return text("Could not save device note: " + (e?.message || e));
      }
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
    save_device_note,
  ];
  if (hd) tools.push(helpdesk_call);
  if (anyWindows) tools.push(get_event_logs);

  if (hardReadonly) {
    // no mutate rights at all: drop the destructive actions entirely.
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
    "helpdesk_call",
  ]);

  return { tools, mutating, verdict, machines, helpdeskState };
}

// ---------------------------------------------------------------------------
// Report mode: no device access. Used by the end-of-batch finalizer to compile
// ONE combined report. Exposes a DETERMINISTIC submit_report tool (single call,
// atomic create-or-update - no LLM API orchestration) + report_result. This is
// deliberately NOT the free-form helpdesk_api_request: a fixed-format fleet
// report must never fan out into dozens of calls or duplicate tickets.
export function buildReportTools({ helpdeskCode, helpdeskApi } = {}) {
  const text = (s) => ({ content: [{ type: "text", text: s }], details: {} });
  const verdict = { status: null, summary: "", details: "" };
  let hd = null, hdError = "";
  try { hd = loadHelpdesk(helpdeskCode, helpdeskApi); }
  catch (e) { hdError = e.message; }
  const helpdeskState = { error: false, detail: "" };

  const submit_report = defineTool({
    name: "submit_report",
    label: "Submit combined report",
    description:
      "Create or update THE single combined report ticket. Call this EXACTLY ONCE" +
      " with the entire report composed in the body. If a ticket with the same" +
      " subject already exists for this customer, your body is appended as one" +
      " update note; otherwise one new ticket is created. Do NOT call it more than" +
      " once and do NOT try to write the report any other way.",
    parameters: Type.Object({
      partner_id: Type.Number({
        description: "Customer res.partner id for the report (from your instructions)",
      }),
      team_id: Type.Optional(
        Type.Number({ description: "Helpdesk team id (from your instructions)" }),
      ),
      subject: Type.String({ description: "Exact ticket subject" }),
      body: Type.String({
        description:
          "The COMPLETE report as HTML, covering every machine in one string" +
          " (headline counts, then failing, warning, OK, not-installed sections).",
      }),
    }),
    execute: async (_id, p) => {
      if (!hd || !hd.operations.submit_report) {
        helpdeskState.error = true;
        helpdeskState.detail = `submit_report unavailable${hdError ? ": " + hdError : ""}`;
        return text(
          `Report integration (submit_report) is not available${hdError ? ": " + hdError : ""}.`,
        );
      }
      try {
        const r = await hd.operations.submit_report({
          subject: p.subject,
          body: p.body,
          partner_id: p.partner_id,
          team_id: p.team_id,
        });
        let out = typeof r === "string" ? r : JSON.stringify(r);
        if (hd.apiKey) out = out.split(hd.apiKey).join("***");
        return text(`${out}. Do not call submit_report again.`);
      } catch (e) {
        let msg = e && e.message ? e.message : String(e);
        if (hd.apiKey) msg = msg.split(hd.apiKey).join("***");
        helpdeskState.error = true; helpdeskState.detail = `submit_report: ${msg}`;
        return text(`Report submit failed: ${msg}`);
      }
    },
  });

  const report_result = defineTool({
    name: "report_result",
    label: "Report result",
    description:
      "Call this EXACTLY ONCE at the end to report the outcome of building the" +
      " combined report. status='ok' if the report ticket was created/updated," +
      " 'warning' if partial, 'alert' if it failed. summary is a one-line headline.",
    parameters: Type.Object({
      status: Type.String({ description: "'ok' | 'warning' | 'alert'" }),
      summary: Type.String({ description: "One-line headline" }),
      details: Type.Optional(Type.String({ description: "Supporting details" })),
    }),
    execute: async (_id, p) => {
      const s = (p.status || "").toLowerCase();
      verdict.status = ["ok", "warning", "alert"].includes(s) ? s : "ok";
      verdict.summary = p.summary || "";
      verdict.details = p.details || "";
      return text("Result recorded.");
    },
  });

  return { tools: [submit_report, report_result], verdict, helpdeskState };
}
