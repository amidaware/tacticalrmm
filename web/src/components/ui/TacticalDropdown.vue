<template>
  <q-select
    dense
    options-dense
    outlined
    @update:model-value="value => $emit('update:modelValue', value)"
    :model-value="modelValue"
    map-options
    emit-value
  >
    <template v-slot:option="scope">
      <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
        <q-item-section>
          <q-item-label v-html="scope.opt.label"></q-item-label>
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
  },
};
</script>