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
    <q-card-section>
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
      <div class="q-gutter-sm">
        <q-radio v-model="winupdatepolicy.reboot_after_install" val="never" label="Never" />
        <q-radio
          v-model="winupdatepolicy.reboot_after_install"
          val="required"
          label="When Required"
        />
        <q-radio v-model="winupdatepolicy.reboot_after_install" val="always" label="Always" />
      </div>
    </q-card-section>
    <!-- Failed Patches -->
    <div class="text-subtitle2">Failed Patches</div>
    <hr />
    <q-card-section class="row">
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
          :rules="[ val => val > 0 || 'Must be greater than 0']"
        />
      </div>
      <div class="col-3"></div>
      <q-checkbox
        v-model="winupdatepolicy.email_if_fail"
        label="Send an email when patch installation fails"
      />
    </q-card-section>
    <q-card-actions align="left" v-if="policy">
      <q-btn label="Apply" color="primary" @click="submit" />
      <q-space />
      <q-btn v-if="editing" label="Remove Policy" color="negative" @click="deletePolicy" />
    </q-card-actions>
  </div>
</template>

<script>
import { scheduledTimes } from "@/mixins/data";
import { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";

export default {
  name: "PatchPolicyForm",
  props: {
    policy: Object,
    agent: Object,
  },
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
        run_time_hour: 0,
        repeat: 0,
        run_time_days: [],
        reboot_after_install: "never",
        reprocess_failed: false,
        reprocess_failed_times: 5,
        email_if_fail: false,
      },
      severityOptions: [
        { label: "Manual", value: "manual" },
        { label: "Approve", value: "approve" },
        { label: "Ignore", value: "ignore" },
      ],
      timeOptions: scheduledTimes,
    };
  },
  methods: {
    submit() {
      this.$q.loading.show();

      // modifying patch policy in automation manager
      if (this.policy) {
        // editing patch policy
        if (this.editing) {
          this.$store
            .dispatch("automation/editPatchPolicy", this.winupdatepolicy)
            .then(response => {
              this.$q.loading.hide();
              this.$emit("close");
              this.$q.notify(notifySuccessConfig("Patch policy was edited successfully!"));
            })
            .catch(error => {
              this.$q.loading.hide();
              this.$q.notify(notifyErrorConfig("An Error occured while editing patch policy"));
            });
        } else {
          // adding patch policy
          this.$store
            .dispatch("automation/addPatchPolicy", this.winupdatepolicy)
            .then(response => {
              this.$q.loading.hide();
              this.$emit("close");
              this.$q.notify(notifySuccessConfig("Patch policy was created successfully!"));
            })
            .catch(error => {
              this.$q.loading.hide();
              this.$q.notify(notifyErrorConfig("An Error occured while adding patch policy"));
            });
        }
      }
    },
    deletePolicy() {
      this.$q
        .dialog({
          title: "Delete patch policy?",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$store
            .dispatch("automation/deletePatchPolicy", this.winupdatepolicy.id)
            .then(response => {
              this.$q.loading.hide();
              this.$emit("close");
              this.$q.notify(notifySuccessConfig("Patch policy was cleared successfully!"));
            })
            .catch(error => {
              this.$q.loading.hide();
              this.$q.notify(notifyErrorConfig("An Error occured while clearing the patch policy"));
            });
        });
    },
  },
  mounted() {
    if (this.policy) {
      if (this.policy.winupdatepolicy.length === 1) {
        this.winupdatepolicy = this.policy.winupdatepolicy[0];
        this.editing = true;
      } else {
        this.winupdatepolicy = this.defaultWinUpdatePolicy;
        this.winupdatepolicy.policy = this.policy.id;
        this.editing = false;
      }
    } else if (this.agent) {
      this.winupdatepolicy = this.agent.winupdatepolicy[0];
      this.severityOptions.push({ label: "Inherit", value: "inherit" });
    }
  },
};
</script>