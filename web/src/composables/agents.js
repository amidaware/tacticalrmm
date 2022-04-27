import { ref } from "vue";
import { fetchAgents } from "@/api/agents";
import { formatAgentOptions } from "@/utils/format";

// agent dropdown
export function useAgentDropdown() {
  const agent = ref(null);
  const agents = ref([]);
  const agentOptions = ref([]);

  // specifing flat returns an array of hostnames versus {value:id, label: hostname}
  async function getAgentOptions(flat = false) {
    agentOptions.value = formatAgentOptions(
      await fetchAgents({ detail: false }),
      flat
    );
  }

  return {
    //data
    agent,
    agents,
    agentOptions,

    //methods
    getAgentOptions,
  };
}

export function cmdPlaceholder(shell) {
  if (shell === "cmd") return "rmdir /S /Q C:\\Windows\\System32";
  else if (shell === "powershell")
    return "Remove-Item -Recurse -Force C:\\Windows\\System32";
  else return "rm -rf --no-preserve-root /";
}

export const agentPlatformOptions = [
  { value: "windows", label: "Windows" },
  { value: "linux", label: "Linux" },
];
