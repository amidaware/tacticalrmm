import axios from "axios";

export default {
  namespaced: true,
  state: {
    selectedPolicy: null,
    checks: [],
    automatedTasks: {},
    policies: [],
  },

  getters: {
    checks(state) {
      return state.checks;
    },
    tasks(state) {
      return state.automatedTasks.autotasks;
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
      return axios.get("/automation/policies/").then(r => {
        context.commit("SET_POLICIES", r.data);
      })
    },
    loadPolicyAutomatedTasks(context, pk) {
      axios.get(`/automation/${pk}/policyautomatedtasks/`).then(r => {
        context.commit("setPolicyAutomatedTasks", r.data);
      });
    },
    loadPolicyChecks(context, pk) {
      axios.get(`/automation/${pk}/policychecks/`).then(r => {
        context.commit("setPolicyChecks", r.data);
      });
    },
    loadCheckStatus(context, { checkpk }) {
      return axios.patch(`/automation/policycheckstatus/${checkpk}/check/`);
    },
    loadAutomatedTaskStatus(context, { taskpk }) {
      return axios.patch(`/automation/policyautomatedtaskstatus/${taskpk}/task/`);
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
      return axios.put(`/automation/runwintask/${pk}/`);
    },
    getRelated(context, pk) {
      return axios.get(`/automation/policies/${pk}/related/`);
    },
    getRelatedPolicies(context, data) {
      return axios.patch(`/automation/related/`, data);
    },
    updateRelatedPolicies(context, data) {
      return axios.post(`/automation/related/`, data);
    },
    loadPolicyTreeData(context) {
      return axios.get("/automation/policies/overview/");
    },
    addPatchPolicy(context, data) {
      return axios.post("/automation/winupdatepolicy/", data)
    },
    editPatchPolicy(context, data) {
      return axios.put(`/automation/winupdatepolicy/${data.id}/`, data)
    },
    deletePatchPolicy(context, pk) {
      return axios.delete(`/automation/winupdatepolicy/${pk}/`)
    }
  }
}
