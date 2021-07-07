import { ref, watch } from "vue"
import { fetchScripts } from "@/api/scripts"
import { formatScriptOptions } from "@/utils/format"

// script dropdown
export function useScriptDropdown() {

    const scriptOptions = ref([])
    const defaultTimeout = ref(30)
    const defaultArgs = ref([])
    const scriptPK = ref(null)

    // specifing flat returns an array of script names versus {value:id, label: hostname}
    async function getScriptOptions(showCommunityScripts = false, flat = false) {
        scriptOptions.value = formatScriptOptions(await fetchScripts({ showCommunityScripts }), flat)
    }

    // watch scriptPk for changes and update the default timeout and args
    watch(scriptPK, (newValue, oldValue) => {
        if (newValue) {
            const script = scriptOptions.value.find(i => i.value === newValue);
            defaultTimeout.value = script.timeout;
            defaultArgs.value = script.args;
        }
    })

    return {
        //data
        scriptPK,
        scriptOptions,
        defaultTimeout,
        defaultArgs,

        //methods
        getScriptOptions
    }
}
