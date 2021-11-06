
import { ref, onMounted } from "vue"
import { fetchClients } from "@/api/clients"
import { formatClientOptions, formatSiteOptions } from "@/utils/format"

export function useClientDropdown(onMount = false) {
  const client = ref(null)
  const clients = ref([])
  const clientOptions = ref([])

  async function getClientOptions(flat = false) {
    clientOptions.value = formatClientOptions(await fetchClients(), flat)
  }

  if (onMount) onMounted(getClientOptions)

  return {
    //data
    client,
    clients,
    clientOptions,

    //methods
    getClientOptions
  }
}

export function useSiteDropdown(onMount = false) {
  const site = ref(null)
  const sites = ref([])
  const siteOptions = ref([])

  async function getSiteOptions() {
    siteOptions.value = formatSiteOptions(await fetchClients())
  }

  if (onMount) onMounted(getSiteOptions)

  return {
    //data
    site,
    sites,
    siteOptions,

    //methods
    getSiteOptions
  }
}