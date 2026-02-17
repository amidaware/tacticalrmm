# Script Schedules API Specification

Base URL: `/script-schedules/`
Auth: All endpoints require `Authorization: Token <knox-token>` header.

---

## 1. List Schedules

```
GET /script-schedules/
```

### Response `200 OK`

```json
[
  {
    "id": 1,
    "name": "Daily health check",
    "task_type": "daily",
    "run_time_date": "2026-02-14T10:00:00Z",
    "enabled": true,
    "task_supported_platforms": ["darwin", "linux"],
    "actions_count": 2,
    "agents_count": 5
  }
]
```

### DB queries

```
SELECT * FROM scriptschedules_openframescriptschedule
  JOIN autotasks_automatedtask ON managed_task_id = id
  -- + prefetch assigned_agents M2M
```

---

## 2. Create Schedule

```
POST /script-schedules/
Content-Type: application/json
```

### Request body

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
    }
  ]
}
```

### Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Human-readable name (max 255 chars) |
| `task_type` | string | yes | — | One of: `runonce`, `daily`, `weekly`, `monthly`, `monthlydow` |
| `run_time_date` | datetime | yes | — | ISO 8601 datetime for first/next run |
| `daily_interval` | int | if daily | null | Run every N days |
| `weekly_interval` | int | if weekly | null | Run every N weeks |
| `run_time_bit_weekdays` | int | if weekly | null | Bitmask: bit 0=Mon, bit 6=Sun. E.g. 65=Mon+Sun |
| `monthly_days_of_month` | int | if monthly | null | Bitmask of days (bit 0=1st, bit 30=31st) |
| `monthly_months_of_year` | int | if monthly | null | Bitmask of months (bit 0=Jan, bit 11=Dec) |
| `monthly_weeks_of_month` | int | if monthlydow | null | Bitmask of weeks |
| `task_supported_platforms` | string[] | no | `["windows","linux","darwin"]` | Platforms to run on |
| `enabled` | bool | no | true | Whether schedule is active |
| `actions` | object[] | yes | — | List of script actions (see below) |

### Actions format

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

| Field | Type | Description |
|---|---|---|
| `type` | string | Always `"script"` |
| `script` | int | PK of `scripts.Script` record |
| `name` | string | Display name |
| `timeout` | int | Execution timeout in seconds |
| `script_args` | string[] | CLI arguments passed to script |
| `env_vars` | string[] | Environment variables in `KEY=value` format |

### Validation rules

- `daily` requires `daily_interval`
- `weekly` requires `weekly_interval` + `run_time_bit_weekdays`
- `monthly` / `monthlydow` requires `monthly_months_of_year` + `monthly_days_of_month`
- `actions` must contain at least one entry

### Response `201 Created`

Returns full detail format (same as GET `/script-schedules/<pk>/`).

### What happens on create

1. `AutomatedTask` created with all schedule fields
2. `OpenframeScriptSchedule` created, linked to that task via `managed_task`
3. No agents assigned yet — must use `/script-schedules/<pk>/agents/` next

---

## 3. Get Schedule Detail

```
GET /script-schedules/<pk>/
```

### Response `200 OK`

```json
{
  "id": 1,
  "managed_task_id": 42,
  "name": "Daily health check",
  "task_type": "daily",
  "run_time_date": "2026-02-14T10:00:00Z",
  "daily_interval": 1,
  "weekly_interval": null,
  "run_time_bit_weekdays": null,
  "monthly_days_of_month": null,
  "monthly_months_of_year": null,
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
    }
  ],
  "assigned_agents": [
    {
      "agent_id": "abc123def456ghi789jk0",
      "hostname": "server-01",
      "plat": "linux",
      "operating_system": "Ubuntu 22.04",
      "time_zone": "UTC",
      "client_name": "Acme Corp",
      "site_name": "HQ"
    }
  ],
  "last_runs": [
    {
      "id": 101,
      "agent_id": "abc123def456ghi789jk0",
      "agent_hostname": "server-01",
      "agent_platform": "linux",
      "organization": "Acme Corp / HQ",
      "retcode": 0,
      "stdout": "Disk OK: 45% used",
      "stderr": "",
      "execution_time": "1.234",
      "last_run": "2026-02-14T10:00:05Z",
      "status": "passing",
      "sync_status": "synced"
    }
  ]
}
```

### Notes

- `last_runs` returns up to 20 most recent `TaskResult` entries
- `assigned_agents` includes `client_name` and `site_name` resolved via `agent.site.client`

---

## 4. Update Schedule

```
PUT /script-schedules/<pk>/
Content-Type: application/json
```

### Request body (partial update)

Any subset of fields from the Create body. Only provided fields are updated.

```json
{
  "name": "Updated name",
  "enabled": false
}
```

### Response `200 OK`

Returns full detail format.

### What happens on update

Modifies fields on the underlying `AutomatedTask` (not the `OpenframeScriptSchedule`).
The Go agent picks up changes on next sync cycle.

---

## 5. Delete Schedule

```
DELETE /script-schedules/<pk>/
```

### Response `204 No Content`

### Cascade order

1. `OpenframeScriptSchedule` deleted
2. `AutomatedTask` deleted
3. All `TaskResult` rows deleted (via CASCADE)
4. M2M join table rows cleaned automatically

---

## 6. List Assigned Agents

```
GET /script-schedules/<pk>/agents/
```

### Response `200 OK`

```json
[
  {
    "agent_id": "abc123def456ghi789jk0",
    "hostname": "server-01",
    "plat": "linux",
    "operating_system": "Ubuntu 22.04",
    "time_zone": "UTC",
    "client_name": "Acme Corp",
    "site_name": "HQ"
  }
]
```

---

## 7. Replace Agent Set

```
PUT /script-schedules/<pk>/agents/
Content-Type: application/json
```

### Request body

```json
{
  "agents": ["abc123def456ghi789jk0", "xyz789abc123def456gh1"]
}
```

### Response `200 OK`

```json
{
  "agents_count": 2,
  "task_results_created": 2,
  "task_results_deleted": 3
}
```

### Behavior

- Removes ALL previously assigned agents
- Sets exactly the provided agents
- Syncs TaskResult rows: creates for new agents, deletes for removed

---

## 8. Add Agents

```
POST /script-schedules/<pk>/agents/
Content-Type: application/json
```

### Request body

```json
{
  "agents": ["new-agent-id-here12345"]
}
```

### Response `200 OK`

```json
{
  "agents_count": 3,
  "task_results_created": 1,
  "task_results_deleted": 0
}
```

### Behavior

- Adds agents to existing set (no-op for already assigned)
- Creates TaskResult rows for newly added agents

---

## 9. Remove Agents

```
DELETE /script-schedules/<pk>/agents/
Content-Type: application/json
```

### Request body

```json
{
  "agents": ["abc123def456ghi789jk0"]
}
```

### Response `200 OK`

```json
{
  "agents_count": 2,
  "task_results_created": 0,
  "task_results_deleted": 1
}
```

### Behavior

- Removes specified agents from the set
- Deletes their TaskResult rows

---

## 10. Execution History

```
GET /script-schedules/<pk>/history/?limit=50&offset=0
```

### Query parameters

| Param | Type | Default | Max | Description |
|---|---|---|---|---|
| `limit` | int | 50 | 200 | Results per page |
| `offset` | int | 0 | — | Skip N results |

### Response `200 OK`

```json
{
  "total": 128,
  "limit": 50,
  "offset": 0,
  "results": [
    {
      "id": 101,
      "agent_id": "abc123def456ghi789jk0",
      "agent_hostname": "server-01",
      "agent_platform": "linux",
      "organization": "Acme Corp / HQ",
      "retcode": 0,
      "stdout": "OK",
      "stderr": "",
      "execution_time": "1.234",
      "last_run": "2026-02-14T10:00:05Z",
      "status": "passing",
      "sync_status": "synced"
    }
  ]
}
```

### Notes

- Only shows results where `last_run` is not null (i.e., task has actually executed)
- Ordered by `last_run` descending (most recent first)

---

## 11. Schedules for Script (Reverse Lookup)

```
GET /scripts/<script_pk>/schedules/
```

Returns all schedules whose `actions` contain a reference to this script.

### Response `200 OK`

```json
[
  {
    "id": 1,
    "name": "Daily health check",
    "task_type": "daily",
    "run_time_date": "2026-02-14T10:00:00Z",
    "enabled": true,
    "agents_count": 5
  }
]
```

### DB query

Uses JSONField lookup: `AutomatedTask.objects.filter(actions__contains=[{"script": pk}])`

---

## 12. Schedules for Agent (Reverse Lookup)

```
GET /agents/<agent_id>/script-schedules/
```

Returns all schedules assigned to this agent.

### Response `200 OK`

```json
[
  {
    "id": 1,
    "managed_task_id": 42,
    "name": "Daily health check",
    "task_type": "daily",
    "run_time_date": "2026-02-14T10:00:00Z",
    "enabled": true,
    "actions": [
      {
        "type": "script",
        "script": 5,
        "name": "check_disk",
        "timeout": 60,
        "script_args": [],
        "env_vars": []
      }
    ],
    "task_supported_platforms": ["darwin", "linux"]
  }
]
```

---

## Error Responses

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

Returned when `<pk>` or `<agent_id>` or `<script_pk>` doesn't exist.

### 400 Bad Request

```json
{
  "daily_interval": ["Required for daily schedule."]
}
```

Returned on validation errors (missing required fields, invalid task_type, etc.).

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

Returned when no valid token is provided.

---

## task_type values

| Value | Description | Required fields |
|---|---|---|
| `runonce` | Run once at `run_time_date` | — |
| `daily` | Repeat every N days | `daily_interval` |
| `weekly` | Repeat every N weeks on specified days | `weekly_interval`, `run_time_bit_weekdays` |
| `monthly` | Repeat monthly on specified days/months | `monthly_days_of_month`, `monthly_months_of_year` |
| `monthlydow` | Repeat monthly on day-of-week pattern | `monthly_days_of_month`, `monthly_months_of_year`, `monthly_weeks_of_month` |

---

## Bitmask reference

### run_time_bit_weekdays

```
Bit 0 = Monday    (1)
Bit 1 = Tuesday   (2)
Bit 2 = Wednesday (4)
Bit 3 = Thursday  (8)
Bit 4 = Friday    (16)
Bit 5 = Saturday  (32)
Bit 6 = Sunday    (64)

