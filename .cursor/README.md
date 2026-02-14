# Openframe Script Schedules

A new Django app (`scriptschedules`) that adds the ability to create scheduled script
executions and assign them to multiple agents at once — without modifying any
existing TacticalRMM models.

---

## Architecture

```
OpenframeScriptSchedule
  ├── managed_task   ──►  AutomatedTask (OneToOne, CASCADE)
  │       ├── name, task_type, run_time_date
  │       ├── actions (JSON list of script entries)
  │       ├── task_supported_platforms, enabled
  │       ├── daily_interval, weekly_interval, ...
  │       └──► TaskResult (FK per agent — created automatically)
  └── assigned_agents ──► Agent (M2M)
```

### Key design decisions

1. **No data duplication** — `OpenframeScriptSchedule` has only 2 fields:
   `managed_task` (OneToOneField) and `assigned_agents` (ManyToManyField).
   All scheduling configuration (name, type, datetime, recurrence, script
   actions, platform filter, enabled flag) lives entirely on the existing
   `AutomatedTask` model.

2. **Zero changes to existing models** — `AutomatedTask`, `TaskResult`, `Agent`
   models are not modified. The only change is adding a new method
   `get_tasks_from_openframe_schedules()` to the Agent model class.

3. **Scheduler integration via existing pipeline** — The Celery tasks
   `sync_scheduled_tasks` and `scheduled_task_runner` already call
   `agent.get_tasks_with_policies()`. We extend that method to also include
   tasks from `OpenframeScriptSchedule` (only when `OPENFRAME_MODE=True`).
   This means:
   - `TaskResult` rows are created automatically by the scheduler
   - Task scheduling, execution, and result collection work identically to
     native TacticalRMM tasks
   - The Go agent sees the same `AutomatedTask` via its normal
     `GET /api/v3/{taskpk}/{agentid}/taskrunner/` endpoint

4. **All new classes prefixed with `Openframe`** to clearly separate from
   upstream TacticalRMM code.

---

## Database tables

| Table | Purpose |
|---|---|
| `scriptschedules_openframescriptschedule` | Main model — links AutomatedTask ↔ Agents |
| `scriptschedules_openframescriptschedule_assigned_agents` | M2M join table |

---

## Python classes

### Model

| Class | File |
|---|---|
| `OpenframeScriptSchedule` | `models.py` |

**Methods:**
- `sync_task_results()` — ensures a `TaskResult` row exists for every assigned agent; removes stale rows. Returns `{"created": int, "deleted": int}`.
- `delete()` — deletes the managed `AutomatedTask` (cascades to all `TaskResult` rows), then deletes self.

### Serializers

| Class | File | Purpose |
|---|---|---|
| `OpenframeScriptScheduleListSerializer` | `serializers.py` | List view — proxies task fields |
| `OpenframeScriptScheduleDetailSerializer` | `serializers.py` | Detail view — includes agents + history |
| `OpenframeScriptScheduleCreateSerializer` | `serializers.py` | Create/Update — writes to AutomatedTask |
| `OpenframeAssignedAgentSerializer` | `serializers.py` | Agent info (hostname, platform, etc.) |
| `OpenframeExecutionHistorySerializer` | `serializers.py` | TaskResult history entries |
| `OpenframeAgentAssignmentSerializer` | `serializers.py` | Agent ID list for assignment |

### Views

| Function | File | Purpose |
|---|---|---|
| `openframe_script_schedule_list_create` | `views.py` | `GET`/`POST` on `/script-schedules/` |
| `openframe_script_schedule_detail` | `views.py` | `GET`/`PUT`/`DELETE` on `/script-schedules/<pk>/` |
| `openframe_script_schedule_agents` | `views.py` | `GET`/`PUT`/`POST`/`DELETE` on `/script-schedules/<pk>/agents/` |
| `openframe_script_schedule_history` | `views.py` | `GET` on `/script-schedules/<pk>/history/` |
| `openframe_schedules_for_script` | `views.py` | `GET` on `/scripts/<pk>/schedules/` |
| `openframe_schedules_for_agent` | `views.py` | `GET` on `/agents/<agent_id>/script-schedules/` |

### App config

| Class | File |
|---|---|
| `OpenframeScriptSchedulesConfig` | `apps.py` |

---

## API endpoints

### CRUD — `/script-schedules/`

| Method | URL | Description |
|---|---|---|
| `GET` | `/script-schedules/` | List all schedules (lightweight) |
| `POST` | `/script-schedules/` | Create schedule + AutomatedTask |
| `GET` | `/script-schedules/<pk>/` | Full detail: task fields + agents + last runs |
| `PUT` | `/script-schedules/<pk>/` | Partial update (modifies the AutomatedTask) |
| `DELETE` | `/script-schedules/<pk>/` | Delete schedule + task + all TaskResults |

### Agent management — `/script-schedules/<pk>/agents/`

| Method | Description | Body |
|---|---|---|
| `GET` | List assigned agents | — |
| `PUT` | Replace entire agent set | `{"agents": ["id1", "id2"]}` |
| `POST` | Add agents | `{"agents": ["id3"]}` |
| `DELETE` | Remove agents | `{"agents": ["id1"]}` |

After `PUT`/`POST`/`DELETE`, `TaskResult` rows are automatically synced.

### Execution history — `/script-schedules/<pk>/history/`

| Method | Description | Query params |
|---|---|---|
| `GET` | Paginated execution results | `?limit=50&offset=0` |

### Reverse lookups

