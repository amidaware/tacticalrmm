
import { ref } from "vue"
import { fetchAgents } from "@/api/agents"
import { formatAgentOptions } from "@/utils/format"

export function useAgentDropdown() {

  const agentOptions = ref([])

  const getAgentOptions = async () => {
    agentOptions.value = formatAgentOptions(await fetchAgents())
  }

  return {
    //data
    agentOptions,

    //methods
    getAgentOptions
  }
}