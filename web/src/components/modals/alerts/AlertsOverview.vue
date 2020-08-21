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

      <q-card-section class="row">
        <div class="col-3">
          <q-input outlined dense v-model="search">
            <template v-slot:append>
              <q-icon v-if="search !== ''" name="close" @click="search = ''" class="cursor-pointer" />
              <q-icon name="search" />
            </template>

            <template v-slot:hint>
              Type in client, site, or agent name
            </template>
          </q-input>
        </div>

        <div class="col-3">
          <q-checkbox outlined dense v-model="includeDismissed" label="Include dismissed alerts?"/>
        </div>
      </q-card-section>

    <q-separator />

    <q-list separator>
      <q-item v-if="alerts.length === 0">No Alerts!</q-item>
      <q-item v-for="alert in alerts" :key="alert.id">
        <q-item-section>
          <q-item-label overline>{{ alert.client }} - {{ alert.site }} - {{ alert.hostname }}</q-item-label>
          <q-item-label>
            <q-icon size="sm" :class="`text-${alertColor(alert.severity)}`" :name="alert.severity"></q-icon>
            {{ alert.message }}
          </q-item-label>
        </q-item-section>

        <q-item-section side top>
          <q-item-label caption>{{ alertTime(alert.alert_time) }}</q-item-label>
          <q-item-label>
            <q-icon name="snooze" size="sm">
              <q-tooltip>
                Snooze the alert for 24 hours
              </q-tooltip>
            </q-icon>
            <q-icon name="alarm_off" size="sm">
              <q-tooltip>
                Dismiss alert
              </q-tooltip>
            </q-icon>
          </q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";

export default {
  name: "AlertsOverview",
  mixins: [mixins],
  data() {
    return {
      search: "",
      includeDismissed: false
    };
  },
  methods: {
    getAlerts() {
      this.$q.loading.show();

      this.$store
        .dispatch("alerts/getAlerts")
        .then(response => {
          this.$q.loading.hide();
        })
        .catch(error => {
          this.$q.loading.hide();
          this.notifyError("Something went wrong");
        });
    },
    alertColor(severity) {
      if (severity === "error") {
        return "red";
      }
      if (severity === "warning") {
        return "orange";
      }
      if (severity === "info") {
        return "blue";
      }
    },
  },
  computed: {
    ...mapGetters({
      alerts: "alerts/getAlerts"
    })
  },
  mounted() {
    this.getAlerts()
  }
};
</script>
