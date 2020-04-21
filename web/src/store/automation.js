import axios from 'axios';

export default {
  namespaced: true,
  state: {
    selectedPolicy: null,
    checks: {},
    automatedTasks: {},
    policies: [],
  },

  getters:{
    selectedPolicyPk (state) {
      return state.selectedPolicy;
    },
    policies (state) {
      return state.policies;
    }
  },

  mutations: {
    SET_POLICIES (state, policies) {
      state.policies = policies;
    },
    setSelectedPolicy (state, pk) {
      state.selectedPolicy = pk;
    },
    setPolicyChecks (state, checks) {
      state.checks = checks;
    },
    setPolicyAutomatedTasks (state, tasks) {
      state.automatedTasks = tasks;
    },
  },

  actions: {
    getPolicies (context) {
      axios.get("/automation/policies/").then(r => {
        context.commit("SET_POLICIES", r.data);
      })
    },
    loadPolicyAutomatedTasks (context, pk) {
      axios.get(`/automation/${pk}/policyautomatedtasks/`).then(r => {
        context.commit("setPolicyAutomatedTasks", r.data);
      });
    },
    loadPolicyChecks (context, pk) {
      axios.get(`/checks/${pk}/loadpolicychecks/`).then(r => {
        context.commit("setPolicyChecks", r.data);
      });
    },
  }
}
