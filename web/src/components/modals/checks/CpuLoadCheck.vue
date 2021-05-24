<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div v-if="mode === 'add'" class="text-h6">Add CPU Load Check</div>
      <div v-else-if="mode === 'edit'" class="text-h6">Edit CPU Load Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="mode === 'add' ? addCheck() : editCheck()">
      <q-card-section>
        <q-input
          outlined
          type="number"
          v-model.number="cpuloadcheck.warning_threshold"
          label="Warning Threshold (%)"
          :rules="[val => val >= 0 || 'Minimum threshold is 0', val => val < 100 || 'Maximum threshold is 99']"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          type="number"
          v-model.number="cpuloadcheck.error_threshold"
          label="Error Threshold (%)"
          :rules="[val => val >= 0 || 'Minimum threshold is 0', val => val < 100 || 'Maximum threshold is 99']"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          options-dense
          v-model="cpuloadcheck.fails_b4_alert"
          :options="failOptions"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          type="number"
          v-model.number="cpuloadcheck.run_interval"
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
  name: "CpuLoadCheck",
  emits: ["close"],
  props: {
    agentpk: Number,
    policypk: Number,
    mode: String,
    checkpk: Number,
  },
  mixins: [mixins],
  data() {
    return {
      cpuloadcheck: {
        check_type: "cpuload",
        warning_threshold: 70,
        error_threshold: 90,
        run_interval: 0,
        fails_b4_alert: 1,
      },
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  methods: {
    getCheck() {
      this.$axios
        .get(`/checks/${this.checkpk}/check/`)
        .then(r => (this.cpuloadcheck = r.data))
        .catch(e => {});
    },
    addCheck() {
      if (!this.isValidThreshold(this.cpuloadcheck.warning_threshold, this.cpuloadcheck.error_threshold)) {
        return;
      }

      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.cpuloadcheck,
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
      if (!this.isValidThreshold(this.cpuloadcheck.warning_threshold, this.cpuloadcheck.error_threshold)) {
        return;
      }

      this.$axios
        .patch(`/checks/${this.checkpk}/check/`, this.cpuloadcheck)
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
  mounted() {
    if (this.mode === "edit") {
      this.getCheck();
    }
  },
};
</script>