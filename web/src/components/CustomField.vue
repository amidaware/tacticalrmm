<template>
  <q-input
    v-if="field.type === 'text' || field.type === 'number'"
    ref="input"
    outlined
    dense
    :label="field.name"
    :type="field.type === 'text' ? 'text' : 'number'"
    :hint="hintText(field)"
    :value="value"
    @input="value => $emit('input', value)"
    :rules="[...validationRules]"
    reactive-rules
  />

  <q-toggle
    v-else-if="field.type === 'checkbox'"
    ref="input"
    :label="field.name"
    :hint="hintText(field)"
    :value="value"
    @input="value => $emit('input', value)"
  />

  <q-input
    v-else-if="field.type === 'datetime'"
    ref="input"
    :label="field.name"
    :hint="hintText(field)"
    outlined
    dense
    :value="value"
    @input="value => $emit('input', value)"
    :rules="[...validationRules]"
    reactive-rules
  >
    <template v-slot:append>
      <q-icon name="event" class="cursor-pointer">
        <q-popup-proxy transition-show="scale" transition-hide="scale">
          <q-date :value="value" @input="value => $emit('input', value)" mask="YYYY-MM-DD HH:mm">
            <div class="row items-center justify-end">
              <q-btn v-close-popup label="Close" color="primary" flat />
            </div>
          </q-date>
        </q-popup-proxy>
      </q-icon>
      <q-icon name="access_time" class="cursor-pointer">
        <q-popup-proxy transition-show="scale" transition-hide="scale">
          <q-time :value="value" @input="value => $emit('input', value)" mask="YYYY-MM-DD HH:mm">
            <div class="row items-center justify-end">
              <q-btn v-close-popup label="Close" color="primary" flat />
            </div>
          </q-time>
        </q-popup-proxy>
      </q-icon>
    </template>
  </q-input>

  <q-select
    v-else-if="field.type === 'single' || field.type === 'multiple'"
    ref="input"
    :value="value"
    @input="value => $emit('input', value)"
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
export default {
  name: "CustomField",
  props: ["field", "value"],
  methods: {
    validate(...args) {
      return this.$refs.input.validate(...args);
    },
    hintText(field) {
      if (field.type === "multiple")
        return field.default_values_multiple.length > 0 ? `Default value: ${field.default_values_multiple}` : "";
      else if (field.type === "checkbox")
        return field.default_value_bool ? `Default value: ${field.default_value_bool}` : "";
      else return field.default_value_string ? `Default value: ${field.default_value_string}` : "";
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