# Pi.dev AI Assistant for Tactical RMM

An in-portal AI assistant that operates on a **single device at a time** through
Tactical RMM's existing agent channel, plus **scheduled AI tasks** that
periodically check a device and raise TRMM alerts when they find a problem.

- Right-click a device → **Pi.dev** → chat window scoped to that device.
- The assistant acts on the device with **the same REST endpoints** TRMM already
  uses (`/cmd/`, `/runscript/`, processes, event logs, software, checks…), so
  everything it does is audited and goes over the normal agent path.
- Global settings hold provider API keys + a model catalog; role permissions
  gate who can use it and which models they can use.
- Scheduled tasks run headlessly, report a verdict, and create alerts.

---

## 1. Architecture

```
Browser (portal)
  AgentActionMenu → "Pi.dev" → popup /pichat/:agent_id
      POST /agents/<id>/pi/session/   (Knox auth + PiPerms → short-lived redis token)
      WebSocket  wss://<api>/pi/ws/<token>/
                     │
  nginx  location ~ ^/pi/  → 127.0.0.1:8787
                     │
  pi-trmm-bridge (Node, systemd, /opt/pi-trmm-bridge)
      • reads redis pi_session:<token>  (written by Django; never exposed to browser)
      • one AI session per chat, scoped to the agent
      • built-in shell/edit/write DISABLED; custom tools call the TRMM REST API
      • streams events → WebSocket → chat window
                     │TRMM REST (service API key)         │LLM provider (key from settings)
                Django (/rmm)  → NATS → device            Anthropic / OpenAI / …
```

Scheduled tasks use the same bridge via a headless `POST /pi/run` endpoint driven
by a Celery beat poller.

### Components added

| Layer | What |
|-------|------|
| Backend (`api/tacticalrmm`) | `AIProvider`, `AIModel`, `AITask`, `AITaskRun` models; `CoreSettings` AI toggles; `Role.can_use_ai` / `can_use_ai_autoapprove` / `ai_allowed_models`; `PiPerms`; endpoints under `/core/ai/…` and `/agents/<id>/pi/…`; Celery tasks `dispatch_due_ai_tasks` + `run_ai_task`; redis token helper `agents/pi_session.py` |
| Bridge (`pibridge/`) | Node service embedding the AI runtime; deployed to `/opt/pi-trmm-bridge` by `pibridge/setup.sh` |
| Frontend (`tacticalrmm-web`) | "Pi.dev" menu item + `PiChat.vue`; AI settings tab; role permissions; `AIHistoryTab`, `AITasksTab` (per-device + company aggregate) |
| Install/Update | `install.sh` and `update.sh` call `pibridge/setup.sh`; nginx `/pi/` block added |

---

## 2. Installation & updates (automatic)

Fresh installs and upgrades set everything up with **no manual steps**:

- `install.sh` builds the nginx `/pi/` location block into `rmm.conf` and calls
  `pibridge/setup.sh`.
- `update.sh` calls `pibridge/setup.sh` (idempotent) after migrations/restarts.

`pibridge/setup.sh` (idempotent) does:

1. Deploys `pibridge/` → `/opt/pi-trmm-bridge` and runs `npm install` (incl. the
   AI runtime SDK).
2. Ensures a TRMM **service API key** (`pi-bridge`, role `pi-bridge-service`) the
   bridge uses to act on devices.
3. Writes `/etc/pi-trmm-bridge.env` (port, redis, API url, key, session dir).
4. Writes/enables `pi-trmm-bridge.service` (systemd).
5. Injects the nginx `/pi/` block on existing installs if missing.
6. Restarts the bridge.

Manual run if ever needed:

```bash
bash /rmm/pibridge/setup.sh
sudo systemctl status pi-trmm-bridge
curl -s http://127.0.0.1:8787/pi/health      # {"ok":true}
tail -f /var/log/pi-trmm-bridge.log
```

---

