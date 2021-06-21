
import { ref } from "vue"
import { fetchClients } from "@/api/clients"
import { formatClientOptions, formatSiteOptions } from "@/utils/format"

export function useClientDropdown() {

  const clientOptions = ref([])

  async function getClientOptions(flat = false) {
    clientOptions.value = formatClientOptions(await fetchClients(), flat)
  }

  return {
    //data
    clientOptions,

    //methods
    getClientOptions
  }
}

export function useSiteDropdown() {
  const siteOptions = ref([])

  async function getSiteOptions() {
    siteOptions.value = formatSiteOptions(await fetchSites())
  }

  return {
    //data
    siteOptions,

    //methods
    getSiteOptions
  }
}