<template>
  <q-select
    dense
    options-dense
    @update:model-value="value => $emit('update:modelValue', value)"
    :model-value="modelValue"
    :map-options="mapOptions"
    :emit-value="mapOptions"
    :multiple="multiple"
    :use-chips="multiple"
  >
    <template v-slot:option="scope">
      <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
        <q-item-section>
          <q-item-label v-html="mapOptions ? scope.opt.label : scope.opt"></q-item-label>
        </q-item-section>
      </q-item>
      <q-item-label v-if="scope.opt.category" header class="q-pa-sm">{{ scope.opt.category }}</q-item-label>
    </template>
  </q-select>
</template>
<script>
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
  },
};
</script>