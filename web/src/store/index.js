import Vue from "vue";
import Vuex from "vuex";
import axios from "axios";
import { Notify } from "quasar";
import adminModule from "./admin.js"

Vue.use(Vuex);

export default function () {
  const Store = new Vuex.Store({
    modules: {
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
      notes: [],
      needrefresh: false,
      tableHeight: "35vh",
      tabHeight: "35vh",
      showCommunityScripts: false,
      agentDblClickAction: "",
      defaultAgentTblTab: "server",
      clientTreeSort: "alphafail",
      clientTreeSplitter: 11,
    },
    getters: {
      clientTreeSplitterModel(state) {
        return state.clientTreeSplitter;
      },
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
      showCommunityScripts(state) {
        return state.showCommunityScripts;
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
      SET_REFRESH_NEEDED(state, action) {
        state.needrefresh = action;
      },
      SET_SPLITTER(state, val) {
        const agentHeight = Math.abs(100 - val - 15);
        const tabsHeight = Math.abs(val - 10);
        agentHeight <= 15.0 ? state.tableHeight = "15vh" : state.tableHeight = `${agentHeight}vh`;
        tabsHeight <= 15.0 ? state.tabHeight = "15vh" : state.tabHeight = `${tabsHeight}vh`;
      },
      SET_CLIENT_SPLITTER(state, val) {
        state.clientTreeSplitter = val;
      },
      SET_NOTES(state, notes) {
        state.notes = notes;
      },
      setShowCommunityScripts(state, show) {
        state.showCommunityScripts = show
      },
      SET_AGENT_DBLCLICK_ACTION(state, action) {
        state.agentDblClickAction = action
      },
      SET_DEFAULT_AGENT_TBL_TAB(state, tab) {
        state.defaultAgentTblTab = tab
      },
      SET_CLIENT_TREE_SORT(state, val) {
        state.clientTreeSort = val
      }
    },
    actions: {
      setClientTreeSplitter(context, val) {
        axios.patch("/accounts/users/ui/", { client_tree_splitter: Math.trunc(val) }).then(r => {
          context.commit("SET_CLIENT_SPLITTER", val)
        })
      },
      setShowCommunityScripts(context, data) {
        axios.patch("/accounts/users/ui/", { show_community_scripts: data }).then(r => {
          context.commit("setShowCommunityScripts", data)
        })
      },
      toggleMaintenanceMode(context, data) {
        return axios.post("/agents/maintenance/", data)
      },
      getDashInfo(context) {
        return axios.get("/core/dashinfo/");
      },
      loadAutomatedTasks(context, pk) {
        axios.get(`/tasks/${pk}/automatedtasks/`).then(r => {
          context.commit("SET_AUTOMATED_TASKS", r.data);
        })
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
      loadTree({ commit, state }) {
        axios.get("/clients/tree/").then(r => {

          if (r.data.length === 0) {
            this.$router.push({ name: "InitialSetup" });
          }

          let output = [];
          for (let client of r.data) {

            let childSites = [];
            for (let site of client.sites) {

              let siteNode = {
                label: site.name,
                id: site.id,
                raw: `Site|${site.id}`,
                header: "generic",
                icon: "apartment",
                client: client.id,
                server_policy: site.server_policy,
                workstation_policy: site.workstation_policy,
                alert_template: site.alert_template
              }

              if (site.maintenance_mode) { siteNode["color"] = "green" }
              else if (site.failing_checks.error) { siteNode["color"] = "negative" }
              else if (site.failing_checks.warning) { siteNode["color"] = "warning" }

              childSites.push(siteNode);
            }

            let clientNode = {
              label: client.name,
              id: client.id,
              raw: `Client|${client.id}`,
              header: "root",
              icon: "business",
              server_policy: client.server_policy,
              workstation_policy: client.workstation_policy,
              alert_template: client.alert_template,
              children: childSites
            }

            if (client.maintenance_mode) clientNode["color"] = "green"
            else if (client.failing_checks.error) { clientNode["color"] = "negative" }
            else if (client.failing_checks.warning) { clientNode["color"] = "warning" }

            output.push(clientNode);
          }


          if (state.clientTreeSort === "alphafail") {
            // move failing clients to the top
            const sortedByFailing = output.sort(a => a.color === "negative" ? -1 : 1);
            commit("loadTree", sortedByFailing);
          } else {
            commit("loadTree", output);
          }

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