## 3. Configure providers & models

**Global Settings → Pi.dev AI** (requires `can_edit_core_settings`):

- **Enable Pi.dev module** (master switch), **Require approval for device
  actions**, **Persist chat history**.
- **Providers** — add a provider (Anthropic / OpenAI / Google / xAI / OpenRouter
  / custom) and paste its API key (stored server-side, write-only).
- **Models** — pick from a dropdown that lists **exactly the models available for
  your configured keys**, set a display name, thinking level, enable, and mark
  one **default**.

Example: add Anthropic with your key, add model `claude-sonnet-4-5` as default.

Under the hood:

```
POST /core/ai/providers/   {"name":"anthropic","api_key":"sk-...","enabled":true}
GET  /core/ai/available-models/          → models the current keys can use
POST /core/ai/models/      {"provider":1,"model_id":"claude-sonnet-4-5",
                            "display_name":"Claude Sonnet 4.5","is_default":true,"enabled":true}
```

---

## 4. Who can use it (roles)

**Accounts → Roles → (role) → Pi.dev AI**:

- **Use Pi.dev AI Assistant** (`can_use_ai`) — required to open chats and to see /
  manage scheduled tasks.
- **Allow auto-approve of device actions** (`can_use_ai_autoapprove`) — lets that
  role toggle auto-approve in a chat.
- **Allowed AI models** — multiselect; empty = the global default only.

Model access is enforced **server-side**: the session token only carries the
models the role may use, and the bridge refuses anything else. Superusers get all
enabled models.

**Scope:** chats and scheduled tasks are further limited by the role's normal
agent access — a tech only sees/manages tasks for devices in the clients/sites
they're allowed to view (task lists are filtered by `Agent.filter_by_role`, and
per-device actions are checked with `_has_perm_on_agent`). Configuring providers /
models is separate and still requires core-settings admin
(`can_view/edit_core_settings`).

---

## 5. Interactive chat

Right-click a device → **Pi.dev** opens a popup scoped to that device.

- The system prompt is seeded with the device facts (hostname, client/site, OS,
  logged-in user, IPs…). The assistant has an effective **root/console shell** on
  the device via `run_command_on_device` (each call is a fresh non-interactive
  shell; it batches steps with `;`/`&&`).
- **Mutating actions** (run command/script, kill process, reboot) require an
  in-window **Approve** click by default. Roles with auto-approve can flip a
  per-session toggle.
- **Switch models mid-conversation** from the dropdown — the model changes on the
  **same session**, history preserved (no reset).
- Everything the assistant runs shows as a tool card with the exact command and
  its output.

Example prompts:

- *"What's using all the memory right now?"*
- *"List the docker containers and tell me if any are unhealthy."*
- *"The disk is filling up — find the biggest directories under /var."*

### 6.1 AI History

Device view → **AI History** tab shows a unified log of AI activity on that
device, with a **Source** column:

- **Chat** — interactive sessions; **Continue** resumes one (survives a dropped
  connection), **New chat** starts fresh.
- **Task: <name>** — a scheduled task run; **View** shows its transcript.
- **Bulk: <name>** — a run from a Bulk AI Command (§7); **View** shows its
  transcript.

Chat sessions persist per `agent_id`; task/bulk runs come from `AITaskRun`.

---

## 6. Scheduled AI Tasks

Device view → **AI Tasks** tab (or the company aggregate, §7).

Create a task with:

- **Prompt** — what to check, e.g. *"Check SQL Server performance. Alert if any
  data file write latency is over 1s or wait stats look bad; warn over 500ms;
  otherwise ok."*
- **Model** (or global default), **Alert threshold** (never / warning+alert /
  alert-only).
- **When to run**: **Now** (one-shot — runs when you click Run now, then
  auto-disables itself, kept with its results) or **Scheduled**.
- **Scheduled** options: **Every N minutes**, **Daily**, **Weekly** (pick days),
  or **Monthly** (day of month). (Legacy one-time tasks still run at their target
  and disable afterward.)
