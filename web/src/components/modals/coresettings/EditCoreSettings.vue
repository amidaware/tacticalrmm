<template>
  <q-card style="min-width: 600px">
    <q-form @submit.prevent="editSettings">
      <q-card-section class="row items-center">
        <div class="text-h6">Global Settings</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Disk Check Interval:</div>
        <q-input
          dense
          class="col-2"
          type="number"
          filled
          label="Seconds"
          v-model.number="settings.disk_check_interval"
          :rules="[ 
            val => !!val || '*Required',
            val => val >= 10 || 'Minimum is 10 seconds',
            val => val <= 3600 || 'Maximum is 3600 seconds'
            ]"
        />
        <div class="col-1"></div>
        <div class="col-3">CPU Load Check Interval:</div>
        <q-input
          dense
          class="col-2"
          type="number"
          filled
          label="Seconds"
          v-model.number="settings.cpuload_check_interval"
          :rules="[ 
            val => !!val || '*Required',
            val => val >= 10 || 'Minimum is 10 seconds',
            val => val <= 3600 || 'Maximum is 3600 seconds'
            ]"
        />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Memory Check Interval:</div>
        <q-input
          dense
          class="col-2"
          type="number"
          filled
          label="Seconds"
          v-model.number="settings.mem_check_interval"
          :rules="[ 
            val => !!val || '*Required',
            val => val >= 10 || 'Minimum is 10 seconds',
            val => val <= 3600 || 'Maximum is 3600 seconds'
            ]"
        />
        <div class="col-1"></div>
        <div class="col-3">Win Service Check Interval:</div>
        <q-input
          dense
          type="number"
          filled
          label="Seconds"
          v-model.number="settings.win_svc_check_interval"
          class="col-2"
          :rules="[ 
            val => !!val || '*Required',
            val => val >= 10 || 'Minimum is 10 seconds',
            val => val <= 3600 || 'Maximum is 3600 seconds'
            ]"
        />
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Save" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "EditCoreSettings",
  mixins: [mixins],
  data() {
    return {
      settings: {}
    };
  },
  methods: {
    getCoreSettings() {
      axios.get("/core/getcoresettings/").then(r => (this.settings = r.data));
    },
    editSettings() {
      this.$q.loading.show();
      axios
        .patch("/core/editsettings/", this.settings)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess("Settings were edited!");
          this.$emit("close");
        })
        .catch(() => {
          this.$q.loading.hide();
          this.notifyError("Something weng wrong");
        });
    }
  },
  created() {
    this.getCoreSettings();
  }
};
</script>