<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Edit Script Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="editScriptCheck">
      <q-card-section>
        <q-select dense outlined v-model="scriptName" disable label="Select script" />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          dense
          v-model.number="timeout"
          label="Timeout (seconds)"
          :rules="[ 
              val => !!val || '*Required',
              val => val >= 10 || 'Minimum is 10 seconds',
              val => val <= 86400 || 'Maximum is 86400 seconds'
          ]"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          v-model="failure"
          :options="failures"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn label="Edit" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "EditScriptCheck",
  props: ["agentpk", "policypk", "editCheckPK"],
  mixins: [mixins],
  data() {
    return {
      scriptName: null,
      failure: null,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      timeout: null
    };
  },
  methods: {
    getScriptCheck() {
      axios
        .get(`/checks/getstandardcheck/script/${this.editCheckPK}/`)
        .then(r => {
          this.failure = r.data.failures;
          this.timeout = r.data.timeout;
          this.scriptName = r.data.script.name;
        });
    },
    editScriptCheck() {
      const data = {
        pk: this.editCheckPK,
        check_type: "script",
        failures: this.failure,
        timeout: this.timeout
      };
      axios
        .patch("/checks/editstandardcheck/", data)
        .then(r => {
          this.$emit("close");

          if (this.policypk) {
            this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
          } else {
            this.$store.dispatch("loadChecks", this.agentpk);
          }
          
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  created() {
    this.getScriptCheck();
  }
};
</script>