import { ref, computed, watch } from "vue"
import { useQuasar } from "quasar"
import { fetchDebugLog, fetchAuditLog } from "@/api/logs"
import { formatDate, formatTableColumnText } from "@/utils/format"
import AuditLogDetailModal from "@/components/logs/AuditLogDetailModal";

// debug log
export function useDebugLog() {

  const debugLog = ref([])
  const agentFilter = ref(null)
  const logLevelFilter = ref("info")
  const logTypeFilter = ref(null)

  async function getDebugLog() {
    const data = {
      logLevelFilter: logLevelFilter.value
    }
    if (agentFilter.value) data["agentFilter"] = agentFilter.value
    if (logTypeFilter.value) data["logTypeFilter"] = logTypeFilter.value

    debugLog.value = await fetchDebugLog(data)
  }

  return {
    // data
    logLevelFilter,
    logTypeFilter,
    agentFilter,
    debugLog,

    // methods
    getDebugLog
  }
}

useDebugLog.logTypeOptions = [
  { label: "Agent Update", value: "agent_update" },
  { label: "Agent Issues", value: "agent_issues" },
  { label: "Windows Updates", value: "windows_updates" },
  { label: "System Issues", value: "system_issues" },
  { label: "Scripting", value: "scripting" }
]

useDebugLog.tableColumns = [
  {
    name: "entry_time",
    label: "Time",
    field: "entry_time",
    align: "left",
    sortable: true,
    format: (val, row) => formatDate(val, true),
  },
  { name: "log_level", label: "Log Level", field: "log_level", align: "left", sortable: true },
  { name: "agent", label: "Agent", field: "agent", align: "left", sortable: true },
  {
    name: "log_type",
    label: "Log Type",
    field: "log_type",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  },
  { name: "message", label: "Message", field: "message", align: "left", sortable: true },
]

// audit Log
export function useAuditLog() {
  const auditLogs = ref([])
  const agentFilter = ref(null)
  const userFilter = ref(null)
  const actionFilter = ref(null)
  const clientFilter = ref(null)
  const objectFilter = ref(null)
  const timeFilter = ref(7)
  const filterType = ref("clients")
  const loading = ref(false)
  const searched = ref(false)

  const pagination = ref({
    rowsPerPage: 25,
    rowsNumber: null,
    sortBy: "entry_time",
    descending: true,
    page: 1,
  })

  async function search() {
    loading.value = true
    searched.value = true;

    const data = {
      pagination: pagination.value
    };

    if (!!agentFilter.value && agentFilter.value.length > 0) data["agentFilter"] = agentFilter.value;
    else if (!!clientFilter.value && clientFilter.value.length > 0) data["clientFilter"] = clientFilter.value;
    if (!!userFilter.value && userFilter.value.length > 0) data["userFilter"] = userFilter.value;
    if (!!timeFilter.value) data["timeFilter"] = timeFilter.value;
    if (!!actionFilter.value && actionFilter.value.length > 0) data["actionFilter"] = actionFilter.value;
    if (!!objectFilter.value && objectFilter.value.length > 0) data["objectFilter"] = objectFilter.value;

    const { audit_logs, total } = await fetchAuditLog(data)
    auditLogs.value = audit_logs
    pagination.value.rowsNumber = total

    loading.value = false
  }

  function onRequest(props) {
    const { page, rowsPerPage, sortBy, descending } = props.pagination;

    pagination.value.page = page;
    pagination.value.rowsPerPage = rowsPerPage;
    pagination.value.sortBy = sortBy;
    pagination.value.descending = descending;

    search();
  }

  const { dialog } = useQuasar()
  function openAuditDetail(evt, log) {
    dialog({
      component: AuditLogDetailModal,
      componentProps: {
        log
      }
    })
  }

  function formatActionColor(action) {
    if (action === "add") return "success";
    else if (action === "agent_install") return "success";
    else if (action === "modify") return "warning";
    else if (action === "delete") return "negative";
    else if (action === "failed_login") return "negative";
    else return "primary";
  }

  watch(filterType, () => {
    agentFilter.value = null
    clientFilter.value = null
  })

  const noDataText = computed(() => searched ? "No data found. Try to refine you search" : "Click search to find audit logs")

  return {
    // data
    auditLogs,
    agentFilter,
    userFilter,
    actionFilter,
    clientFilter,
    objectFilter,
    timeFilter,
    filterType,
    loading,
    searched,
    pagination,

    //computed
    noDataText,

    // methods
    search,
    onRequest,
    openAuditDetail,
    formatActionColor
  }
}

useAuditLog.tableColumns = [
  {
    name: "entry_time",
    label: "Time",
    field: "entry_time",
    align: "left",
    sortable: true,
    format: (val, row) => formatDate(val, true),
  },
  { name: "username", label: "Username", field: "username", align: "left", sortable: true },
  { name: "agent", label: "Agent", field: "agent", align: "left", sortable: true },
  {
    name: "action",
    label: "Action",
    field: "action",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val)
  },
  {
    name: "object_type",
    label: "Object",
    field: "object_type",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  },
  { name: "message", label: "Message", field: "message", align: "left", sortable: true },
]

useAuditLog.actionOptions = [
  { value: "agent_install", label: "Agent Installs" },
  { value: "add", label: "Add Object" },
  { value: "bulk_action", label: "Bulk Actions" },
  { value: "check_run", label: "Check Run Results" },
  { value: "execute_command", label: "Execute Command" },
  { value: "execute_script", label: "Execute Script" },
  { value: "delete", label: "Delete Object" },
  { value: "failed_login", label: "Failed User login" },
  { value: "login", label: "User Login" },
  { value: "modify", label: "Modify Object" },
  { value: "remote_session", label: "Remote Session" },
  { value: "task_run", label: "Task Run Results" },
]

useAuditLog.objectOptions = [
  { value: "agent", label: "Agent" },
  { value: "automatedtask", label: "Automated Task" },
  { value: "bulk", label: "Bulk Actions" },
  { value: "coresettings", label: "Core Settings" },
  { value: "check", label: "Check" },
  { value: "client", label: "Client" },
  { value: "policy", label: "Policy" },
  { value: "site", label: "Site" },
  { value: "script", label: "Script" },
  { value: "user", label: "User" },
  { value: "winupdatepolicy", label: "Patch Policy" },
]

useAuditLog.timeOptions = [
  { value: 1, label: "1 Day Ago" },
  { value: 7, label: "1 Week Ago" },
  { value: 30, label: "30 Days Ago" },
  { value: 90, label: "3 Months Ago" },
  { value: 180, label: "6 Months Ago" },
  { value: 365, label: "1 Year Ago" },
  { value: 0, label: "Everything" },
]

useAuditLog.filterTypeOptions = [
  {
    label: "Clients",
    value: "clients",
  },
  {
    label: "Agents",
    value: "agents",
  },
]