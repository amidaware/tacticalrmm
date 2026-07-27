// Central config, read from environment (see /etc/pi-trmm-bridge.env)
export const CONFIG = {
  port: parseInt(process.env.PORT || "8787", 10),
  host: process.env.HOST || "127.0.0.1",
  redisUrl: process.env.REDIS_URL || "redis://127.0.0.1:6379",
  // TRMM REST API base (the bridge calls this with a service X-API-KEY to act on devices)
  trmmApiUrl: process.env.TRMM_API_URL || "http://127.0.0.1:8080",
  trmmApiKey: process.env.TRMM_API_KEY || "",
  // where pi session .jsonl files live (per agent_id)
  sessionsRoot: process.env.PI_SESSIONS_ROOT || "/opt/pi-trmm-bridge/sessions",
  idleTimeoutMs: parseInt(process.env.IDLE_TIMEOUT_MS || String(30 * 60 * 1000), 10),
  // Force-abort a streaming turn that emits no events for this long (dead/stuck
  // LLM stream) so a chat can never hang forever. Set 0 to disable.
  turnStallMs: parseInt(process.env.TURN_STALL_MS || String(3 * 60 * 1000), 10),
  // How often the turn watchdog checks for a stalled streaming turn.
  watchdogIntervalMs: parseInt(process.env.WATCHDOG_INTERVAL_MS || String(30 * 1000), 10),
  maxSessions: parseInt(process.env.MAX_SESSIONS || "10", 10),
  sessionPrefix: "pi_session:",
};
