import { ref } from "vue"
import { fetchDebugLog } from "@/api/logs"
import { formatDate, formatTableColumnText } from "@/utils/format"

// debug log
export function useDebugLog() {

  const debugLog = ref([])
  const agentFilter = ref(null)
  const logLevelFilter = ref("info")
  const logTypeFilter = ref(null)

  const getDebugLog = async () => {
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
  { label: "Agent Update", value: "agent_value" },
  { label: "Agent Issues", value: "agent_issues" },
  { label: "Windows Updates", value: "windows_updates" },
  { label: "System Issues", value: "system_issues" },
  { label: "Scripting", value: "scripting" }
]

useDebugLog.debugLogTableColumns = [
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