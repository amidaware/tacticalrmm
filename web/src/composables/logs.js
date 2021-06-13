import { ref, watch, onMounted } from "vue"
import { fetchDebugLog } from "@/api/logs.js"

export function useDebugLog() {

  const debugLog = ref("")
  const logLevel = ref("info")
  const agent = ref("all")
  const order = ref("latest")

  const getDebugLog = async () => {
    debugLog.value = await fetchDebugLog(logLevel.value, agent.value, order.value)
  }

  watch(logLevel, getDebugLog)
  watch(agent, getDebugLog)
  watch(order, getDebugLog)

  onMounted(getDebugLog)

  return {
    //data
    logLevel,
    agent,
    order,
    debugLog,

    //methods
    getDebugLog
  }
}