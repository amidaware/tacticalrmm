<template>
  <q-input
    v-if="field.type === 'text'"
    ref="input"
    outlined
    dense
    :label="field.name"
    type="text"
    :value="value"
    @input="value => $emit('input', value)"
    :rules="[...validationRules]"
    reactive-rules
  />

  <q-input
    v-else-if="field.type === 'number'"
    ref="input"
    outlined
    dense
    :label="field.name"
    type="number"
    :value="value"
    @input="value => $emit('input', value)"
    :rules="[...validationRules]"
    reactive-rules
  />

  <q-toggle
    v-else-if="field.type === 'checkbox'"
    :label="field.name"
    :value="value"
    @input="value => $emit('input', value)"
  />

  <q-input v-else-if="field.type === 'datetime'" outlined dense :value="value" @input="value => $emit('input', value)">
    <template v-slot:append>
      <q-icon name="event" class="cursor-pointer">
        <q-popup-proxy transition-show="scale" transition-hide="scale">
          <q-date v-model="value" mask="YYYY-MM-DD HH:mm">
            <div class="row items-center justify-end">
              <q-btn v-close-popup label="Close" color="primary" flat />
            </div>
          </q-date>
        </q-popup-proxy>
      </q-icon>
      <q-icon name="access_time" class="cursor-pointer">
        <q-popup-proxy transition-show="scale" transition-hide="scale">
          <q-time v-model="value" mask="YYYY-MM-DD HH:mm">
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
    :value="value"
    @input="value => $emit('input', value)"
    outlined
    dense
    :options="field.options"
    :multiple="field.type === 'multiple'"
    :rules="[...validationRules]"
    reactive-rules
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