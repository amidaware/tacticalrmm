// Thin Tactical RMM REST client. Every call is authenticated with the bridge's
// service API key. All device-facing tools go through here.
//
// Every request is bounded by a transport timeout (default 120s) and can also
// be cancelled by the caller's AbortSignal (the agent turn's abort). This
// guarantees a tool call can NEVER hang forever: on timeout the promise
// rejects with a model-friendly error, which pi returns to the LLM as an
// error tool result so it can adapt (retry smaller, different approach, etc).
import { CONFIG } from "./config.js";

const DEFAULT_TIMEOUT_MS = 120_000;

async function req(method, path, body, { timeoutMs = DEFAULT_TIMEOUT_MS, signal } = {}) {
  const url = `${CONFIG.trmmApiUrl}${path}`;
  const headers = {
    "X-API-KEY": CONFIG.trmmApiKey,
    "Content-Type": "application/json",
  };
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const finalSignal = signal
    ? AbortSignal.any([signal, timeoutSignal])
    : timeoutSignal;
  let res;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: finalSignal,
    });
  } catch (e) {
    if (timeoutSignal.aborted) {
      throw new Error(
        `STALLED: TRMM ${method} ${path} produced no response within ${Math.round(timeoutMs / 1000)}s. ` +
          `The device agent or RMM API is hung/slow; the operation MAY still be running on the device. ` +
          `Do not immediately re-run the exact same command - try a shorter/simpler variant, split the ` +
          `work into smaller steps, or a different approach.`,
      );
    }
    if (signal?.aborted) {
      throw new Error(`TRMM ${method} ${path} was cancelled by the operator.`);
    }
    throw e;
  }
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const msg = typeof data === "string" ? data : JSON.stringify(data);
    throw new Error(`TRMM ${method} ${path} -> ${res.status}: ${msg}`);
  }
  return data;
}

export const trmm = {
  getAgent: (agentId, opts) => req("GET", `/agents/${agentId}/`, null, opts),
  // Run a raw shell/cmd/powershell command on the device.
  // TRMM: POST /agents/<id>/cmd/  { shell, cmd, timeout, custom_shell, run_as_user }
  // NOTE: run_as_user and custom_shell are REQUIRED by the TRMM view (missing => 500).
  sendCmd: (agentId, { shell, cmd, timeout = 30, runAsUser = false, customShell = null }, opts) =>
    req(
      "POST",
      `/agents/${agentId}/cmd/`,
      {
        shell,
        cmd,
        timeout,
        custom_shell: customShell,
        run_as_user: runAsUser,
      },
      // transport waits a bit longer than the device-side timeout so the
      // device gets first chance to report; then we give up cleanly.
      { timeoutMs: (timeout + 30) * 1000, ...opts },
    ),
  // Run a saved script by pk. TRMM: POST /agents/<id>/runscript/
  runScript: (agentId, { script, args = [], timeout = 90, output = "wait" }, opts) =>
    req(
      "POST",
      `/agents/${agentId}/runscript/`,
      {
        script,
        args,
        timeout,
        output,
      },
      { timeoutMs: (timeout + 30) * 1000, ...opts },
    ),
  listScripts: (opts) => req("GET", `/scripts/`, null, opts),
  listProcesses: (agentId, opts) => req("GET", `/agents/${agentId}/processes/`, null, opts),
  killProcess: (agentId, pid, opts) =>
    req("DELETE", `/agents/${agentId}/processes/${pid}/`, null, opts),
  eventLog: (agentId, logType, days, opts) =>
    req("GET", `/agents/${agentId}/eventlog/${logType}/${days}/`, null, opts),
  listSoftware: (agentId, opts) => req("GET", `/software/${agentId}/`, null, opts),
  getChecks: (agentId, opts) => req("GET", `/agents/${agentId}/checks/`, null, opts),
  getTasks: (agentId, opts) => req("GET", `/agents/${agentId}/tasks/`, null, opts),
  reboot: (agentId, opts) => req("POST", `/agents/${agentId}/reboot/`, null, opts),
  // Send an email via the RMM server's configured SMTP (TRMM: POST /core/ai/email/)
  sendEmail: ({ to, subject, body, html, from_address, from_name, job_ref }, opts) =>
    req(
      "POST",
      `/core/ai/email/`,
      { to, subject, body, html, from_address, from_name, job_ref },
      opts,
    ),
  // Append one durable note to a device's Pi.dev AI memory (TRMM: POST
  // /core/ai/device-note/ { agent_id, note }). Surfaced to future runs in the
  // system prompt.
  // AI Procedures library (RMM-native). The bridge may only ever create DRAFTS - see
  // save_procedure in tools.js for why.
  saveProcedure: (proc, opts) => req("POST", `/core/ai/procedures/`, proc, opts),
  // Credit an AI-performed ticket action to the human who drove it (see AIActionCredit).
  creditAction: (credit, opts) => req("POST", `/core/ai/action-credit/`, credit, opts),
  // Work ledger: one entry per burst of real work, posted as the session ends.
  logWork: (entry, opts) => req("POST", `/core/ai/work-entry/`, entry, opts),
  listProcedures: ({ q } = {}, opts) =>
    req("GET", `/core/ai/procedures/${q ? `?q=${encodeURIComponent(q)}` : ""}`, null, opts),

  saveDeviceNote: (agentId, note, opts) =>
    req("POST", `/core/ai/device-note/`, { agent_id: agentId, note }, opts),
  // Read a device's existing Pi.dev AI memory notes (GET /core/ai/device-note/?agent_id=).
  getDeviceNotes: (agentId, opts) =>
    req("GET", `/core/ai/device-note/?agent_id=${encodeURIComponent(agentId)}`, null, opts),
  // Link an Odoo company (domain/name) + optional requester username to the RMM
  // client and the user's device(s). (TRMM: POST /core/ai/resolve-devices/)
  resolveDevices: ({ domain, company_name, username, person_name, hostname }, opts) =>
    req("POST", `/core/ai/resolve-devices/`, { domain, company_name, username, person_name, hostname }, opts),
  // Schedule a future AI action (runs once at run_at). TRMM: POST /core/ai/schedule-action/
  scheduleAction: ({ agent_id, ticket_ref, action, run_at, allow_mutating }, opts) =>
    req("POST", `/core/ai/schedule-action/`, { agent_id, ticket_ref, action, run_at, allow_mutating }, opts),
};
