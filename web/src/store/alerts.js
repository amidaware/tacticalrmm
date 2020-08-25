import axios from 'axios'

export default {
  namespaced: true,
  state: {
    alerts: []
  },

  getters: {
    getAlerts(state) {
      return state.alerts;
    },
    getNewAlerts(state) {
      return state.alerts.filter(alert => !alert.resolved || alert.snoozed_until == undefined)
    }
  },

  mutations: {
    SET_ALERTS(state, alerts) {
      state.alerts = alerts;
    },
  },

  actions: {
    getAlerts(context) {
      axios.get("/alerts/alerts/").then(r => {
        context.commit("SET_ALERTS", r.data);
      });
    },
    editAlert(context, pk) {
      return axios.put(`/alerts/alerts/${pk}`);
    }
  }
}