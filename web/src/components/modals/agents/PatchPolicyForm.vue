<template>
  <div class="q-pa-md">
    <!-- Auto Approval -->
    <div class="text-subtitle2">Auto Approval</div>
    <hr />
    <q-card-section class="row">
      <div class="col-3">Severity</div>
      <div class="col-4"></div>
      <div class="col-5">Action</div>
    </q-card-section>
    <q-card-section class="row">
      <div class="col-3">Critical:</div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.critical"
        :options="severityOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <q-card-section class="row">
      <div class="col-3">Important:</div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.important"
        :options="severityOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <q-card-section class="row">
      <div class="col-3">Moderate:</div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.moderate"
        :options="severityOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <q-card-section class="row">
      <div class="col-3">Low:</div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.low"
        :options="severityOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <q-card-section class="row">
      <div class="col-3">Other:</div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.other"
        :options="severityOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <!-- Installation Schedule -->
    <div class="text-subtitle2">Installation Schedule</div>
    <hr />
    <q-card-section class="row">
      <div class="col-3">Schedule Frequency:</div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.run_time_frequency"
        :options="frequencyOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <q-card-section class="row" v-if="winupdatepolicy.run_time_frequency === 'monthly'">
      <div class="col-3">Day of month to run:</div>
      <div class="col-4"></div>
      <q-select
        v-show="winupdatepolicy.run_time_frequency !== 'inherit'"
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.run_time_day"
        :options="monthDays"
        emit-value
        map-options
      />
    </q-card-section>
    <q-card-section class="row" v-show="winupdatepolicy.run_time_frequency !== 'inherit'">
      <div class="col-3">Scheduled Time:</div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.run_time_hour"
        :options="timeOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <q-card-section
      v-if="winupdatepolicy.run_time_frequency === 'daily'"
      v-show="winupdatepolicy.run_time_frequency !== 'inherit'"
    >
      <div class="q-gutter-sm">
        <q-checkbox v-model="winupdatepolicy.run_time_days" :val="1" label="Monday" />
        <q-checkbox v-model="winupdatepolicy.run_time_days" :val="2" label="Tuesday" />
        <q-checkbox v-model="winupdatepolicy.run_time_days" :val="3" label="Wednesday" />
        <q-checkbox v-model="winupdatepolicy.run_time_days" :val="4" label="Thursday" />
        <q-checkbox v-model="winupdatepolicy.run_time_days" :val="5" label="Friday" />
        <q-checkbox v-model="winupdatepolicy.run_time_days" :val="6" label="Saturday" />
        <q-checkbox v-model="winupdatepolicy.run_time_days" :val="0" label="Sunday" />
      </div>
    </q-card-section>
    <!-- Reboot After Installation -->
    <div class="text-subtitle2">Reboot After Installation</div>
    <hr />
    <q-card-section class="row">
      <div class="col-3"></div>
      <div class="col-4"></div>
      <q-select
        dense
        class="col-5"
        outlined
        v-model="winupdatepolicy.reboot_after_install"
        :options="rebootOptions"
        emit-value
        map-options
      />
    </q-card-section>
    <!-- Failed Patches -->
    <div class="text-subtitle2">Failed Patches</div>
    <hr />
    <q-card-section class="row" v-if="!policy">
      <div class="col-5">
        <q-checkbox v-model="winupdatepolicy.reprocess_failed_inherit" label="Inherit failed patch settings" />
      </div>
    </q-card-section>
    <q-card-section class="row" v-show="!winupdatepolicy.reprocess_failed_inherit">
      <div class="col-5">
        <q-checkbox v-model="winupdatepolicy.reprocess_failed" label="Reprocess failed patches" />
      </div>

      <div class="col-3">
        <q-input
          dense
          v-model.number="winupdatepolicy.reprocess_failed_times"
          type="number"
          filled
          label="Times"
          :rules="[val => val > 0 || 'Must be greater than 0']"
        />
      </div>
      <div class="col-3"></div>
      <q-checkbox v-model="winupdatepolicy.email_if_fail" label="Send an email when patch installation fails" />
    </q-card-section>
    <q-card-actions align="left" v-if="policy">
      <q-btn label="Submit" color="primary" @click="submit" />
      <q-btn label="Cancel" @click="$emit('hide')" />
      <q-space />
      <q-btn v-if="editing" label="Remove Policy" color="negative" @click="deletePolicy(winupdatepolicy)" />
    </q-card-actions>
  </div>
