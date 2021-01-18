<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div v-if="mode === 'add'" class="text-h6">Add Ping Check</div>
      <div v-else-if="mode === 'edit'" class="text-h6">Edit Ping Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="mode === 'add' ? addCheck() : editCheck()">
      <q-card-section>
        <q-input outlined v-model="pingcheck.name" label="Descriptive Name" :rules="[val => !!val || '*Required']" />
      </q-card-section>
      <q-card-section>
        <q-input outlined v-model="pingcheck.ip" label="Hostname or IP" :rules="[val => !!val || '*Required']" />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          options-dense
          v-model="pingcheck.alert_severity"
          :options="severityOptions"
          label="Alert Severity"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          options-dense
          map-options
          emit-value
          v-model="pingcheck.fails_b4_alert"
          :options="failOptions"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn v-if="mode === 'add'" label="Add" color="primary" type="submit" />
        <q-btn v-else-if="mode === 'edit'" label="Edit" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "PingCheck",
  props: {
    agentpk: Number,
    policypk: Number,
    mode: String,
    checkpk: Number,
  },
  mixins: [mixins],
  data() {
    return {
      pingcheck: {
        check_type: "ping",
        name: null,
        ip: null,
        alert_severity: "warning",
        fails_b4_alert: 1,
      },
      severityOptions: [
        { label: "Informational", value: "info" },
        { label: "Warning", value: "warning" },
        { label: "Error", value: "error" },
      ],
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  methods: {
    getCheck() {
      axios.get(`/checks/${this.checkpk}/check/`).then(r => (this.pingcheck = r.data));
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.pingcheck,
      };
      axios
        .post("/checks/checks/", data)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.non_field_errors));
    },
    editCheck() {
      axios
        .patch(`/checks/${this.checkpk}/check/`, this.pingcheck)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.non_field_errors));
    },
    reloadChecks() {
      if (this.policypk) {
        this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
      } else {
        this.$store.dispatch("loadChecks", this.agentpk);
      }
    },
  },
  created() {
    if (this.mode === "edit") {
      this.getCheck();
    }
  },
};
</script>