- **Allow changes** — off by default. Off = read-only diagnostics (can run shell
  commands described in the prompt, but destructive tools are blocked). On =
  allows run-script / kill / reboot for unattended remediation.

### How a task decides "something is wrong"

The scheduled run has a `report_result` tool it must call once with a verdict:

```
report_result(status: "ok" | "warning" | "alert", summary, details)
```

Django maps the verdict to a TRMM alert severity and, if it meets the threshold,
creates a **custom Alert** on the device (dashboard + alert-template routing):

| Verdict | Severity | Alerts when threshold is… |
|---------|----------|---------------------------|
| `ok`      | —      | never |
| `warning` | WARNING | "warning" |
| `alert`   | ERROR   | "warning" or "alert" |
| run error | WARNING | "warning" or "alert" |

### Scheduling

A Celery beat poller (`dispatch_due_ai_tasks`, every minute) queues due tasks;
`run_ai_task` calls the bridge's headless `POST /pi/run`, records an `AITaskRun`,
updates the task, and raises the alert if needed. One-time tasks store a computed
`run_at` target and set `enabled=False` after their single run.

### Run history & live tracing

- **Run now** starts the task immediately and opens a **live trace** window that
  streams each tool call, its output, and the final verdict in real time.
- The **history** view is master-detail: every run on the left (status + brief
  summary + when); click one to see the full transcript of everything it did.

---

## 7. Bulk AI Commands

**Tools → Bulk AI Command** runs one AI prompt across **many devices**, on demand
or on a schedule. Offline agents are skipped at run time.

- **Targeting** mirrors Bulk Command: **All / Client / Site / Agents / Filter**.
  - The Agents picker lists machines with their **client / site** shown faded,
    and filters as you type (by hostname, client, or site).
  - **Filter** mode builds dynamic rules (a `+` adds conditions, all ANDed):
    e.g. *client contains "Lehigh" AND hostname contains "VM"*. Fields: hostname,
    client, site, description, OS, platform, monitoring type. Operators: contains,
    does-not-contain, equals, does-not-equal, starts-with. A live preview shows
    how many online devices match.
  - Type/OS quick filters apply to All/Client/Site targets.
- **When to run**: **Now** (one-shot — runs on the online targets then disables
  itself, kept with its results) or **Scheduled** (Every N hours / Daily / Weekly
  / Monthly).
- Same options as tasks: model, alert threshold, read-only vs allow-changes.

Each per-device execution is recorded as an `AITaskRun` tagged to the bulk
command, so it appears in that device's **AI History** (§6.1) with a
**"Bulk: <name>"** source, and raises alerts per the threshold.

Endpoints (`BulkAIPerms` = `can_use_ai` + `can_run_bulk`):

```
GET/POST     /core/ai/bulk/           ,  PUT/DELETE /core/ai/bulk/<id>/
POST         /core/ai/bulk/<id>/run/  (run now)
POST         /core/ai/bulk/preview/   (count online agents a target would hit)
```

Scheduler: `dispatch_due_bulk_ai_commands` (beat, every minute) fans a due
command out to `run_bulk_ai_agent` per online target.

## 8. Company-wide view (Client / Site)

Select a **Client** or **Site** in the tree, then open the **AI Tasks** tab in
the bottom panel: instead of "No agent selected" it shows **every task across all
devices in that company** with a **Hostname** column and an **aggregate status
summary** (counts of OK / Warning / Alert / Error / Never-run), worst-status
sorted, filterable. Run-now and history work per row.

---

## 9. API reference

Device-scoped (Knox auth, `PiPerms`):

```
POST   /agents/<agent_id>/pi/session/     → { token, url, model_id, allowed_models, ... }
GET    /agents/<agent_id>/pi/history/     → { sessions: [...] }
DELETE /agents/<agent_id>/pi/history/     { "session_id": "..." }
WS     /pi/ws/<token>/                    (via the bridge)
```

