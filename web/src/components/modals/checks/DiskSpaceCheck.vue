<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div v-if="mode === 'add'" class="text-h6">Add Disk Space Check</div>
      <div v-else-if="mode === 'edit'" class="text-h6">Edit Disk Space Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="mode === 'add' ? addCheck() : editCheck()">
      <q-card-section>
        <q-select
          :disable="this.mode === 'edit'"
          outlined
          v-model="diskcheck.disk"
          :options="diskOptions"
          label="Disk"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          type="number"
          v-model.number="diskcheck.warning_threshold"
          label="Warning Threshold Remaining (%)"
          :rules="[val => val >= 0 || 'Minimum threshold is 0', val => val < 100 || 'Maximum threshold is 99']"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          type="number"
          v-model.number="diskcheck.error_threshold"
          label="Error Threshold Remaining (%)"
          :rules="[val => val >= 0 || 'Minimum threshold is 0', val => val < 100 || 'Maximum threshold is 99']"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          options-dense
          v-model="diskcheck.fails_b4_alert"
          :options="failOptions"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          type="number"
          v-model.number="diskcheck.run_interval"
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
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "DiskSpaceCheck",
  props: {
    agentpk: Number,
    policypk: Number,
    mode: String,
    checkpk: Number,
  },
  mixins: [mixins],
  data() {
    return {
      diskcheck: {
        disk: null,
        check_type: "diskspace",
        warning_threshold: 25,
        error_threshold: 10,
        fails_b4_alert: 1,
        run_interval: 0,
      },
      diskOptions: [],
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  methods: {
    setDiskOptions() {
      if (this.policypk) {
        this.$axios
          .get("/checks/getalldisks/")
          .then(r => {
            this.diskOptions = r.data;
            this.diskcheck.disk = "C:";
          })
          .catch(e => {});
      } else {
        this.diskOptions = this.agentDisks.map(i => i.device);
        this.diskcheck.disk = this.diskOptions[0];
      }
    },
    getCheck() {
      this.$axios
        .get(`/checks/${this.checkpk}/check/`)
        .then(r => (this.diskcheck = r.data))
        .catch(e => {});
    },
    addCheck() {
      if (!this.isValidThreshold(this.diskcheck.warning_threshold, this.diskcheck.error_threshold, true)) {
        return;
      }

      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.diskcheck,
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
      if (!this.isValidThreshold(this.diskcheck.warning_threshold, this.diskcheck.error_threshold, true)) {
        return;
      }

      this.$axios
        .patch(`/checks/${this.checkpk}/check/`, this.diskcheck)
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
  computed: {
    ...mapGetters(["agentDisks"]),
  },
  created() {
    if (this.mode === "add") {
      this.setDiskOptions();
    } else if (this.mode === "edit") {
      this.getCheck();
    }
  },
};
</script>