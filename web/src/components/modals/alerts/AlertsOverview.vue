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
      <q-list separator>
        <q-item v-for="alert in alerts" :key="alert.id">
          <q-item-section>
            <q-item-label>{{ alert.client }} - {{ alert.hostname }}</q-item-label>
            <q-item-label caption>
              <q-icon :class="`text-${alertColor(alert.severity)}`" :name="alert.severity"></q-icon>
              {{ alert.message }}
            </q-item-label>
          </q-item-section>

          <q-item-section side top>
            <q-item-label caption>{{ alert.timestamp }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card-section>
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