Provider / model config (Knox auth, core-settings admin
`can_view/edit_core_settings`):

```
GET/POST        /core/ai/providers/          ,  PUT/DELETE /core/ai/providers/<id>/
GET             /core/ai/available-models/
GET/POST        /core/ai/models/             ,  PUT/DELETE /core/ai/models/<id>/
```

Scheduled tasks & runs (Knox auth, `AITaskPerms` = `can_use_ai` + per-agent
access; lists are scoped to the role's visible clients/sites):

```
GET/POST        /core/ai/tasks/              ,  PUT/DELETE /core/ai/tasks/<id>/
   (filter: ?agent_id= | ?site=<id> | ?client=<id>)
POST            /core/ai/tasks/<id>/run/     (run now)
GET             /core/ai/runs/?task_id=<id>  (run history)
GET             /core/ai/runs/<run_id>/live/ (live progress from redis)
```

Bridge (localhost only):

```
GET  /pi/health
POST /pi/run                 (headless scheduled run → {status, summary, transcript})
POST /pi/models              (available models for provider keys)
GET  /pi/history/<agent_id>  (session index)
WS   /pi/ws/<token>/         (interactive chat)
```

---

## 10. Reliability & troubleshooting

Several safeguards keep a chat or task from appearing "stuck":

- **Command timeout guard** — on Linux, `run_command_on_device` wraps the command
  in `timeout`, so a hung command (e.g. a stuck Proxmox `qm list`/pmxcfs) is
  terminated and returns partial output plus a clear note instead of blocking the
  session.
- **Chat stall watchdog** — the chat window shows an elapsed timer while working,
  and after ~45s with no activity it warns that the model/device may be slow and
  offers a **Stop** button.
- **Connection recovery** — if the WebSocket drops mid-response, the window shows
  a **Reconnect** button that resumes the same conversation (via session id).
- **Auto-retry visibility** — transient provider errors are retried and surfaced
  in the chat (“provider was busy; retrying…”).
- **WebSocket heartbeat** — the bridge pings clients and drops zombie connections.
- **Per-session logging** — the bridge logs each tool call, retries, and errors to
  `/var/log/pi-trmm-bridge.log` for diagnosis.
- **Long scheduled runs** — the runner waits up to `PI_RUN_TIMEOUT` (default
  3600s) for a task to finish, so lengthy investigations/remediations aren't cut
  off. If the HTTP call still times out, it recovers the verdict from the
  bridge's redis progress when available. Raise `PI_RUN_TIMEOUT` in
  `local_settings.py` for tasks that need even longer.

## 11. Security model

1. Gated by **module enabled** (global) + **`can_use_ai`** (role) + agent scope,
   enforced when the session token is minted.
2. Model choice enforced server-side against the role's allowed list.
3. The bridge has **no shell on the RMM server** (built-in shell/edit/write
   disabled); it only acts on the target device through TRMM's REST API, hard-
   bound to the one `agent_id` in the token.
4. Mutating device actions require in-window approval by default; unattended
   tasks are read-only unless explicitly allowed.
5. Provider keys and the TRMM service key stay server-side; the browser only ever
   receives a short-lived (8h) redis token over TLS.
6. Device data and command output are sent to the configured LLM provider — this
   is inherent to the feature and should be acceptable under your data policy
   before enabling the module.

---

## 12. Bridge environment (`/etc/pi-trmm-bridge.env`)

```
PORT=8787
HOST=127.0.0.1
REDIS_URL=redis://127.0.0.1:6379
TRMM_API_URL=https://<your-api-domain>
TRMM_API_KEY=<service key, auto-created by setup.sh>
PI_SESSIONS_ROOT=/opt/pi-trmm-bridge/sessions
IDLE_TIMEOUT_MS=1800000
MAX_SESSIONS=10
```
