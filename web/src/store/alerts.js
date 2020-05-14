import axios from 'axios'

export default {
  namespaced: true,
  state: {
    alerts: [],
  },

  getters: {
    getAlerts(state) {
      return state.alerts;
    },
    getUncheckedAlerts(state) {
      //filter for non-dismissed active alerts
    }
  },

  mutations: {
    SET_ALERTS(state, alerts) {
      state.alerts = alerts;
    },
  },

  actions: {
    getAlerts(context) {
      axios.get(`/alerts/getAlerts/`).then(r => {
        context.commit("SET_ALERTS", r.data);
      });
    }
  }
}