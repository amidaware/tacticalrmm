# Agent Timezone Auto-Detection

Automatically populates `agents_agent.time_zone` with the agent's local IANA timezone
on every `agent-agentinfo` check-in, eliminating the need to set it manually in the UI.
Only active when `OPENFRAME_MODE=true`.

---

## Problem

`agents_agent.time_zone` defaults to `NULL` in the database. When it is `NULL`, all
scheduling logic (automated tasks, Windows Update policies, scheduled reboots) falls back
to `CoreSettings.default_time_zone` which is hardcoded as `America/Los_Angeles`. This
causes tasks to run at wrong local times for agents in other timezones.

---

## Architecture

```
Go agent (rmmagent)
  └── agent-agentinfo (every ~15 min)
        └── AgentInfoNatsEx { ...fields..., Timezone: "Europe/Kyiv" }
              │  (msgpack over NATS)
              ▼
nats-listener (Go)
  └── agent-agentinfo handler
        ├── decode → trmm.AgentInfoNats   (standard fields UPDATE)
        └── decode → agentTimezone        (timezone-only UPDATE, OPENFRAME_MODE only)
              │
              ▼
        PostgreSQL: UPDATE agents_agent SET time_zone=$1 WHERE agent_id=$2
              │
              ▼
        Django scheduler reads agent.timezone → ZoneInfo("Europe/Kyiv")
```

Two separate msgpack decodes on the same `msg.Data` bytes — avoids duplicating all fields
of the upstream `trmm.AgentInfoNats` struct (which cannot be modified as it is a pinned
external dependency).

---

## Files changed

### `nats-listener` (Go server)

| File | Change |
|---|---|
| `nats-listener/types.go` | Added `agentTimezone` struct with `agent_id` + `timezone` fields |
| `nats-listener/svc.go` | `agent-agentinfo` handler: second decode into `agentTimezone`, UPDATE `time_zone` when `OPENFRAME_MODE=true` |

---

## Settings

| Setting | Where | Purpose |
|---|---|---|
| `OPENFRAME_MODE=true` | env var for `nats-api` process | Enables timezone UPDATE in `agent-agentinfo` handler |

---

## Effect on business logic

Once `time_zone` is populated, the following use it automatically with no further changes:

| Component | File | Affected platforms | Behavior |
|---|---|---|---|
| Task scheduler | `core/tasks.py` + `tacticalrmm/scheduler.py` | **Linux / macOS only** | Runs daily/weekly/monthly tasks at correct local time |
| Windows Update | `winupdate/tasks.py` | **Windows** | Applies patch policy at correct local hour/day |
| Scheduled reboot | `agents/views.py` | All | Validates "date in past" check against agent local time |
| Pending action signal | `logs/signals.py` | All | Expires pending reboot correctly |

> **Note:** Windows automated tasks are **not affected** by `time_zone`. Windows agents use
> native Windows Task Scheduler which runs tasks at the specified local OS time independently.
> The Celery `scheduled_task_runner` explicitly excludes Windows agents
> (`.exclude(agent__plat=AgentPlat.WINDOWS)`).

---

## UI restriction in Openframe mode

When `OPENFRAME_MODE = True`, the `PUT /agents/<agent_id>/` endpoint silently drops
`time_zone` from the request payload before saving:

```python
# agents/views.py — GetUpdateDeleteAgent.put()
data = request.data.copy()
if getattr(settings, "OPENFRAME_MODE", False):
    data.pop("time_zone", None)
```

The UI always sends all agent fields on save — rejecting the request would break every
edit. Instead the field is stripped, so the rest of the payload (description, policy,
alerts, etc.) saves normally while `time_zone` in the database remains untouched.