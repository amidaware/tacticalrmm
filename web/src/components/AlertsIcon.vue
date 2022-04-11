<template>
  <q-btn dense flat icon="notifications">
    <q-badge v-if="alertsCount > 0" :color="badgeColor" floating transparent>{{ alertsCountText() }}</q-badge>
    <q-menu style="max-height: 30vh">
      <q-list separator>
        <q-item v-if="alertsCount === 0">No New Alerts</q-item>
        <q-item v-for="alert in topAlerts" :key="alert.id">
          <q-item-section>
            <q-item-label overline
              ><router-link :to="`/agents/${alert.agent_id}`"
                >{{ alert.client }} - {{ alert.site }} - {{ alert.hostname }}</router-link
              ></q-item-label
            >
            <q-item-label lines="1">
              <q-icon size="xs" :class="`text-${alertIconColor(alert.severity)}`" :name="alert.severity"></q-icon>
              {{ alert.message }}
            </q-item-label>
          </q-item-section>

          <q-item-section side top>
            <q-item-label caption>{{ getTimeLapse(alert.alert_time) }}</q-item-label>
            <q-item-label>
              <q-icon name="snooze" size="xs" class="cursor-pointer" @click="snoozeAlert(alert)" v-close-popup>
                <q-tooltip>Snooze alert</q-tooltip>
              </q-icon>
              <q-icon name="flag" size="xs" class="cursor-pointer" @click="resolveAlert(alert)" v-close-popup>
                <q-tooltip>Resolve alert</q-tooltip>
              </q-icon>
            </q-item-label>
          </q-item-section>
        </q-item>
        <q-item clickable v-close-popup @click="showOverview">View All Alerts ({{ alertsCount }})</q-item>
      </q-list>
    </q-menu>
  </q-btn>
</template>

<script>
import mixins from "@/mixins/mixins";
import AlertsOverview from "@/components/modals/alerts/AlertsOverview";
import { getTimeLapse } from "@/utils/format";

export default {
  name: "AlertsIcon",
  mixins: [mixins],
  setup(props) {
    return {
      getTimeLapse,
    };
  },
  data() {
    return {
      alertsCount: 0,
      topAlerts: [],
      errorColor: "red",
      warningColor: "orange",
      infoColor: "blue",
      poll: null,
    };
  },
  computed: {
    badgeColor() {
      const severities = this.topAlerts.map(alert => alert.severity);

      if (severities.includes("error")) return this.errorColor;
      else if (severities.includes("warning")) return this.warningColor;
      else return this.infoColor;
    },
  },
  methods: {
    getAlerts() {
      this.$axios
        .patch("alerts/", { top: 10 })
        .then(r => {
          this.alertsCount = r.data.alerts_count;
          this.topAlerts = r.data.alerts;
        })
        .catch(e => {});
    },
    showOverview() {
      this.$q
        .dialog({
          component: AlertsOverview,
        })
        .onDismiss(() => {
          this.getAlerts();
        });
    },
    snoozeAlert(alert) {
      this.$q
        .dialog({
          title: "Snooze Alert",
          message: "How many days to snooze alert?",
          prompt: {
            model: "",
            type: "number",
            isValid: val => !!val && val > 0 && val < 9999,
          },
          cancel: true,
        })
        .onOk(days => {
          this.$q.loading.show();

          const data = {
            id: alert.id,
            type: "snooze",
            snooze_days: days,
          };

          this.$axios
            .put(`alerts/${alert.id}/`, data)
            .then(r => {
              this.getAlerts();
              this.$q.loading.hide();
              this.notifySuccess(`The alert has been snoozed for ${days} days`);
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
    resolveAlert(alert) {
      this.$q.loading.show();

      const data = {
        id: alert.id,
        type: "resolve",
      };

      this.$axios
        .put(`alerts/${alert.id}/`, data)
        .then(r => {
          this.getAlerts();
          this.$q.loading.hide();
          this.notifySuccess("The alert has been resolved");
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    alertIconColor(severity) {
      if (severity === "error") return this.errorColor;
      else if (severity === "warning") return this.warningColor;
      else return this.infoColor;
    },
    alertsCountText() {
      if (this.alertsCount > 99) return "99+";
      else return this.alertsCount;
    },
    pollAlerts() {
      this.poll = setInterval(() => {
        this.getAlerts();
      }, 60 * 1 * 1000);
    },
  },
  mounted() {
    this.getAlerts();
    this.pollAlerts();
  },
  beforeUnmount() {
    clearInterval(this.poll);
  },
};
</script>