<template>
  <q-btn dense flat icon="notifications">
    <q-badge color="red" floating transparent>
        {{ test_alerts.length }}
    </q-badge>
    <q-menu>
      <q-list separator>
        <q-item v-for="alert in test_alerts" :key="alert.id">
          <q-item-section>
            <q-item-label>{{ alert.client }} - {{ alert.hostname }}</q-item-label>
            <q-item-label caption>
              <q-icon :class="`text-${alertColor(alert.type)}`" :name="alert.type"></q-icon> 
              {{ alert.message }}</q-item-label>
          </q-item-section>

          <q-item-section side top>
            <q-item-label caption>{{ alert.timestamp }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-item clickable @click="showAlertsModal = true">
          View All Alerts ({{test_alerts.length}})
        </q-item>
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
import { mapState } from 'vuex';
import AlertsOverview from '@/components/modals/alerts/AlertsOverview'

export default {
  name: "AlertsIcon",
  components: {AlertsOverview},
  data () {
    return {
      showAlertsModal: false,
      test_alerts: [
        {
          id: 1,
          client: "NMHSI",
          site: "Default",
          hostname: "NMSC-BACK01",
          message: "HDD error. Stuff ain't working",
          type: "error",
          timestamp: "2 min ago"
        },
        {
          id: 2,
          client: "Dove IT",
          site: "Default",
          hostname: "NMSC-ANOTHER",
          message: "Big error. Stuff still ain't working",
          type: "warning",
          timestamp: "5 hours ago"
        }
      ]
    }
  },
  methods: {
    alertColor (type) {
      if (type === "error"){
        return "red";
      } 
      if (type === "warning"){
        return "orange"
      }
    }
  },
  computed: {
    ...mapState('alerts/', {
      alerts: state => state.alerts
    })
  }
}
</script>