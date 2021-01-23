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
          v-model.number="cpuloadcheck.warning_threshold"
          label="Warning Threshold (%)"
          :rules="[
            val => !!val || '*Required',
            val => val >= 1 || 'Minimum threshold is 1',
            val => val < 100 || 'Maximum threshold is 99',
          ]"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          v-model.number="cpuloadcheck.error_threshold"
          label="Error Threshold (%)"
          :rules="[
            val => !!val || '*Required',
            val => val >= 1 || 'Minimum threshold is 1',
            val => val < 100 || 'Maximum threshold is 99',
          ]"
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
  name: "CpuLoadCheck",
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
        fails_b4_alert: 1,
      },
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  computed: {
    thresholdIsValid() {
      return (
        this.cpuloadcheck.warning_threshold === 0 ||
        this.cpuloadcheck.error_threshold === 0 ||
        this.cpuloadcheck.warning_threshold < this.cpuloadcheck.error_threshold
      );
    },
  },
  methods: {
    getCheck() {
      axios.get(`/checks/${this.checkpk}/check/`).then(r => (this.cpuloadcheck = r.data));
    },
    addCheck() {
      if (!this.thresholdIsValid) {
        this.notifyError("Warning Threshold needs to be less than Error threshold");
        return;
      }

      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.cpuloadcheck,
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
      if (!this.thresholdIsValid) {
        this.notifyError("Warning Threshold needs to be less than Error threshold");
        return;
      }

      axios
        .patch(`/checks/${this.checkpk}/check/`, this.cpuloadcheck)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.non_field_errors));
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