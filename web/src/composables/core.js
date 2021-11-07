
import { ref, onMounted } from "vue"
import { fetchCustomFields } from "@/api/core"
import { formatCustomFieldOptions } from "@/utils/format"

export function useCustomFieldDropdown({ onMount = false }) {

  const customFieldOptions = ref([])

  // type can be "client", "site", or "agent"
  async function getCustomFieldOptions(model = null, flat = false) {

    const params = {}

    if (model) params[model] = model
    customFieldOptions.value = formatCustomFieldOptions(await fetchCustomFields(params), flat)
  }

  if (onMount) onMounted(getCustomFieldOptions)

  return {
    //data
    customFieldOptions,

    //methods
    getCustomFieldOptions
  }
}
