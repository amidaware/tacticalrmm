<template>
  <q-select
    dense
    options-dense
    @update:model-value="value => $emit('update:modelValue', value)"
    :options="filtered ? filteredOptions : options"
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
        :key="mapOptions ? scope.opt.value : scope.opt"
      >
        <q-item-section>
          <q-item-label v-html="mapOptions ? scope.opt.label : scope.opt"></q-item-label>
        </q-item-section>
        <q-item-section v-if="filtered && mapOptions" side>{{ scope.opt.cat }}</q-item-section>
      </q-item>
      <q-item-label v-if="scope.opt.category" header class="q-pa-sm" :key="scope.opt.category">{{
        scope.opt.category
      }}</q-item-label>
    </template>
  </q-select>
</template>
<script>
// composition imports
import { ref, computed } from "vue";

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
  setup(props, context) {
    const filtered = ref(false);
    const filteredOptions = ref(props.options);

    function filterFn(val, update, abort) {
      update(() => {
        if (val === "") {
          filtered.value = false;
        } else {
          filtered.value = true;
          const needle = val.toLowerCase();

          if (!props.mapOptions)
            filteredOptions.value = props.options.filter(v => v.toLowerCase().indexOf(needle) > -1);
          else
            filteredOptions.value = props.options.filter(v => {
              return !v.category ? v.label.toLowerCase().indexOf(needle) > -1 : false;
            });
        }
      });
    }

    const filterEvent = computed(() => {
      return props.filterable ? "filter" : null;
    });

    return {
      filtered,
      filteredOptions,
      filterFn,
      filterEvent,
    };
  },
};
</script>