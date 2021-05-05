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
          emit-value
          map-options
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
      <q-card-section>
        <q-input
          outlined
          dense
          type="number"
          v-model.number="pingcheck.run_interval"
          label="Run this check every (seconds)"
          hint="Setting this value to anything other than 0 will override the 'Run checks every' setting on the agent"
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
        run_interval: 0,
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
      this.$axios
        .get(`/checks/${this.checkpk}/check/`)
        .then(r => (this.pingcheck = r.data))
        .catch(e => {});
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.pingcheck,
      };
      this.$axios
        .post("/checks/checks/", data)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => {});
    },
    editCheck() {
      this.$axios
        .patch(`/checks/${this.checkpk}/check/`, this.pingcheck)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => {});
    },
    reloadChecks() {
      if (this.agentpk) {
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