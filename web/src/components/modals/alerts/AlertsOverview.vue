<template>
  <q-card>
    <q-bar>
      Alerts Overview
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-separator />
    <q-card-section>All Alerts</q-card-section>
    <q-card-section>
      <q-btn label="Update" color="primary" />
    </q-card-section>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "AlertsOverview",
  mixins: [mixins],
  data() {
    return {
      alerts: []
    };
  },
  methods: {
    getAlerts() {
      this.$q.loading.show();
      axios
        .get("/alerts/")
        .then(r => {
          this.alerts = r.data.alerts;
        })
        .catch(() => {
          this.$q.loading.hide();
          this.notifyError("Something went wrong");
        });
    }
  },
  computed: {},
  created() {
    this.getAlerts();
  }
};
</script>
