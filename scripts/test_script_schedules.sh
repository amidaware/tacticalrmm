#!/bin/bash
# =============================================================================
# Test script for Openframe Script Schedules API
# Usage: bash test_script_schedules.sh
# Requires: curl, jq
# =============================================================================

set -e

BASE_URL="http://localhost:8000"
USERNAME="tactical"
PASSWORD="tactical"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_request() {
  local method="$1"
  local url="$2"
  local body="$3"
  echo -e "    ${CYAN}${method} ${url}${NC}"
  if [ -n "$body" ]; then
    echo -e "    ${YELLOW}Body:${NC}"
    echo "$body" | jq '.' 2>/dev/null || echo "    $body"
  fi
}

log_response() {
  local response="$1"
  echo -e "    ${GREEN}Response:${NC}"
  echo "$response" | jq '.' 2>/dev/null || echo "    $response"
}

echo "============================================"
echo " Openframe Script Schedules — E2E Test"
echo "============================================"

# -----------------------------------------------------------------
# 1. Get auth token
# -----------------------------------------------------------------
echo ""
echo ">>> 1. Getting auth token..."

LOGIN_BODY="{\"username\": \"${USERNAME}\", \"password\": \"${PASSWORD}\"}"
log_request "POST" "${BASE_URL}/v2/login/" "$LOGIN_BODY"

TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/v2/login/" \
  -H "Content-Type: application/json" \
  -d "${LOGIN_BODY}")

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.token // empty')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "    Failed to get token."
  log_response "$TOKEN_RESPONSE"
  TOKEN="${TRMM_TOKEN:-}"
  if [ -z "$TOKEN" ]; then
    echo "    No token available. Exiting."
    exit 1
  fi
fi

AUTH="Authorization: Token ${TOKEN}"
echo "    Token: ${TOKEN:0:20}..."

# -----------------------------------------------------------------
# 2. Get list of agents
# -----------------------------------------------------------------
echo ""
echo ">>> 2. Getting agents..."
log_request "GET" "${BASE_URL}/agents/"

AGENTS_RESPONSE=$(curl -s -X GET "${BASE_URL}/agents/" -H "${AUTH}")
AGENT_COUNT=$(echo "$AGENTS_RESPONSE" | jq 'length')
echo "    Found ${AGENT_COUNT} agents"

if [ "$AGENT_COUNT" -eq 0 ]; then
  echo "    No agents found! Cannot assign to schedule."
  AGENT_IDS="[]"
else
  AGENT_IDS=$(echo "$AGENTS_RESPONSE" | jq '[.[0:3] | .[].agent_id]')
  echo "    Will assign: ${AGENT_IDS}"
fi

# -----------------------------------------------------------------
# 3. Get list of scripts
# -----------------------------------------------------------------
echo ""
echo ">>> 3. Getting scripts..."
log_request "GET" "${BASE_URL}/scripts/"

SCRIPTS_RESPONSE=$(curl -s -X GET "${BASE_URL}/scripts/" -H "${AUTH}")
SCRIPT_COUNT=$(echo "$SCRIPTS_RESPONSE" | jq 'length')
echo "    Found ${SCRIPT_COUNT} scripts"

if [ "$SCRIPT_COUNT" -eq 0 ]; then
  SCRIPT_ID=1
  SCRIPT_NAME="test_script"
  echo "    No scripts found, using placeholder script ID=${SCRIPT_ID}"
else
  SCRIPT_ID=$(echo "$SCRIPTS_RESPONSE" | jq '.[0].id')
  SCRIPT_NAME=$(echo "$SCRIPTS_RESPONSE" | jq -r '.[0].name')
  echo "    Using script: ${SCRIPT_NAME} (id=${SCRIPT_ID})"
fi

# -----------------------------------------------------------------
# 4. Create a run-once schedule (+2 min from now)
# -----------------------------------------------------------------
echo ""
echo ">>> 4. Creating run-once schedule (+2 min)..."

