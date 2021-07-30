<template>
  <q-select
    dense
    options-dense
    @update:model-value="value => $emit('update:modelValue', value)"
    :options="filterable ? filteredOptions : options"
    :model-value="modelValue"
    :map-options="mapOptions"
    :emit-value="mapOptions"
    :multiple="multiple"
    :use-chips="multiple"
    :use-input="filterable"
    @[filterEvent]="filterFn"
  >
    <template v-slot:option="scope">
      <q-item
        v-if="!scope.opt.category"
        v-bind="scope.itemProps"
        class="q-pl-lg"
        :key="mapOptions ? scope.opt.value : null"
      >
        <q-item-section>
          <q-item-label v-html="mapOptions ? scope.opt.label : scope.opt"></q-item-label>
        </q-item-section>
      </q-item>
      <q-item-label v-if="scope.opt.category" header class="q-pa-sm" :key="scope.opt.category">{{
        scope.opt.category
      }}</q-item-label>
    </template>
  </q-select>
</template>
<script>
// composition imports
import { toRefs, computed } from "vue";
import { useDropdownFilter } from "@/composables/quasar";

export default {
  name: "tactical-dropdown",
  props: {
    modelValue: !String,
    mapOptions: {
      type: Boolean,
      default: false,
    },
    multiple: {
      type: Boolean,
      default: false,
    },
    filterable: {
      type: Boolean,
      default: false,
    },
    options: !Array,
  },
  setup(props) {
    const { options } = toRefs(props);
    const { filterFn, filteredOptions } = useDropdownFilter(options, !props.mapOptions);

    const filterEvent = computed(() => {
      return props.filterable ? "filter" : null;
    });

    return {
      filterFn,
      filteredOptions,
      filterEvent,
    };
  },
};
</script>