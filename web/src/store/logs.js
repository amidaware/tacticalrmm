import axios from "axios";

export default {
  namespaced: true,
  state: {
    toggleLogModal: false,
    togglePendingActions: false,
    pendingActionsLoading: false,
    actionsAgentPk: null,
    actionsHostname: null,
    allPendingActions: []
  },
  getters: {
    actionsHostname(state) {
      return state.actionsHostname;
    },
    togglePendingActions(state) {
      return state.togglePendingActions;
    },
    allPendingActions(state) {
      return state.allPendingActions;
    },
    actionsAgentPk(state) {
      return state.actionsAgentPk;
    },
    pendingActionsLoading(state) {
      return state.pendingActionsLoading;
    }
  },
  mutations: {
    PENDING_ACTIONS_LOADING(state, visible) {
      state.pendingActionsLoading = visible;
    },
    TOGGLE_LOG_MODAL(state, action) {
      state.toggleLogModal = action;
    },
    TOGGLE_PENDING_ACTIONS(state, { action, agentpk, hostname }) {
      state.actionsAgentPk = agentpk;
      state.actionsHostname = hostname;
      state.togglePendingActions = action;
    },
    SET_PENDING_ACTIONS(state, actions) {
      state.allPendingActions = actions;
    },
    CLEAR_PENDING_ACTIONS(state) {
      state.togglePendingActions = false;
      state.allPendingActions = [];
      state.actionsAgentPk = null;
      state.actionsHostname = null;
    },
  },
  actions: {
    getPendingActions({ commit, state }) {
      commit("PENDING_ACTIONS_LOADING", true);
      const url = state.actionsAgentPk === null
        ? "/logs/allpendingactions/"
        : `/logs/${state.actionsAgentPk}/pendingactions/`;

      axios.get(url).then(r => {
        commit("SET_PENDING_ACTIONS", r.data);
        commit("PENDING_ACTIONS_LOADING", false);
      })
    },
    loadAuditLogs(context, data) {
      return axios.patch("/logs/auditlogs/", data)
    },
    optionsFilter(context, data) {
      return axios.post(`logs/auditlogs/optionsfilter/`, data)
    }
  }
}