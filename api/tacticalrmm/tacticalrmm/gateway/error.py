# ── User-facing messages (sent to SSH client) ──────────────────────────────
DENIED_EXEC_DISABLED      = "SSH gateway exec access is disabled by your administrator.\r\n"
DENIED_TERMINAL_DISABLED  = "SSH gateway terminal access is disabled by your administrator.\r\n"
DENIED_AGENT_PERMISSION   = "Access denied: you don't have permission to access this agent.\r\n"
DENIED_AGENT_NOT_FOUND_FMT = "Agent {agent_id} not found.\r\n"
DENIED_NO_AGENTS          = "No agents available. You don't have permission to access any agents, or no agents exist.\r\n"
DENIED_NO_AGENTS_REFRESH  = "No agents available.\r\n"
GOODBYE                   = "\r\nGoodbye.\r\n"

# ── Audit reason strings ──────────────────────────────────────────────────
REASON_FUNCTION_NO_PERMISSION = "function_no_permission"
REASON_EXEC_DISABLED    = "exec_disabled"
REASON_TERMINAL_DISABLED = "terminal_disabled"
REASON_UNKNOWN_KEY      = "unknown_key"
REASON_INACTIVE_USER    = "inactive_user"
REASON_NO_PERMISSION    = "access_denied_no_permission"
REASON_AGENT_OFFLINE    = "agent_offline"

# ── Log message templates ─────────────────────────────────────────────────
LOG_FUNCTION_DENIED     = "Gateway: function %s denied for user=%s from %s"
LOG_EXEC_DISABLED       = "Gateway: exec denied (disabled) user=%s agent=%s from %s"
LOG_TERMINAL_DISABLED   = "Gateway: terminal denied (disabled) user=%s agent=%s from %s"
LOG_AGENT_DENIED        = "Gateway: denied user=%s agent=%s from %s"
LOG_AGENT_OFFLINE       = "Gateway: denied user=%s agent=%s from %s reason=agent_%s"
LOG_UNKNOWN_KEY         = "Gateway: unknown key %s from %s"
LOG_INACTIVE_USER       = "Gateway: inactive user %s from %s"
