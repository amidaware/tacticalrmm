<template>
  <q-btn dense flat icon="notifications">
    <q-badge v-if="alerts.length !== 0" color="red" floating transparent>{{ alertsLengthText() }}</q-badge>
    <q-menu>
      <q-list separator>
        <q-item v-if="alerts.length === 0">No Alerts</q-item>
        <q-item v-for="alert in alerts" :key="alert.id">
          <q-item-section>
            <q-item-label>{{ alert.client }} - {{ alert.hostname }}</q-item-label>
            <q-item-label caption>
              <q-icon :class="`text-${alertColor(alert.severity)}`" :name="alert.severity"></q-icon>
              {{ alert.message }}
            </q-item-label>
          </q-item-section>

          <q-item-section side top>
            <q-item-label caption>{{ alert.alert_time }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-item clickable @click="showAlertsModal = true">View All Alerts</q-item>
      </q-list>
    </q-menu>

    <q-dialog
      v-model="showAlertsModal"
      maximized
      transition-show="slide-up"
      transition-hide="slide-down"
    >
      <AlertsOverview @close="showAlertsModal = false" />
    </q-dialog>
  </q-btn>
</template>

<script>
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins"
import AlertsOverview from "@/components/modals/alerts/AlertsOverview";

export default {
  name: "AlertsIcon",
  components: { AlertsOverview },
  mixins: [mixins],
  data() {
    return {
      showAlertsModal: false,
    };
  },
  methods: {
    getAlerts() {
      this.$store
        .dispatch("alerts/getAlerts")
        .catch(error => {
          console.error(error)
        });
    },
    alertColor(type) {
      if (type === "error") {
        return "red";
      }
      if (type === "warning") {
        return "orange";
      }
    },
    alertsLengthText() {
      if (this.alerts.length > 9) {
        return "9+";
      } else {
        return this.alerts.length;
      }
    }
  },
  computed: {
    ...mapGetters({
      alerts: "alerts/getNewAlerts"
    })
  },
  mounted() {
    this.getAlerts()
  }
};
</script>