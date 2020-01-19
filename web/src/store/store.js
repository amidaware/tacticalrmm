import Vue from "vue";
import Vuex from "vuex";
import axios from "axios";
import { Notify } from "quasar";
import router from "../router";
import logModule from "./logs";

Vue.use(Vuex);

export const store = new Vuex.Store({
  modules: {
    logs: logModule
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
    agentChecks: {},
    agentTableLoading: false,
    treeLoading: false
  },
  getters: {
    loggedIn(state) {
      return state.token !== null;
    },
    selectedAgentPk(state) {
      return state.agentSummary.id;
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
    }
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
    setChecks(state, checks) {
      state.agentChecks = checks;
    },
    destroySubTable(state) {
      (state.agentSummary = {}),
        (state.agentChecks = {}),
        (state.winUpdates = {});
      state.selectedRow = "";
    }
  },
  actions: {
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
    getUpdatedSites(context) {
      axios.get("/clients/loadclients/").then(r => {
        context.commit("getUpdatedSites", r.data);
      });
    },
    loadTree({ commit }) {
      axios.get("/clients/loadtree/").then(r => {
        const input = r.data;
        if (
          Object.entries(input).length === 0 &&
          input.constructor === Object
        ) {
          router.push({ name: "InitialSetup" });
        }
        const output = [];
        for (let prop in input) {
          let sites_arr = input[prop];
          let child_single = [];
          for (let i = 0; i < sites_arr.length; i++) {
            child_single.push({
              label: sites_arr[i].split("|")[0],
              id: sites_arr[i].split("|")[1],
              raw: sites_arr[i],
              header: "generic",
              icon: "fas fa-map-marker-alt",
              iconColor: sites_arr[i].split("|")[2]
            });
          }
          output.push({
            label: prop.split("|")[0],
            id: prop.split("|")[1],
            raw: prop,
            header: "root",
            icon: "fas fa-user",
            iconColor: prop.split("|")[2],
            children: child_single
          });
        }

        // first sort alphabetically, then move failing clients to the top
        const sortedAlpha = output.sort((a, b) => (a.label > b.label ? 1 : -1));
        const sortedByFailing = sortedAlpha.sort(a =>
          a.iconColor === "red" ? -1 : 1
        );
        commit("loadTree", sortedByFailing);
        //commit("destroySubTable");
      });
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
              color: "red",
              position: "top",
              timeout: 1000,
              textColor: "white",
              icon: "fas fa-times-circle",
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
