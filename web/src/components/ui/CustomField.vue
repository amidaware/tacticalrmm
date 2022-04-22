<template>
  <q-input
    :class="longTextClass(field)"
    v-if="field.type === 'text' || field.type === 'number'"
    ref="input"
    outlined
    dense
    :label="field.name"
    :type="field.type === 'text' ? 'text' : 'number'"
    :hint="hintText(field)"
    :model-value="modelValue"
    @update:model-value="value => $emit('update:modelValue', value)"
    :rules="[...validationRules]"
    reactive-rules
    autogrow
  />

  <q-toggle
    v-else-if="field.type === 'checkbox'"
    ref="input"
    :label="field.name"
    :hint="hintText(field)"
    :model-value="modelValue"
    @update:model-value="value => $emit('update:modelValue', value)"
  />

  <q-input
    v-else-if="field.type === 'datetime'"
    :label="field.name"
    :hint="hintText(field)"
    ref="input"
    type="datetime-local"
    dense
    stack-label
    outlined
    :model-value="modelValue"
    @update:model-value="value => $emit('update:modelValue', value)"
    :rules="[...validationRules]"
    reactive-rules
  />

  <q-select
    v-else-if="field.type === 'single' || field.type === 'multiple'"
    ref="input"
    :model-value="modelValue"
    @update:model-value="value => $emit('update:modelValue', value)"
    outlined
    dense
    :hint="hintText(field)"
    :label="field.name"
    :options="field.options"
    :multiple="field.type === 'multiple'"
    :rules="[...validationRules]"
    reactive-rules
    clearable
  />
</template>

<script>
import { truncateText } from "@/utils/format";
export default {
  name: "CustomField",
  props: ["field", "modelValue"],
  methods: {
    validate(...args) {
      return this.$refs.input.validate(...args);
    },
    hintText(field) {
      let value = "";
      if (field.type === "multiple")
        value = field.default_values_multiple.length > 0 ? `Default value: ${field.default_values_multiple}` : "";
      else if (field.type === "checkbox")
        value = field.default_value_bool ? `Default value: ${field.default_value_bool}` : "";
      else value = field.default_value_string ? `Default value: ${field.default_value_string}` : "";

      return value.length > 100 ? truncateText(value, 100) : value;
    },
    longTextClass(field) {
      return field.hasOwnProperty("default_value_string") && field.default_value_string.length >= 130
        ? "q-mb-xl q-mt-xl"
        : "";
    },
  },
  computed: {
    validationRules() {
      const rules = [];

      if (this.field.required) {
        rules.push(val => !!val || `${this.field.name} is required`);
      }

      return rules;
    },
  },
};
</script>