#!/bin/bash
# =============================================================================
# Test script for Openframe Script Schedules API
# Usage: bash test_script_schedules.sh
# Requires: curl, jq
# =============================================================================

set -e

BASE_URL="http://tactical-nginx-0.tactical-nginx.integrated-tools.svc.cluster.local:8000"
USERNAME="tactical"
PASSWORD="tactical"

# Colors
RED='\033[0;31m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Globals set by do_curl
CURL_BODY=""
CURL_HTTP_CODE=""

do_curl() {
  local tmpfile
  tmpfile=$(mktemp)
  CURL_HTTP_CODE=$(curl -s -o "$tmpfile" -w "%{http_code}" "$@")
  CURL_BODY=$(cat "$tmpfile")
  rm -f "$tmpfile"
}

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
  local body="$1"
  local code="${2:-$CURL_HTTP_CODE}"
  if [ "$code" -ge 400 ] 2>/dev/null; then
    echo -e "    ${RED}HTTP ${code}${NC}"
  else
    echo -e "    ${GREEN}HTTP ${code}${NC}"
  fi
  if [ -n "$body" ]; then
    echo "$body" | jq '.' 2>/dev/null || echo "    $body"
  else
    echo "    (empty body)"
  fi
}

jq_field() {
  local json="$1"
  local field="$2"
  echo "$json" | jq -r "${field} // empty" 2>/dev/null
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

do_curl -X POST "${BASE_URL}/v2/login/" \
  -H "Content-Type: application/json" \
  -d "${LOGIN_BODY}"

TOKEN=$(jq_field "$CURL_BODY" '.token')

if [ -z "$TOKEN" ]; then
  echo "    Failed to get token."
  log_response "$CURL_BODY"
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

do_curl -X GET "${BASE_URL}/agents/" -H "${AUTH}"
AGENTS_RESPONSE="$CURL_BODY"
AGENT_COUNT=$(echo "$AGENTS_RESPONSE" | jq 'length' 2>/dev/null || echo 0)
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

do_curl -X GET "${BASE_URL}/scripts/" -H "${AUTH}"
SCRIPTS_RESPONSE="$CURL_BODY"
SCRIPT_COUNT=$(echo "$SCRIPTS_RESPONSE" | jq 'length' 2>/dev/null || echo 0)
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

do_curl -X POST "${BASE_URL}/script-schedules/" \
  -H "${AUTH}" \
  -H "Content-Type: application/json" \
  -d "${CREATE_BODY}"
CREATE_RESPONSE="$CURL_BODY"

SCHEDULE_ID=$(jq_field "$CREATE_RESPONSE" '.id')
TASK_ID=$(jq_field "$CREATE_RESPONSE" '.managed_task_id')

echo "    Created schedule id=${SCHEDULE_ID}, managed_task_id=${TASK_ID}"
log_response "$CREATE_RESPONSE"

if [ -z "$SCHEDULE_ID" ]; then
  echo -e "    ${RED}ERROR: Failed to create run-once schedule. Cannot continue.${NC}"
  exit 1
fi

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

do_curl -X POST "${BASE_URL}/script-schedules/" \
  -H "${AUTH}" \
  -H "Content-Type: application/json" \
  -d "${DAILY_BODY}"
DAILY_RESPONSE="$CURL_BODY"

DAILY_ID=$(jq_field "$DAILY_RESPONSE" '.id')
echo "    Created daily schedule id=${DAILY_ID}"
log_response "$DAILY_RESPONSE"

if [ -z "$DAILY_ID" ]; then
  echo -e "    ${RED}ERROR: Failed to create daily schedule. Cannot continue.${NC}"
  exit 1
fi

# -----------------------------------------------------------------
# 6. Assign agents to the run-once schedule
# -----------------------------------------------------------------
echo ""
echo ">>> 6. Assigning agents to schedule ${SCHEDULE_ID}..."

ASSIGN_BODY="{\"agents\": ${AGENT_IDS}}"

if [ "$AGENT_COUNT" -gt 0 ]; then
  log_request "POST" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/" "$ASSIGN_BODY"

  do_curl -X POST "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/" \
    -H "${AUTH}" \
    -H "Content-Type: application/json" \
    -d "${ASSIGN_BODY}"

  log_response "$CURL_BODY"
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

  do_curl -X POST "${BASE_URL}/script-schedules/${DAILY_ID}/agents/" \
    -H "${AUTH}" \
    -H "Content-Type: application/json" \
    -d "${ASSIGN_BODY}"

  log_response "$CURL_BODY"
else
  echo "    Skipped — no agents"
fi

# -----------------------------------------------------------------
# 8. GET: List all schedules
# -----------------------------------------------------------------
echo ""
echo ">>> 8. List all schedules..."
log_request "GET" "${BASE_URL}/script-schedules/"

do_curl -X GET "${BASE_URL}/script-schedules/" -H "${AUTH}"
log_response "$CURL_BODY"

# -----------------------------------------------------------------
# 9. GET: Schedule detail
# -----------------------------------------------------------------
echo ""
echo ">>> 9. Schedule detail..."
log_request "GET" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/"

do_curl -X GET "${BASE_URL}/script-schedules/${SCHEDULE_ID}/" -H "${AUTH}"
log_response "$CURL_BODY"

# -----------------------------------------------------------------
# 10. GET: Agents of schedule
# -----------------------------------------------------------------
echo ""
echo ">>> 10. Agents of schedule..."
log_request "GET" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/"

do_curl -X GET "${BASE_URL}/script-schedules/${SCHEDULE_ID}/agents/" -H "${AUTH}"
log_response "$CURL_BODY"

# -----------------------------------------------------------------
# 11. GET: Execution history
# -----------------------------------------------------------------
echo ""
echo ">>> 11. Execution history..."
log_request "GET" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/history/?limit=10"

do_curl -X GET "${BASE_URL}/script-schedules/${SCHEDULE_ID}/history/?limit=10" -H "${AUTH}"
log_response "$CURL_BODY"

# -----------------------------------------------------------------
# 12. GET: Schedules for script (reverse lookup)
# -----------------------------------------------------------------
echo ""
echo ">>> 12. Schedules for script (reverse lookup)..."
log_request "GET" "${BASE_URL}/scripts/${SCRIPT_ID}/schedules/"

do_curl -X GET "${BASE_URL}/scripts/${SCRIPT_ID}/schedules/" -H "${AUTH}"
log_response "$CURL_BODY"

# -----------------------------------------------------------------
# 13. GET: Schedules for agent (reverse lookup)
# -----------------------------------------------------------------
if [ "$AGENT_COUNT" -gt 0 ]; then
  FIRST_AGENT=$(echo "$AGENT_IDS" | jq -r '.[0]')
  echo ""
  echo ">>> 13. Schedules for agent (reverse lookup)..."
  log_request "GET" "${BASE_URL}/agents/${FIRST_AGENT}/script-schedules/"

  do_curl -X GET "${BASE_URL}/agents/${FIRST_AGENT}/script-schedules/" -H "${AUTH}"
  log_response "$CURL_BODY"
fi

# -----------------------------------------------------------------
# 14. GET: Standard tasks endpoint (agent.get_tasks_with_policies)
# -----------------------------------------------------------------
if [ "$AGENT_COUNT" -gt 0 ]; then
  FIRST_AGENT=$(echo "$AGENT_IDS" | jq -r '.[0]')
  echo ""
  echo ">>> 14. Standard tasks endpoint for agent..."
  log_request "GET" "${BASE_URL}/agents/${FIRST_AGENT}/tasks/"

  do_curl -X GET "${BASE_URL}/agents/${FIRST_AGENT}/tasks/" -H "${AUTH}"
  STANDARD_TASKS="$CURL_BODY"
  TASK_COUNT=$(echo "$STANDARD_TASKS" | jq 'length' 2>/dev/null || echo 0)
  echo "    Total tasks: ${TASK_COUNT}"

  # Show only our schedule-created tasks (agent=null)
  echo -e "    ${YELLOW}Schedule tasks (agent=null):${NC}"
  echo "$STANDARD_TASKS" | jq '[.[] | select(.agent == null) | {id, name, task_type, enabled, status: .task_result.status, sync_status: .task_result.sync_status, last_run: .task_result.last_run, retcode: .task_result.retcode}]'
fi

# -----------------------------------------------------------------
# 15. PUT: Update schedule name
# -----------------------------------------------------------------
echo ""
echo ">>> 15. Update schedule (rename + change timeout)..."

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

do_curl -X PUT "${BASE_URL}/script-schedules/${SCHEDULE_ID}/" \
  -H "${AUTH}" \
  -H "Content-Type: application/json" \
  -d "${UPDATE_BODY}"

log_response "$CURL_BODY"

# -----------------------------------------------------------------
# 16. DELETE: Clean up old schedules
# -----------------------------------------------------------------
echo ""
echo ">>> 16. Cleaning up created schedules..."
log_request "DELETE" "${BASE_URL}/script-schedules/${SCHEDULE_ID}/"
do_curl -X DELETE "${BASE_URL}/script-schedules/${SCHEDULE_ID}/" -H "${AUTH}"
log_response "$CURL_BODY"

log_request "DELETE" "${BASE_URL}/script-schedules/${DAILY_ID}/"
do_curl -X DELETE "${BASE_URL}/script-schedules/${DAILY_ID}/" -H "${AUTH}"
log_response "$CURL_BODY"

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