| Method | URL | Description |
|---|---|---|
| `GET` | `/scripts/<script_pk>/schedules/` | Schedules that use this script |
| `GET` | `/agents/<agent_id>/script-schedules/` | Schedules assigned to this agent |

---

## How scheduling works (end-to-end)

### 1. Schedule creation

```
POST /script-schedules/
  → serializer creates AutomatedTask with name, task_type, run_time_date, actions, etc.
  → creates OpenframeScriptSchedule linked to that task
```

### 2. Assign agents

```
POST /script-schedules/1/agents/
  {"agents": ["agent-id-1", "agent-id-2"]}
  → adds agents to M2M
  → sync_task_results() creates TaskResult(agent=X, task=Y, sync_status=SYNCED)
```

### 3. Celery scheduler picks it up

```
sync_scheduled_tasks (runs every 30s)
  → for each agent: agent.get_tasks_with_policies()
      → includes agent.get_tasks_from_openframe_schedules()
      → returns AutomatedTask objects from M2M-linked schedules
  → for each task: checks TaskResult.sync_status
      → INITIAL → sends "create" via NATS to Go agent
      → NOT_SYNCED → sends "modify" via NATS
      → PENDING_DELETION → sends "delete" via NATS
```

### 4. Go agent executes the task

```
Go agent receives NATS "schedtask" payload
  → creates local scheduled job
  → when triggered, calls GET /api/v3/{taskpk}/{agentid}/taskrunner/
  → receives script code, runs it
  → reports results back → TaskResult updated
```

### 5. scheduled_task_runner (POSIX agents)

```
scheduled_task_runner (runs every 60s)
  → queries TaskResult.objects.filter(task__enabled=True).exclude(agent__plat=WINDOWS)
  → checks if task should run based on schedule type + time
  → sends NATS "runtask" command to agent
```

---

## POST /script-schedules/ — example request

```json
{
  "name": "Daily health check",
  "task_type": "daily",
  "run_time_date": "2026-02-14T10:00:00Z",
  "daily_interval": 1,
  "task_supported_platforms": ["darwin", "linux"],
  "enabled": true,
  "actions": [
    {
      "type": "script",
      "script": 5,
      "name": "check_disk",
      "timeout": 60,
      "script_args": [],
      "env_vars": []
    },
    {
      "type": "script",
      "script": 12,
      "name": "check_memory",
      "timeout": 30,
      "script_args": ["-threshold", "90"],
      "env_vars": ["ALERT_EMAIL=ops@example.com"]
    }
  ]
}
```

### Run-once example

```json
{
  "name": "One-time cleanup",
  "task_type": "runonce",
  "run_time_date": "2026-02-14T15:30:00Z",
  "task_supported_platforms": ["darwin"],
  "enabled": true,
  "actions": [
    {
      "type": "script",
      "script": 8,
      "name": "cleanup_tmp",
      "timeout": 120,
      "script_args": [],
      "env_vars": []
    }
  ]
}
```

### Weekly example

```json
{
  "name": "Weekly backup verification",
  "task_type": "weekly",
  "run_time_date": "2026-02-14T02:00:00Z",
  "weekly_interval": 1,
  "run_time_bit_weekdays": 65,
  "task_supported_platforms": ["windows", "linux", "darwin"],
  "enabled": true,
  "actions": [
    {
      "type": "script",
      "script": 15,
      "name": "verify_backup",
      "timeout": 300,
      "script_args": [],
      "env_vars": []
    }
  ]
}
```

> **Note on `run_time_bit_weekdays`:** Bitmask where bit 0 = Monday, bit 6 = Sunday.
> 65 = `0b1000001` = Monday + Sunday.

---

## Files modified outside this app

| File | Change |
|---|---|
| `tacticalrmm/settings.py` | Added `"scriptschedules"` to `INSTALLED_APPS` |
| `tacticalrmm/urls.py` | Added `path("script-schedules/", include("scriptschedules.urls"))` |
| `agents/urls.py` | Added import `openframe_schedules_for_agent` + path |
| `agents/models.py` | Added `get_tasks_from_openframe_schedules()` method + extended `get_tasks_with_policies()` |
| `scripts/urls.py` | Added import `openframe_schedules_for_script` + path |

---

## Settings

| Setting | Required | Purpose |
|---|---|---|
| `OPENFRAME_MODE = True` | Yes | Enables scheduler integration (without it, schedules exist but won't execute) |

---

## actions JSON format

The `actions` field on `AutomatedTask` is a JSON list. Each entry:

```json
{
  "type": "script",
  "script": 5,
  "name": "human readable name",
  "timeout": 60,
  "script_args": ["-flag", "value"],
  "env_vars": ["KEY=value"]
}
```

The `script` field is the PK of a `scripts.Script` record. The Go agent
resolves it via `TaskGOGetSerializer` which fetches the actual script code
at execution time.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Stale TaskResult rows if agent removed from schedule | `sync_task_results()` called after every agent mutation; deletes stale rows |
| Deleted Script referenced in actions | `TaskGOGetSerializer.get_task_actions()` handles `Script.DoesNotExist` — skips missing scripts and cleans the actions list |
| Performance of scheduler loop with many schedules | `select_related("managed_task")` in `get_tasks_from_openframe_schedules()` — single DB query per agent. Can add caching if needed |
| Cascade delete safety | `OpenframeScriptSchedule.delete()` deletes the AutomatedTask first (cascades to TaskResult), then deletes self |
| Go agent compatibility | Go agent only knows about `AutomatedTask` via `taskpk` — completely transparent, no changes needed |
