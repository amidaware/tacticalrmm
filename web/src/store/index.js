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
      toggleScriptManager: false,
      needrefresh: false,
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
      managedByWsus(state) {
        return state.agentSummary.managed_by_wsus;
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
      }
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
      }
    },
    actions: {
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
        axios.get("/clients/loadclients/").then(r => {
          context.commit("getUpdatedSites", r.data);
        });
      },
      loadClients(context) {
        return axios.get("/clients/listclients/");
      },
      loadSites(context) {
        return axios.get("/clients/listsites/");
      },
      loadAgents(context) {
        return axios.get("/agents/listagents/");
      },
      loadTree({ commit }) {
        axios.get("/clients/loadtree/").then(r => {
          const input = r.data;
          if (
            Object.entries(input).length === 0 &&
            input.constructor === Object
          ) {
            this.$router.push({ name: "InitialSetup" });
          }
          const output = [];
          for (let prop in input) {
            let sites_arr = input[prop];
            let child_single = [];
            for (let i = 0; i < sites_arr.length; i++) {
              child_single.push({
                label: sites_arr[i].split("|")[0],
                id: sites_arr[i].split("|")[1],
                raw: `Site|${sites_arr[i]}`,
                header: "generic",
                icon: "apartment",
                color: sites_arr[i].split("|")[2]
              });
            }
            output.push({
              label: prop.split("|")[0],
              id: prop.split("|")[1],
              raw: `Client|${prop}`,
              header: "root",
              icon: "business",
              color: prop.split("|")[2],
              children: child_single
            });
          }

          // first sort alphabetically, then move failing clients to the top
          const sortedAlpha = output.sort((a, b) => (a.label > b.label ? 1 : -1));
          const sortedByFailing = sortedAlpha.sort(a =>
            a.iconColor === "negative" ? -1 : 1
          );
          commit("loadTree", sortedByFailing);
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

