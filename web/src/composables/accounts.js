
import { ref, onMounted } from "vue"
import { fetchUsers } from "@/api/accounts"
import { formatUserOptions } from "@/utils/format"

export function useUserDropdown(onMount = false) {

  const userOptions = ref([])
  const userDropdownLoading = ref(false)

  async function getUserOptions(flat = false) {
    userOptions.value = formatUserOptions(await fetchUsers(), flat)
  }

  function getDynamicUserOptions(val, update, abort) {
    if (!val || val.length < 2) {
      abort()
      return
    }

    update(async () => {
      userDropdownLoading.value = true

      const params = {
        search: val.toLowerCase()
      }

      const options = await fetchUsers(params)

      userOptions.value = options.map(user => user.username)
      userDropdownLoading.value = false
    })
  }

  if (onMount) {
    onMounted(getUserOptions())
  }

  return {
    //data
    userOptions,
    userDropdownLoading,

    //methods
    getUserOptions,
    getDynamicUserOptions
  }
}
