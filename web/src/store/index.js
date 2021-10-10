import { createStore } from 'vuex'
import { Screen } from 'quasar'
import axios from "axios";

export default function () {
  const Store = new createStore({
    state() {
      return {
        username: localStorage.getItem("user_name") || null,
        token: localStorage.getItem("access_token") || null,
        clients: {},
        tree: [],
        treeReady: false,
        selectedRow: null,
        agentTableLoading: false,
        treeLoading: false,
        needrefresh: false,
        tableHeight: "300px",
        tabHeight: "300px",
        showCommunityScripts: false,
        agentDblClickAction: "",
        agentUrlAction: null,
        defaultAgentTblTab: "server",
        clientTreeSort: "alphafail",
        clientTreeSplitter: 11,
        noCodeSign: false,
        hosted: false
      }
    },
    getters: {
      clientTreeSplitterModel(state) {
        return state.clientTreeSplitter;
      },
      loggedIn(state) {
        return state.token !== null;
      },
      selectedAgentId(state) {
        return state.selectedRow.agent_id;
      },
      showCommunityScripts(state) {
        return state.showCommunityScripts;
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
      setActiveRow(state, agent_id) {
        state.selectedRow = agent_id;
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
      destroySubTable(state) {
        state.selectedRow = "";
      },
      SET_REFRESH_NEEDED(state, action) {
        state.needrefresh = action;
      },
      SET_SPLITTER(state, val) {
        // top toolbar is 50px. Filebar is 40px and agent filter tabs are 44px 
        state.tableHeight = `${Screen.height - 50 - 40 - 78 - val}px`;

        // q-tabs are 37px
        state.tabHeight = `${val - 37}px`;
      },
      SET_CLIENT_SPLITTER(state, val) {
        state.clientTreeSplitter = val;
      },
      setShowCommunityScripts(state, show) {
        state.showCommunityScripts = show
      },
      SET_AGENT_DBLCLICK_ACTION(state, action) {
        state.agentDblClickAction = action
      },
      SET_URL_ACTION(state, action) {
        state.agentUrlAction = action
      },
      SET_DEFAULT_AGENT_TBL_TAB(state, tab) {
        state.defaultAgentTblTab = tab
      },
      SET_CLIENT_TREE_SORT(state, val) {
        state.clientTreeSort = val
      },
      SET_HOSTED(state, val) {
        state.hosted = val
      }
    },
    actions: {
      setClientTreeSplitter(context, val) {
        axios.patch("/accounts/users/ui/", { client_tree_splitter: Math.trunc(val) }).then(r => {
          context.commit("SET_CLIENT_SPLITTER", val)
        })
          .catch(e => { })
      },
      setShowCommunityScripts(context, data) {
        axios.patch("/accounts/users/ui/", { show_community_scripts: data }).then(r => {
          context.commit("setShowCommunityScripts", data)
        })
          .catch(e => { })
      },
      toggleMaintenanceMode(context, data) {
        return axios.post("/agents/maintenance/", data)
      },
      getDashInfo(context) {
        return axios.get("/core/dashinfo/");
      },
      getUpdatedSites(context) {
        axios.get("/clients/clients/").then(r => {
          context.commit("getUpdatedSites", r.data);
        })
          .catch(e => { });
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
                raw: `Site | ${site.id} `,
                header: "generic",
                icon: "apartment",
                client: client.id,
                selectable: true,
                server_policy: site.server_policy,
                workstation_policy: site.workstation_policy,
                alert_template: site.alert_template,
                blockInheritance: site.block_policy_inheritance
              }

              if (site.maintenance_mode) { siteNode["color"] = "green" }
              else if (site.failing_checks.error) { siteNode["color"] = "negative" }
              else if (site.failing_checks.warning) { siteNode["color"] = "warning" }

              childSites.push(siteNode);
            }

            let clientNode = {
              label: client.name,
              id: client.id,
              raw: `Client | ${client.id} `,
              header: "root",
              icon: "business",
              server_policy: client.server_policy,
              workstation_policy: client.workstation_policy,
              alert_template: client.alert_template,
              blockInheritance: client.block_policy_inheritance,
              children: childSites
            }

            if (client.maintenance_mode) clientNode["color"] = "green"
            else if (client.failing_checks.error) { clientNode["color"] = "negative" }
            else if (client.failing_checks.warning) { clientNode["color"] = "warning" }

            output.push(clientNode);
          }


          if (state.clientTreeSort === "alphafail") {
            // move failing clients to the top
            const failing = output.filter(i => i.color === "negative" || i.color === "warning");
            const ok = output.filter(i => i.color !== "negative" && i.color !== "warning");
            const sortedByFailing = [...failing, ...ok];
            commit("loadTree", sortedByFailing);
          } else {
            commit("loadTree", output);
          }

        })
          .catch(e => { });
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
          .catch(e => { })
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
            .catch(e => { })
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
              });
          });
        }
      }
    }
  });

  return Store;
}

