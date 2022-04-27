import { ref, watch, computed, onMounted } from "vue";
import { useStore } from "vuex";
import { fetchScripts } from "@/api/scripts";
import { formatScriptOptions } from "@/utils/format";

// script dropdown
export function useScriptDropdown(setScript = null, { onMount = false } = {}) {
  const scriptOptions = ref([]);
  const defaultTimeout = ref(30);
  const defaultArgs = ref([]);
  const script = ref(setScript);
  const syntax = ref("");
  const link = ref("");
  const baseUrl =
    "https://github.com/amidaware/community-scripts/blob/main/scripts/";

  // specify parameters to filter out community scripts
  async function getScriptOptions(showCommunityScripts = false) {
    scriptOptions.value = Object.freeze(
      formatScriptOptions(await fetchScripts({ showCommunityScripts }))
    );
  }

  // watch scriptPk for changes and update the default timeout and args
  watch([script, scriptOptions], () => {
    if (script.value && scriptOptions.value.length > 0) {
      const tmpScript = scriptOptions.value.find(
        (i) => i.value === script.value
      );
      defaultTimeout.value = tmpScript.timeout;
      defaultArgs.value = tmpScript.args;
      syntax.value = tmpScript.syntax;
      link.value =
        tmpScript.script_type === "builtin"
          ? `${baseUrl}${tmpScript.filename}`
          : null;
    }
  });

  // vuex show community scripts
  const store = useStore();
  const showCommunityScripts = computed(() => store.state.showCommunityScripts);

  if (onMount) onMounted(() => getScriptOptions(showCommunityScripts.value));

  return {
    //data
    script,
    scriptOptions,
    defaultTimeout,
    defaultArgs,
    syntax,
    link,

    //methods
    getScriptOptions,
  };
}

export const shellOptions = [
  { label: "Powershell", value: "powershell" },
  { label: "Batch", value: "cmd" },
  { label: "Python", value: "python" },
  { label: "Shell", value: "shell" },
];
