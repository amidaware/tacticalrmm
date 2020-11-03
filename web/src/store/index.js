import Vue from "vue";
import Vuex from "vuex";
import axios from "axios";
import { Notify } from "quasar";
import logModule from "./logs";
import alertsModule from "./alerts";
import automationModule from "./automation";
import adminModule from "./admin.js"

Vue.use(Vuex);

export default function () {
  const Store = new Vuex.Store({
    modules: {
      logs: logModule,
      automation: automationModule,
      alerts: alertsModule,
      admin: adminModule
    },
    state: {
      username: localStorage.getItem("user_name") || null,
      token: localStorage.getItem("access_token") || null,
      clients: {},
      tree: [],
      treeReady: false,
      selectedRow: null,
      agentSummary: {},
      winUpdates: {},
      agentChecks: null,
      automatedTasks: {},
      agentTableLoading: false,
      treeLoading: false,
      installedSoftware: [],
      scripts: [],
      notes: [],
      toggleScriptManager: false,
      needrefresh: false,
      tableHeight: "35vh",
      tabHeight: "35vh",
    },
    getters: {
      loggedIn(state) {
        return state.token !== null;
      },
      selectedAgentPk(state) {
        return state.agentSummary.id;
      },
      agentDisks(state) {
        return state.agentSummary.disks;
      },
      agentServices(state) {
        return state.agentSummary.services;
      },
      checks(state) {
        return state.agentChecks;
      },
      sortedUpdates(state) {
        // sort patches by latest then not installed
        if (!state.winUpdates.winupdates) {
          return [];
        }
        const sortedByID = state.winUpdates.winupdates.sort((a, b) =>
          a.id > b.id ? 1 : -1
        );
        const sortedByInstall = sortedByID.sort(a =>
          a.installed === false ? -1 : 1
        );
        return sortedByInstall;
      },
      agentHostname(state) {
        return state.agentSummary.hostname;
      },
      scripts(state) {
        return state.scripts;
      },
      needRefresh(state) {
        return state.needrefresh;
      },
      agentTableHeight(state) {
        return state.tableHeight;
      },
      tabsTableHeight(state) {
        return state.tabHeight;
      },
    },
    mutations: {
      TOGGLE_SCRIPT_MANAGER(state, action) {
        state.toggleScriptManager = action;
      },
      AGENT_TABLE_LOADING(state, visible) {
        state.agentTableLoading = visible;
      },
      setActiveRow(state, pk) {
        state.selectedRow = pk;
      },
      retrieveToken(state, { token, username }) {
        state.token = token;
        state.username = username;
      },
      destroyCommit(state) {
        state.token = null;
        state.username = null;
      },
      getUpdatedSites(state, clients) {
        state.clients = clients;
      },
      loadTree(state, treebar) {
        state.tree = treebar;
        state.treeReady = true;
      },
      setSummary(state, summary) {
        state.agentSummary = summary;
      },
      SET_WIN_UPDATE(state, updates) {
        state.winUpdates = updates;
      },
      SET_INSTALLED_SOFTWARE(state, software) {
        state.installedSoftware = software;
      },
      setChecks(state, checks) {
        state.agentChecks = checks;
      },
      SET_AUTOMATED_TASKS(state, tasks) {
        state.automatedTasks = tasks;
      },
      destroySubTable(state) {
        (state.agentSummary = {}),
          (state.agentChecks = null),
          (state.winUpdates = {});
        (state.installedSoftware = []);
        state.selectedRow = "";
      },
      SET_SCRIPTS(state, scripts) {
        state.scripts = scripts;
      },
      SET_REFRESH_NEEDED(state, action) {
        state.needrefresh = action;
      },
      SET_SPLITTER(state, val) {
        const agentHeight = Math.abs(100 - val - 15);
        const tabsHeight = Math.abs(val - 10);
        agentHeight <= 15.0 ? state.tableHeight = "15vh" : state.tableHeight = `${agentHeight}vh`;
        tabsHeight <= 15.0 ? state.tabHeight = "15vh" : state.tabHeight = `${tabsHeight}vh`;
      },
      SET_NOTES(state, notes) {
        state.notes = notes;
      }
    },
    actions: {
      toggleMaintenanceMode(context, data) {
        return axios.post("/agents/maintenance/", data)
      },
      getAgentCounts(context, data = {}) {
        return axios.post("/agents/agent_counts/", data)
      },
      getDashInfo(context) {
        return axios.get("/core/dashinfo/");
      },
      loadAutomatedTasks(context, pk) {
        axios.get(`/tasks/${pk}/automatedtasks/`).then(r => {
          context.commit("SET_AUTOMATED_TASKS", r.data);
        })
      },
      getScripts(context) {
        axios.get("/scripts/scripts/").then(r => {
          context.commit("SET_SCRIPTS", r.data);
        });
      },
      loadInstalledSoftware(context, pk) {
        axios.get(`/software/installed/${pk}`).then(r => {
          context.commit("SET_INSTALLED_SOFTWARE", r.data.software);
        });
      },
      loadWinUpdates(context, pk) {
        axios.get(`/winupdate/${pk}/getwinupdates/`).then(r => {
          context.commit("SET_WIN_UPDATE", r.data);
        });
      },
      loadSummary(context, pk) {
        axios.get(`/agents/${pk}/agentdetail/`).then(r => {
          context.commit("setSummary", r.data);
        });
      },
      loadChecks(context, pk) {
        axios.get(`/checks/${pk}/loadchecks/`).then(r => {
          context.commit("setChecks", r.data);
        });
      },
      loadNotes(context, pk) {
        axios.get(`/agents/${pk}/notes/`).then(r => {
          context.commit("SET_NOTES", r.data.notes);
        });
      },
      loadDefaultServices(context) {
        return axios.get("/services/getdefaultservices/");
      },
      loadAgentServices(context, agentpk) {
        return axios.get(`/services/${agentpk}/services/`);
      },
      editCheckAlert(context, { pk, data }) {
        return axios.patch(`/checks/${pk}/check/`, data);
      },
      deleteCheck(context, pk) {
        return axios.delete(`/checks/${pk}/check/`);
      },
      editAutoTask(context, data) {
        return axios.patch(`/tasks/${data.id}/automatedtasks/`, data);
      },
      deleteAutoTask(context, pk) {
        return axios.delete(`/tasks/${pk}/automatedtasks/`);
      },
      getUpdatedSites(context) {
        axios.get("/clients/clients/").then(r => {
          context.commit("getUpdatedSites", r.data);
        });
      },
      loadClients(context) {
        return axios.get("/clients/clients/");
      },
      loadSites(context) {
        return axios.get("/clients/sites/");
      },
      loadAgents(context) {
        return axios.get("/agents/listagents/");
      },
      loadTree({ commit }) {
        axios.get("/clients/tree/").then(r => {

          if (r.data.length === 0) {
            this.$router.push({ name: "InitialSetup" });
          }

          let output = [];
          for (let client of r.data) {

            let childSites = [];
            for (let site of client.sites) {

              let site_color = "black"
              if (site.maintenance_mode) { site_color = "orange" }
              else if (site.failing_checks) { site_color = "red" }

              childSites.push({
                label: site.name,
                id: site.id,
                raw: `Site|${site.id}`,
                header: "generic",
                icon: "apartment",
                color: site_color
              });
            }

            let client_color = "black"
            if (client.maintenance_mode) { client_color = "orange" }
            else if (client.failing_checks) { client_color = "red" }

            output.push({
              label: client.name,
              id: client.id,
              raw: `Client|${client.id}`,
              header: "root",
              icon: "business",
              color: client_color,
              children: childSites
            });
          }

          commit("loadTree", output);
          //commit("destroySubTable");
        });
      },
      checkVer(context) {
        axios.get("/core/version/").then(r => {
          const version = r.data;

          if (localStorage.getItem("rmmver")) {
            if (localStorage.getItem("rmmver") === version) {
              return;
            } else {
              localStorage.setItem("rmmver", "0.0.1");
              context.commit("SET_REFRESH_NEEDED", true);
            }
          } else {
            localStorage.setItem("rmmver", version);
            return;
          }
        })
      },
      reload() {
        localStorage.removeItem("rmmver");
        location.reload();
      },
      retrieveToken(context, credentials) {
        return new Promise((resolve, reject) => {
          axios
            .post("/login/", credentials)
            .then(response => {
              const token = response.data.token;
              const username = credentials.username;
              localStorage.setItem("access_token", token);
              localStorage.setItem("user_name", username);
              context.commit("retrieveToken", { token, username });
              resolve(response);
            })
            .catch(error => {
              Notify.create({
                type: "negative",
                timeout: 1000,
                message: "Bad token"
              });
              reject(error);
            });
        });
      },
      destroyToken(context) {
        if (context.getters.loggedIn) {
          return new Promise((resolve, reject) => {
            axios
              .post("/logout/")
              .then(response => {
                localStorage.removeItem("access_token");
                localStorage.removeItem("user_name");
                context.commit("destroyCommit");
                resolve(response);
              })
              .catch(error => {
                localStorage.removeItem("access_token");
                localStorage.removeItem("user_name");
                context.commit("destroyCommit");
                reject(error);
              });
          });
        }
      }
    }
  });

  return Store;
}

