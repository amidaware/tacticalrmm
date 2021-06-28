
import { ref } from "vue"
import { fetchAgents } from "@/api/agents"
import { formatAgentOptions } from "@/utils/format"

export function useAgentDropdown() {

  const agentOptions = ref([])

  // specifing flat returns an array of hostnames versus {value:id, label: hostname}
  async function getAgentOptions(flat = false) {
    agentOptions.value = formatAgentOptions(await fetchAgents(), flat)
  }

  return {
    //data
    agentOptions,

    //methods
    getAgentOptions
  }
}