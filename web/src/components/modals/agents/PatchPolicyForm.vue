<template>
  <div>
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
        <q-checkbox v-model="winupdatepolicy.run_time_day_mon" label="Monday" />
        <q-checkbox v-model="winupdatepolicy.run_time_day_tue" label="Tuesday" />
        <q-checkbox v-model="winupdatepolicy.run_time_day_wed" label="Wednesday" />
        <q-checkbox v-model="winupdatepolicy.run_time_day_thur" label="Thursday" />
        <q-checkbox v-model="winupdatepolicy.run_time_day_fri" label="Friday" />
        <q-checkbox v-model="winupdatepolicy.run_time_day_sat" label="Saturday" />
        <q-checkbox v-model="winupdatepolicy.run_time_day_sun" label="Sunday" />
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
  </div>
</template>

<script>
import { scheduledTimes } from "@/mixins/data";

export default {
  name: "PatchPolicyForm",
  data() {
    return {
      winupdatepolicy: {
        agent: null,
        policy: null,
        critical: "ignore",
        important: "ignore",
        moderate: "ignore",
        low: "ignore",
        other: "ignore",
        run_time_hour: 0,
        repeat: 0,
        run_time_day_mon: false,
        run_time_day_tue: false,
        run_time_day_wed: false,
        run_time_day_thur: false,
        run_time_day_fri: false,
        run_time_day_sat: false,
        run_time_day_sun: false,
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
};
</script>