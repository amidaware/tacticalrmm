import { defineTool } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { trmm } from "./trmm.js";

// Builds the device-scoped toolset. Every tool is hard-bound to `agentId` from
// the session token; the model can never target another device. Mutating tools
// go through `gate(summary)` which resolves to true (approved) or false (denied).
export function buildTools({ agentId, plat, gate, includeReport = false, readonly = false }) {
  const isWindows = plat === "windows";
  const verdict = { status: null, summary: "", details: "" };

  const text = (s) => ({ content: [{ type: "text", text: s }], details: {} });
  const denied = () =>
    text("The operator DENIED this action. Do not retry it; ask what to do instead.");

  const get_device_details = defineTool({
    name: "get_device_details",
    label: "Get device details",
    description:
      "Get full details about THIS device (hardware, OS, disks, IPs, checks status, custom fields).",
    parameters: Type.Object({}),
    execute: async () => {
      const a = await trmm.getAgent(agentId);
      return text(JSON.stringify(a, null, 2));
    },
  });

  const run_command_on_device = defineTool({
    name: "run_command_on_device",
    label: "Run command on device",
    description: isWindows
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
        ].join(" "),
    parameters: Type.Object({
      command: Type.String({
        description:
          "The full command or script to execute. May contain pipes, redirects, multiple" +
          " statements, and multiple lines.",
      }),
      shell: Type.Optional(
        Type.String({
          description: isWindows
            ? "'cmd' or 'powershell' (default powershell)"
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
    execute: async (_id, p) => {
      const shell = isWindows
        ? p.shell === "cmd"
          ? "cmd"
          : "powershell"
        : "/bin/bash";
      const timeout = p.timeout && p.timeout > 0 ? Math.min(p.timeout, 900) : 60;
      const ok = await gate(`Run on device [${shell}]: ${p.command}`);
      if (!ok) return denied();
      // On Linux, self-terminate the command with `timeout` so a hung command
      // (e.g. a stuck Proxmox `qm list`/pmxcfs) returns promptly with partial
      // output instead of blocking the whole chat until the transport timeout.
      let cmd = p.command;
      if (!isWindows) {
        const q = "'" + p.command.replace(/'/g, "'\\''") + "'";
        const note =
          `[pi] command did not finish within ${timeout}s and was terminated (partial output above; the command or the device is hung)`;
        cmd =
          `timeout --preserve-status --signal=TERM -k 5 ${timeout}s /bin/bash -c ${q}; ` +
          `__ec=$?; if [ $__ec -eq 124 ] || [ $__ec -eq 143 ]; then echo ${"'" + note + "'"}; fi`;
      }
      const out = await trmm.sendCmd(agentId, {
        shell,
        cmd,
        timeout: timeout + 10,
        runAsUser: !!p.run_as_user,
      });
      const s = typeof out === "string" ? out : JSON.stringify(out);
      return text(s.length ? s : "(command produced no output; exit assumed success)");
    },
  });

  const list_scripts = defineTool({
    name: "list_scripts",
    label: "List scripts",
    description: "List scripts available in the TRMM script library (id, name, shell, description).",
    parameters: Type.Object({}),
    execute: async () => {
      const scripts = await trmm.listScripts();
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
    description:
      "Run a saved TRMM library script on THIS device by its numeric script id (use list_scripts first).",
    parameters: Type.Object({
      script_id: Type.Number({ description: "Numeric id of the library script" }),
      args: Type.Optional(Type.Array(Type.String(), { description: "Script arguments" })),
      timeout: Type.Optional(Type.Number({ description: "Seconds (default 90)" })),
    }),
    execute: async (_id, p) => {
      const timeout = p.timeout && p.timeout > 0 ? Math.min(p.timeout, 900) : 90;
      const ok = await gate(`Run library script #${p.script_id} on device`);
      if (!ok) return denied();
      const out = await trmm.runScript(agentId, {
        script: p.script_id,
        args: p.args || [],
        timeout,
        output: "wait",
      });
      return text(typeof out === "string" ? out : JSON.stringify(out));
    },
  });

  const list_processes = defineTool({
    name: "list_processes",
    label: "List processes",
    description: "List running processes on THIS device.",
    parameters: Type.Object({}),
    execute: async () => {
      const procs = await trmm.listProcesses(agentId);
      return text(JSON.stringify(procs, null, 2));
    },
  });

  const kill_process = defineTool({
    name: "kill_process",
    label: "Kill process",
    description: "Kill a process on THIS device by PID.",
    parameters: Type.Object({ pid: Type.Number({ description: "Process id to kill" }) }),
    execute: async (_id, p) => {
      const ok = await gate(`Kill process PID ${p.pid} on device`);
      if (!ok) return denied();
      const out = await trmm.killProcess(agentId, p.pid);
      return text(typeof out === "string" ? out : JSON.stringify(out));
    },
  });

  const get_event_logs = defineTool({
    name: "get_event_logs",
    label: "Get Windows event logs",
    description: "Get Windows event logs from THIS device.",
    parameters: Type.Object({
      log_type: Type.String({ description: "Application, System, or Security" }),
      days: Type.Optional(Type.Number({ description: "How many days back (default 1)" })),
    }),
    execute: async (_id, p) => {
      const out = await trmm.eventLog(agentId, p.log_type, p.days && p.days > 0 ? p.days : 1);
      return text(JSON.stringify(out, null, 2));
    },
  });

  const list_software = defineTool({
    name: "list_software",
    label: "List installed software",
    description: "List installed software on THIS device.",
    parameters: Type.Object({}),
    execute: async () => text(JSON.stringify(await trmm.listSoftware(agentId), null, 2)),
  });

  const get_checks = defineTool({
    name: "get_checks",
    label: "Get checks",
    description: "Get monitoring checks and their status for THIS device.",
    parameters: Type.Object({}),
    execute: async () => text(JSON.stringify(await trmm.getChecks(agentId), null, 2)),
  });

  const get_tasks = defineTool({
    name: "get_tasks",
    label: "Get automated tasks",
    description: "Get automated tasks for THIS device.",
    parameters: Type.Object({}),
    execute: async () => text(JSON.stringify(await trmm.getTasks(agentId), null, 2)),
  });

  const reboot_device = defineTool({
    name: "reboot_device",
    label: "Reboot device",
    description: "Reboot THIS device now.",
    parameters: Type.Object({}),
    execute: async () => {
      const ok = await gate(`REBOOT the device now`);
      if (!ok) return denied();
      const out = await trmm.reboot(agentId);
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
  ];
  if (isWindows) tools.push(get_event_logs);

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
  ]);

  return { tools, mutating, verdict };
}
