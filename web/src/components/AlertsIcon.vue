<template>
  <q-btn dense flat icon="notifications">
    <q-badge v-if="alertsCount > 0" color="red" floating transparent>{{ alertsCountText() }}</q-badge>
    <q-menu>
      <q-list separator>
        <q-item v-if="alertsCount === 0">No New Alerts</q-item>
        <q-item v-for="alert in topAlerts" :key="alert.id">
          <q-item-section>
            <q-item-label overline>{{ alert.client }} - {{ alert.site }} - {{ alert.hostname }}</q-item-label>
            <q-item-label>
              <q-icon size="xs" :class="`text-${alertIconColor(alert.severity)}`" :name="alert.severity"></q-icon>
              {{ alert.message }}
            </q-item-label>
          </q-item-section>

          <q-item-section side top>
            <q-item-label caption>{{ alertTime(alert.alert_time) }}</q-item-label>
            <q-item-label>
              <q-icon name="snooze" size="xs" class="cursor-pointer">
                <q-tooltip>Snooze the alert for 24 hours</q-tooltip>
              </q-icon>
              <q-icon name="alarm_off" size="xs" class="cursor-pointer">
                <q-tooltip>Dismiss alert</q-tooltip>
              </q-icon>
            </q-item-label>
          </q-item-section>
        </q-item>
        <q-item clickable @click="showOverview">View All Alerts ({{ alertsCount }})</q-item>
      </q-list>
    </q-menu>
  </q-btn>
</template>

<script>
import mixins from "@/mixins/mixins";
import AlertsOverview from "@/components/modals/alerts/AlertsOverview";

export default {
  name: "AlertsIcon",
  mixins: [mixins],
  data() {
    return {
      alertsCount: 0,
      topAlerts: [],
    };
  },
  methods: {
    getAlerts() {
      this.$q.loading.show();
      this.$axios
        .patch("alerts/alerts/", { top: 10 })
        .then(r => {
          this.alertsCount = r.data.alerts_count;
          this.topAlerts = r.data.alerts;
          this.$q.loading.hide();
        })
        .catch(error => {
          this.$q.loading.hide();
          this.notifyError("Unable to get alerts");
        });
    },
    showOverview() {
      this.$q.dialog({
        component: AlertsOverview,
        parent: this,
      });
    },
    alertIconColor(type) {
      if (type === "error") {
        return "red";
      }
      if (type === "warning") {
        return "orange";
      }
    },
    alertsCountText() {
      if (this.alertsCount > 99) {
        return "99+";
      } else {
        return this.alertsCount;
      }
    },
  },
  mounted() {
    this.getAlerts();
  },
};
</script>