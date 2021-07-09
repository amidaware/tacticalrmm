
import { ref } from "vue"
import { fetchCustomFields } from "@/api/core"
import { formatCustomFieldOptions } from "@/utils/format"

export function useCustomFieldDropdown() {

  const customFieldOptions = ref([])

  // type can be "client", "site", or "agent"
  async function getCustomFieldOptions(model = null, flat = false) {

    const params = {}

    if (model) params[model] = model
    customFieldOptions.value = formatCustomFieldOptions(await fetchCustomFields(params), flat)
  }

  return {
    //data
    customFieldOptions,

    //methods
    getCustomFieldOptions
  }
}
