import { ref, watch } from "vue"
import { fetchScripts } from "@/api/scripts"
import { formatScriptOptions } from "@/utils/format"

// script dropdown
export function useScriptDropdown(setScript = null) {
  const scriptOptions = ref([])
  const defaultTimeout = ref(30)
  const defaultArgs = ref([])
  const script = ref(setScript)

  // specifing flat returns an array of script names versus {value:id, label: hostname}
  async function getScriptOptions(showCommunityScripts = false, flat = false) {
    scriptOptions.value = formatScriptOptions(await fetchScripts({ showCommunityScripts }), flat)
  }

  // watch scriptPk for changes and update the default timeout and args
  watch([script, scriptOptions], (newValue, oldValue) => {
    if (script.value && scriptOptions.value.length > 0) {
      const tmpScript = scriptOptions.value.find(i => i.value === script.value);
      defaultTimeout.value = tmpScript.timeout;
      defaultArgs.value = tmpScript.args;
    }
  })

  return {
    //data
    script,
    scriptOptions,
    defaultTimeout,
    defaultArgs,

    //methods
    getScriptOptions
  }
}

export const shellOptions = [
  { label: "Powershell", value: "powershell" },
  { label: "Batch", value: "cmd" },
  { label: "Python", value: "python" },
];