RUN_DATE=$(date -u -v+2M "+%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "+2 minutes" "+%Y-%m-%dT%H:%M:%SZ")

CREATE_BODY=$(cat <<EOF
{
  "name": "Test Run-Once Schedule",
  "task_type": "runonce",
  "run_time_date": "${RUN_DATE}",
  "task_supported_platforms": ["darwin", "linux"],
  "enabled": true,
  "actions": [
    {
      "type": "script",
      "script": ${SCRIPT_ID},
      "name": "${SCRIPT_NAME}",
      "timeout": 60,
      "script_args": [],
      "env_vars": []
    }
  ]
}
EOF
)

log_request "POST" "${BASE_URL}/script-schedules/" "$CREATE_BODY"

CREATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/script-schedules/" \
  -H "${AUTH}" \
  -H "Content-Type: application/json" \
  -d "${CREATE_BODY}")

SCHEDULE_ID=$(echo "$CREATE_RESPONSE" | jq '.id')
TASK_ID=$(echo "$CREATE_RESPONSE" | jq '.managed_task_id')

echo "    Created schedule id=${SCHEDULE_ID}, managed_task_id=${TASK_ID}"
log_response "$CREATE_RESPONSE"

# -----------------------------------------------------------------
# 5. Create a daily schedule
# -----------------------------------------------------------------
echo ""
echo ">>> 5. Creating daily schedule..."

DAILY_DATE=$(date -u -v+5M "+%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "+5 minutes" "+%Y-%m-%dT%H:%M:%SZ")

DAILY_BODY=$(cat <<EOF
{
  "name": "Daily Health Check",
  "task_type": "daily",
  "run_time_date": "${DAILY_DATE}",
  "daily_interval": 1,
  "task_supported_platforms": ["darwin"],
  "enabled": true,
  "actions": [
    {
      "type": "script",
      "script": ${SCRIPT_ID},
      "name": "${SCRIPT_NAME}",
      "timeout": 90,
      "script_args": ["-v"],
      "env_vars": ["MODE=health"]
    }
  ]
}
EOF
)

log_request "POST" "${BASE_URL}/script-schedules/" "$DAILY_BODY"

DAILY_RESPONSE=$(curl -s -X POST "${BASE_URL}/script-schedules/" \
  -H "${AUTH}" \
  -H "Content-Type: application/json" \
  -d "${DAILY_BODY}")

DAILY_ID=$(echo "$DAILY_RESPONSE" | jq '.id')
echo "    Created daily schedule id=${DAILY_ID}"
log_response "$DAILY_RESPONSE"

# -----------------------------------------------------------------
# 6. Assign agents to the run-once schedule
# -----------------------------------------------------------------
echo ""
echo ">>> 6. Assigning agents to schedule ${SCHEDULE_ID}..."

ASSIGN_BODY="{\"agents\": ${AGENT_IDS}}"

if [ "$AGENT_COUNT" -gt 0 ]; then
  log_request "POST" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/" "$ASSIGN_BODY"

  ASSIGN_RESPONSE=$(curl -s -X POST "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/" \
    -H "${AUTH}" \
    -H "Content-Type: application/json" \
    -d "${ASSIGN_BODY}")

  log_response "$ASSIGN_RESPONSE"
else
  echo "    Skipped — no agents"
fi

# -----------------------------------------------------------------
# 7. Assign agents to the daily schedule
# -----------------------------------------------------------------
echo ""
echo ">>> 7. Assigning agents to daily schedule ${DAILY_ID}..."

if [ "$AGENT_COUNT" -gt 0 ]; then
  log_request "POST" "${BASE_URL}/script-schedules/${DAILY_ID}/agents/" "$ASSIGN_BODY"

  ASSIGN_DAILY=$(curl -s -X POST "${BASE_URL}/script-schedules/${DAILY_ID}/agents/" \
    -H "${AUTH}" \
    -H "Content-Type: application/json" \
    -d "${ASSIGN_BODY}")

  log_response "$ASSIGN_DAILY"
else
  echo "    Skipped — no agents"
fi

# -----------------------------------------------------------------
# 8. GET: List all schedules
# -----------------------------------------------------------------
echo ""
echo ">>> 8. List all schedules..."
log_request "GET" "${BASE_URL}/script-schedules/"

LIST_RESPONSE=$(curl -s -X GET "${BASE_URL}/script-schedules/" -H "${AUTH}")
log_response "$LIST_RESPONSE"

# -----------------------------------------------------------------
# 9. GET: Schedule detail
# -----------------------------------------------------------------
echo ""
echo ">>> 9. Schedule detail..."
log_request "GET" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/"

DETAIL_RESPONSE=$(curl -s -X GET "${BASE_URL}/script-schedules/${SCHEDULE_ID}/" -H "${AUTH}")
log_response "$DETAIL_RESPONSE"

# -----------------------------------------------------------------
# 10. GET: Agents of schedule
# -----------------------------------------------------------------
echo ""
echo ">>> 10. Agents of schedule..."
log_request "GET" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/"

AGENTS_OF_SCHED=$(curl -s -X GET "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/" -H "${AUTH}")
log_response "$AGENTS_OF_SCHED"

# -----------------------------------------------------------------
# 11. GET: Execution history
# -----------------------------------------------------------------
echo ""
echo ">>> 11. Execution history..."
log_request "GET" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/history/?limit=10"

HISTORY=$(curl -s -X GET "${BASE_URL}/script-schedules/${SCHEDULE_ID}/history/?limit=10" -H "${AUTH}")
log_response "$HISTORY"

# -----------------------------------------------------------------
# 12. GET: Schedules for script (reverse lookup)
# -----------------------------------------------------------------
echo ""
echo ">>> 12. Schedules for script (reverse lookup)..."
log_request "GET" "${BASE_URL}/scripts/${SCRIPT_ID}/schedules/"

SCRIPT_SCHEDS=$(curl -s -X GET "${BASE_URL}/scripts/${SCRIPT_ID}/schedules/" -H "${AUTH}")
log_response "$SCRIPT_SCHEDS"

# -----------------------------------------------------------------
# 13. GET: Schedules for agent (reverse lookup)
# -----------------------------------------------------------------
if [ "$AGENT_COUNT" -gt 0 ]; then
  FIRST_AGENT=$(echo "$AGENT_IDS" | jq -r '.[0]')
  echo ""
  echo ">>> 13. Schedules for agent (reverse lookup)..."
  log_request "GET" "${BASE_URL}/agents/${FIRST_AGENT}/script-schedules/"

  AGENT_SCHEDS=$(curl -s -X GET "${BASE_URL}/agents/${FIRST_AGENT}/script-schedules/" -H "${AUTH}")
  log_response "$AGENT_SCHEDS"
fi

# -----------------------------------------------------------------
# 14. GET: Standard tasks endpoint (agent.get_tasks_with_policies)
# -----------------------------------------------------------------
if [ "$AGENT_COUNT" -gt 0 ]; then
  FIRST_AGENT=$(echo "$AGENT_IDS" | jq -r '.[0]')
  echo ""
  echo ">>> 14. Standard tasks endpoint for agent..."
  log_request "GET" "${BASE_URL}/agents/${FIRST_AGENT}/tasks/"

  STANDARD_TASKS=$(curl -s -X GET "${BASE_URL}/agents/${FIRST_AGENT}/tasks/" -H "${AUTH}")
  TASK_COUNT=$(echo "$STANDARD_TASKS" | jq 'length')
  echo "    Total tasks: ${TASK_COUNT}"

  # Show only our schedule-created tasks (agent=null)
  echo -e "    ${YELLOW}Schedule tasks (agent=null):${NC}"
  echo "$STANDARD_TASKS" | jq '[.[] | select(.agent == null) | {id, name, task_type, enabled, status: .task_result.status, sync_status: .task_result.sync_status, last_run: .task_result.last_run, retcode: .task_result.retcode}]'
fi

# -----------------------------------------------------------------
# 15. PUT: Update schedule name
# -----------------------------------------------------------------
echo ""
echo ">>> 14. Update schedule (rename + change timeout)..."

UPDATE_BODY=$(cat <<EOF
{
  "name": "Renamed Run-Once Schedule",
  "task_type": "runonce",
  "run_time_date": "${RUN_DATE}",
  "actions": [
    {
      "type": "script",
      "script": ${SCRIPT_ID},
      "name": "${SCRIPT_NAME}",
      "timeout": 120,
      "script_args": [],
      "env_vars": []
    }
  ]
}
EOF
)

log_request "PUT" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/" "$UPDATE_BODY"

UPDATE_RESPONSE=$(curl -s -X PUT "${BASE_URL}/script-schedules/${SCHEDULE_ID}/" \
  -H "${AUTH}" \
  -H "Content-Type: application/json" \
  -d "${UPDATE_BODY}")

log_response "$UPDATE_RESPONSE"

# -----------------------------------------------------------------
# 16. DELETE: Clean up old schedules
# -----------------------------------------------------------------
echo ""
echo ">>> 16. Cleaning up created schedules..."
log_request "DELETE" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/"
curl -s -o /dev/null -w "    HTTP %{http_code}\n" -X DELETE "${BASE_URL}/script-schedules/${SCHEDULE_ID}/" -H "${AUTH}"

log_request "DELETE" "${BASE_URL}/script-schedules/${DAILY_ID}/"
curl -s -o /dev/null -w "    HTTP %{http_code}\n" -X DELETE "${BASE_URL}/script-schedules/${DAILY_ID}/" -H "${AUTH}"

echo "    Cleaned up."

# -----------------------------------------------------------------
# Summary
# -----------------------------------------------------------------
echo ""
echo "============================================"
echo " Summary"
echo "============================================"
echo "  Schedules created: 2 (run-once id=${SCHEDULE_ID}, daily id=${DAILY_ID})"
echo "  Agents assigned:   ${AGENT_IDS}"
echo "  Script used:       ${SCRIPT_NAME} (id=${SCRIPT_ID})"
echo ""
echo "  To delete:"
echo "    curl -X DELETE ${BASE_URL}/script-schedules/${SCHEDULE_ID}/ -H '${AUTH}'"
echo "    curl -X DELETE ${BASE_URL}/script-schedules/${DAILY_ID}/ -H '${AUTH}'"
echo ""
echo "  Done!"
