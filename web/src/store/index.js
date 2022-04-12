import { createStore } from 'vuex'
import { Screen, Dark, LoadingBar } from 'quasar'
import axios from "axios";
import { formatDate } from "@/utils/format"

export default function () {
  const Store = new createStore({
    state() {
      return {
        username: localStorage.getItem("user_name") || null,
        token: localStorage.getItem("access_token") || null,
        tree: [],
        agents: [],
        treeReady: false,
        selectedTree: "",
        selectedRow: null,
        agentPlatform: "windows",
        agentTableLoading: false,
        needrefresh: false,
        refreshSummaryTab: false,
        tableHeight: "300px",
        tabHeight: "300px",
        showCommunityScripts: false,
        agentDblClickAction: "",
        agentUrlAction: null,
        defaultAgentTblTab: "server",
        clientTreeSort: "alphafail",
        clientTreeSplitter: 20,
        noCodeSign: false,
        hosted: false,
        clearSearchWhenSwitching: false,
        currentTRMMVersion: null,
        latestTRMMVersion: null,
        dateFormat: "MMM-DD-YYYY - HH:mm",
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
        return state.selectedRow;
      },
      showCommunityScripts(state) {
        return state.showCommunityScripts;
      },
      allClientsSelected(state) {
        return !state.selectedTree;
      },
      formatDate: (state, getters) => (date) => {
        if (!state.dateFormat) return formatDate(date)
        else return formatDate(date, state.dateFormat)
      }
    },
    mutations: {
      AGENT_TABLE_LOADING(state, visible) {
        state.agentTableLoading = visible;
      },
      setActiveRow(state, agent_id) {
        state.selectedRow = agent_id;
      },
      setAgentPlatform(state, agentPlatform) {
        state.agentPlatform = agentPlatform;
      },
      retrieveToken(state, { token, username }) {
        state.token = token;
        state.username = username;
      },
      destroyCommit(state) {
        state.token = null;
        state.username = null;
      },
      loadTree(state, treebar) {
        state.tree = treebar;
        state.treeReady = true;
      },
      destroySubTable(state) {
        state.selectedRow = null;
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
      },
      setClearSearchWhenSwitching(state, val) {
        state.clearSearchWhenSwitching = val
      },
      setLatestTRMMVersion(state, val) {
        state.latestTRMMVersion = val
      },
      setCurrentTRMMVersion(state, val) {
        state.currentTRMMVersion = val
      },
      setAgents(state, agents) {
        state.agents = agents
      },
      setRefreshSummaryTab(state, val) {
        state.refreshSummaryTab = val
      },
      setSelectedTree(state, val) {
        state.selectedTree = val
      },
      setDateFormat(state, val) {
        state.dateFormat = val
      },
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
      refreshDashboard({ state, commit, dispatch }, clearTreeSelected = false) {
        if (clearTreeSelected || !state.selectedTree) {
          dispatch("loadAgents")
          commit("setSelectedTree", "")
        }
        else if (state.selectedTree.includes("Client")) {
          dispatch("loadAgents", `?client=${state.selectedTree.split("|")[1]}`)
        }
        else if (state.selectedTree.includes("Site")) {
          dispatch("loadAgents", `?site=${state.selectedTree.split("|")[1]}`)
        } else {
          console.error("refreshDashboard has incorrect parameters")
          return
        }

        if (clearTreeSelected) commit("destroySubTable")

        dispatch("loadTree");
        dispatch("getDashInfo", false);
      },
      async loadAgents(context, params = null) {
        context.commit("AGENT_TABLE_LOADING", true);
        try {
          const { data } = await axios.get(`/agents/${params ? params : ""}`)
          context.commit("setAgents", data);
        } catch (e) {
          console.error(e)
        }

        context.commit("AGENT_TABLE_LOADING", false);
      },
      async getDashInfo(context, edited = true) {
        const { data } = await axios.get("/core/dashinfo/");
        if (edited) {
          LoadingBar.setDefaults({ color: data.loading_bar_color });
          context.commit("setClearSearchWhenSwitching", data.clear_search_when_switching);
          context.commit("SET_DEFAULT_AGENT_TBL_TAB", data.default_agent_tbl_tab);
          context.commit("SET_CLIENT_TREE_SORT", data.client_tree_sort);
          context.commit("SET_CLIENT_SPLITTER", data.client_tree_splitter);
        }
        Dark.set(data.dark_mode);
        context.commit("setCurrentTRMMVersion", data.trmm_version);
        context.commit("setLatestTRMMVersion", data.latest_trmm_ver);
        context.commit("SET_AGENT_DBLCLICK_ACTION", data.dbl_click_action);
        context.commit("SET_URL_ACTION", data.url_action);
        context.commit("setShowCommunityScripts", data.show_community_scripts);
        context.commit("SET_HOSTED", data.hosted);

        if (data.date_format && data.date_format !== "") context.commit("setDateFormat", data.date_format)
        else context.commit("setDateFormat", data.default_date_format)

      },
      loadTree({ commit, state }) {
        axios.get("/clients/").then(r => {

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
                selectable: true,
                site: site
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
              children: childSites,
              client: client
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
          .catch(e => {
            state.treeReady = true
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

