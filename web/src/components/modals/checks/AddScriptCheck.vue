<template>
  <q-card v-if="scripts.length === 0" style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Script Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section>
      <p>You need to upload a script first</p>
      <p>Settings -> Script Manager</p>
    </q-card-section>
  </q-card>
  <q-card v-else style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Script Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="addScriptCheck">
      <q-card-section>
        <q-select
          :rules="[val => !!val || '*Required']"
          dense
          outlined
          v-model="scriptName"
          :options="scriptOptions"
          label="Select script"
        />
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
        <q-btn label="Add" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "AddScriptCheck",
  props: ["agentpk", "policypk"],
  mixins: [mixins],
  data() {
    return {
      scriptName: null,
      failure: 1,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      timeout: 120
    };
  },
  methods: {
    getScripts() {
      this.$store.dispatch("getScripts");
    },
    addScriptCheck() {
      pk = (this.policypk) ? {policy: policypk} : {pk: agentpk}

      const data = {
        ...pk,
        check_type: "script",
        scriptPk: this.scriptPk,
        timeout: this.timeout,
        failures: this.failure
      };
      axios
        .post("/checks/addstandardcheck/", data)
        .then(r => {
          this.$emit("close");

          if (this.policypk) {
            this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
          } else {
            this.$store.dispatch("loadChecks", this.agentpk);
          }
          
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data));
    }
  },
  computed: {
    ...mapGetters(["scripts"]),
    scriptOptions() {
      return this.scripts.map(k => k.name).sort();
    },
    scriptPk(name) {
      return this.scripts.filter(k => k.name === this.scriptName)[0].id;
    }
  },
  created() {
    this.getScripts();
  }
};
</script>