</template>

<script>
import { scheduledTimes, monthDays } from "@/mixins/data";
import mixins from "@/mixins/mixins";

export default {
  name: "PatchPolicyForm",
  emits: ["close", "hide"],
  props: {
    policy: Object,
    agent: Object,
  },
  mixins: [mixins],
  data() {
    return {
      editing: true,
      winupdatepolicy: {},
      defaultWinUpdatePolicy: {
        critical: "ignore",
        important: "ignore",
        moderate: "ignore",
        low: "ignore",
        other: "ignore",
        run_time_hour: 3,
        run_time_frequency: "daily",
        run_time_days: [],
        run_time_day: 1,
        reboot_after_install: "never",
        reprocess_failed_inherit: false,
        reprocess_failed: false,
        reprocess_failed_times: 5,
        email_if_fail: false,
      },
      severityOptions: [
        { label: "Manual", value: "manual" },
        { label: "Approve", value: "approve" },
        { label: "Ignore", value: "ignore" },
      ],
      frequencyOptions: [
        { label: "Daily/Weekly", value: "daily" },
        { label: "Monthly", value: "monthly" },
      ],
      rebootOptions: [
        { label: "Never", value: "never" },
        { label: "When Required", value: "required" },
        { label: "Always", value: "always" },
      ],
      timeOptions: scheduledTimes,
      monthDays,
    };
  },
  methods: {
    submit() {
      this.$q.loading.show();

      // modifying patch policy in automation manager
      if (this.policy) {
        // editing patch policy
        if (this.editing) {
          this.$axios
            .put(`/automation/patchpolicy/${this.winupdatepolicy.id}/`, this.winupdatepolicy)
            .then(response => {
              this.$q.loading.hide();
              this.$emit("close");
              this.notifySuccess("Patch policy was edited successfully!");
            })
            .catch(error => {
              this.$q.loading.hide();
            });
        } else {
          // adding patch policy
          this.$axios
            .post("/automation/patchpolicy/", this.winupdatepolicy)
            .then(response => {
              this.$q.loading.hide();
              this.$emit("close");
              this.notifySuccess("Patch policy was created successfully!");
            })
            .catch(error => {
              this.$q.loading.hide();
            });
        }
      }
    },
    deletePolicy(policy) {
      this.$q
        .dialog({
          title: "Delete patch policy?",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/automation/patchpolicy/${policy.id}/`)
            .then(r => {
              this.$q.loading.hide();
              this.$emit("close");
              this.notifySuccess("Patch policy was deleted successfully!");
            })
            .catch(error => {
              this.$q.loading.hide();
            });
        });
    },
  },
  mounted() {
    if (this.policy && this.policy.winupdatepolicy[0]) {
      this.winupdatepolicy = this.policy.winupdatepolicy[0];
      this.editing = true;
    } else if (this.policy) {
      this.winupdatepolicy = this.defaultWinUpdatePolicy;
      this.winupdatepolicy.policy = this.policy.id;
      this.editing = false;
    } else if (this.agent) {
      this.winupdatepolicy = this.agent.winupdatepolicy[0];

      // add agent inherit options
      this.severityOptions.push({ label: "Inherit", value: "inherit" });
      this.frequencyOptions.push({ label: "Inherit", value: "inherit" });
      this.rebootOptions.push({ label: "Inherit", value: "inherit" });
    }
  },
};
</script>