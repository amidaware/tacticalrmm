<template>
  <q-card style="width: 60vw" >
    <q-card-section class="row items-center">
      <div class="text-h6">{{ this.description }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section>
    <q-list bordered separator>
      <q-item>
        <q-item-section>Single line item</q-item-section>
      </q-item>
    </q-list>
    </q-card-section>
  </q-card>
</template>

<script>
import { mapState } from "vuex";

export default {
  name: "PolicyStatus",
  props: {
    item: {
      required: true,
      type: Object
    },
    type: {
      required: true,
      type: String,
      validator: function (value) {
        // The value must match one of these strings
        return ["task", "check"].includes(value);
      }
    },
    description: {
      type: String
    }
  },
  data() {
    return {
      checkData: []
    }
  },
  methods: {
    getCheckData() {

    }
  },
  computed: {
    ...mapState({
      selectedPolicyId: state => state.automation.selectedPolicyId
    }),
  },
  mounted() {
    this.getCheckData();
  }
}
</script>