Examples:
  Monday + Friday = 1 + 16 = 17
  Monday + Sunday = 1 + 64 = 65
  Weekdays = 1+2+4+8+16 = 31
```

### monthly_days_of_month

```
Bit 0  = 1st   (1)
Bit 1  = 2nd   (2)
Bit 14 = 15th  (16384)
Bit 30 = 31st  (1073741824)

Example: 1st and 15th = 1 + 16384 = 16385
```

### monthly_months_of_year

```
Bit 0  = January   (1)
Bit 1  = February  (2)
Bit 5  = June      (32)
Bit 11 = December  (2048)

Example: Jan + Jul = 1 + 64 = 65
Example: Every month = 4095
```

---

## URL routing summary

| URL pattern | View | Methods |
|---|---|---|
| `/script-schedules/` | `openframe_script_schedule_list_create` | GET, POST |
| `/script-schedules/<int:pk>/` | `openframe_script_schedule_detail` | GET, PUT, DELETE |
| `/script-schedules/<int:pk>/agents/` | `openframe_script_schedule_agents` | GET, PUT, POST, DELETE |
| `/script-schedules/<int:pk>/history/` | `openframe_script_schedule_history` | GET |
| `/scripts/<int:script_pk>/schedules/` | `openframe_schedules_for_script` | GET |
| `/agents/<agent:agent_id>/script-schedules/` | `openframe_schedules_for_agent` | GET |
