import axios from "axios";

export default {
  namespaced: true,
  state: {
    selectedPolicy: null,
    checks: {},
    automatedTasks: {},
    policies: [],
  },

  getters: {
    allChecks(state) {
      return [
        ...state.checks.diskchecks,
        ...state.checks.cpuloadchecks,
        ...state.checks.memchecks,
        ...state.checks.scriptchecks,
        ...state.checks.winservicechecks,
        ...state.checks.pingchecks,
        ...state.checks.eventlogchecks
      ];
    },
    selectedPolicyPk(state) {
      return state.selectedPolicy;
    },
    policies(state) {
      return state.policies;
    }
  },

  mutations: {
    SET_POLICIES(state, policies) {
      state.policies = policies;
    },
    setSelectedPolicy(state, pk) {
      state.selectedPolicy = pk;
    },
    setPolicyChecks(state, checks) {
      state.checks = checks;
    },
    setPolicyAutomatedTasks(state, tasks) {
      state.automatedTasks = tasks;
    },
  },

  actions: {
    loadPolicies(context) {
      axios.get("/automation/policies/").then(r => {
        context.commit("SET_POLICIES", r.data);
      })
    },
    loadPolicyAutomatedTasks(context, pk) {
      axios.get(`/automation/${pk}/policyautomatedtasks/`).then(r => {
        context.commit("setPolicyAutomatedTasks", r.data);
      });
    },
    loadPolicyChecks(context, pk) {
      axios.get(`/checks/${pk}/loadpolicychecks/`).then(r => {
        context.commit("setPolicyChecks", r.data);
      });
    },
    loadPolicy(context, pk) {
      return axios.get(`/automation/policies/${pk}/`);
    },
    addPolicy(context, data) {
      return axios.post("/automation/policies/", data);
    },
    editPolicy(context, data) {
      return axios.put(`/automation/policies/${data.id}/`, data);
    },
    deletePolicy(context, pk) {
      return axios.delete(`/automation/policies/${pk}/`).then(r => {
        context.dispatch("loadPolicies");
      });
    },
    runPolicyTask(context, pk) {
      return axios.get(`/automation/runwintask/${pk}/`);
    },
    getRelated(context, pk) {
      return axios.get(`/automation/policies/${pk}/related/`);
    },
    loadPolicyTreeData(context) {
      return axios.get("/automation/policies/overview/");
    }
  }
}
