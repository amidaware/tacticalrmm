
import { ref, unref } from "vue"

// used to filter dropdown options. Set flat to true id options are in ["option1", "option2"]
export function useDropdownFilter(options, flat = false) {
  const filteredOptions = ref([])

  function filterFn(val, update, abort) {

    update(() => {
      if (!val) {
        filteredOptions.value = unref(options);
      } else {
        const needle = val.toLowerCase();

        if (flat)
          filteredOptions.value = unref(options).filter(v => v.toLowerCase().indexOf(needle) > -1);
        else
          filteredOptions.value = unref(options).filter(v => {
            return !v.category ? v.label.toLowerCase().indexOf(needle) > -1 : false
          });
      }
    });
  }

  return {
    filteredOptions,
    filterFn
  }
}