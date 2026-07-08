// Thin Tactical RMM REST client. Every call is authenticated with the bridge's
// service API key. All device-facing tools go through here.
import { CONFIG } from "./config.js";

async function req(method, path, body) {
  const url = `${CONFIG.trmmApiUrl}${path}`;
  const headers = {
    "X-API-KEY": CONFIG.trmmApiKey,
    "Content-Type": "application/json",
  };
  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
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
  getAgent: (agentId) => req("GET", `/agents/${agentId}/`),
  // Run a raw shell/cmd/powershell command on the device.
  // TRMM: POST /agents/<id>/cmd/  { shell, cmd, timeout, custom_shell, run_as_user }
  // NOTE: run_as_user and custom_shell are REQUIRED by the TRMM view (missing => 500).
  sendCmd: (agentId, { shell, cmd, timeout = 30, runAsUser = false, customShell = null }) =>
    req("POST", `/agents/${agentId}/cmd/`, {
      shell,
      cmd,
      timeout,
      custom_shell: customShell,
      run_as_user: runAsUser,
    }),
  // Run a saved script by pk. TRMM: POST /agents/<id>/runscript/
  runScript: (agentId, { script, args = [], timeout = 90, output = "wait" }) =>
    req("POST", `/agents/${agentId}/runscript/`, {
      script,
      args,
      timeout,
      output,
    }),
  listScripts: () => req("GET", `/scripts/`),
  listProcesses: (agentId) => req("GET", `/agents/${agentId}/processes/`),
  killProcess: (agentId, pid) =>
    req("DELETE", `/agents/${agentId}/processes/${pid}/`),
  eventLog: (agentId, logType, days) =>
    req("GET", `/agents/${agentId}/eventlog/${logType}/${days}/`),
  listSoftware: (agentId) => req("GET", `/software/${agentId}/`),
  getChecks: (agentId) => req("GET", `/agents/${agentId}/checks/`),
  getTasks: (agentId) => req("GET", `/agents/${agentId}/tasks/`),
  reboot: (agentId) => req("POST", `/agents/${agentId}/reboot/`),
};
