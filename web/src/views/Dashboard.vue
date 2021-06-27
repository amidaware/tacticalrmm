<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-grey-9 text-white">
      <q-banner v-if="needRefresh" inline-actions class="bg-red text-white text-center">
        You are viewing an outdated version of this page.
        <q-btn color="dark" icon="refresh" label="Refresh" @click="reload" />
      </q-banner>
      <q-toolbar>
        <q-btn dense flat push @click="refreshEntireSite" icon="refresh" />
        <q-toolbar-title>
          Tactical RMM<span class="text-overline q-ml-sm">v{{ currentTRMMVersion }}</span>
          <span
            class="text-overline q-ml-md"
            v-if="latestTRMMVersion !== 'error' && currentTRMMVersion !== latestTRMMVersion"
            ><q-badge color="warning"
              ><a :href="latestReleaseURL" target="_blank">v{{ latestTRMMVersion }} available</a></q-badge
            ></span
          >
        </q-toolbar-title>

        <!-- temp dark mode toggle -->
        <q-toggle v-model="darkMode" class="q-mr-sm" checked-icon="nights_stay" unchecked-icon="wb_sunny" />

        <!-- Devices Chip -->
        <q-chip class="cursor-pointer">
          <q-avatar size="md" icon="devices" color="primary" />
          <q-tooltip :delay="600" anchor="top middle" self="top middle">Agent Count</q-tooltip>
          {{ totalAgents }}
          <q-menu>
            <q-list dense>
              <q-item-label header>Servers</q-item-label>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="fa fa-server" size="sm" color="primary" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Total: {{ serverCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="power_off" size="sm" color="negative" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Offline: {{ serverOfflineCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item-label header>Workstations</q-item-label>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="computer" size="sm" color="primary" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Total: {{ workstationCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="power_off" size="sm" color="negative" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Offline: {{ workstationOfflineCount }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <AlertsIcon />

        <q-btn-dropdown flat no-caps stretch :label="user">
          <q-list>
            <q-item clickable v-ripple @click="showUserPreferencesModal = true" v-close-popup>
              <q-item-section>
                <q-item-label>Preferences</q-item-label>
              </q-item-section>
            </q-item>
            <q-item to="/expired" exact>
              <q-item-section>
                <q-item-label>Logout</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <FileBar />
      <q-splitter v-model="clientTreeSplitter">
        <template v-slot:before>
          <div v-if="!treeReady" class="q-pa-sm q-gutter-sm text-center" style="height: 30vh">
            <q-spinner size="40px" color="primary" />
          </div>
          <div v-else class="q-pa-sm q-gutter-sm scroll" style="height: 85vh">
            <q-list dense class="rounded-borders">
              <q-item clickable v-ripple :active="allClientsActive" @click="clearTreeSelected">
                <q-item-section avatar>
                  <q-icon name="fas fa-home" />
                </q-item-section>
                <q-item-section>All Clients</q-item-section>
              </q-item>
              <q-tree
                ref="tree"
                :nodes="clientsTree"
                node-key="raw"
                no-nodes-label="No Clients"
                selected-color="primary"
                v-model:selected="selectedTree"
                @update:selected="loadFrame(selectedTree)"
              >
                <template v-slot:default-header="props">
                  <div class="row">
                    <q-icon :name="props.node.icon" :color="props.node.color" class="q-mr-sm" />
                    <span
                      >{{ props.node.label }} <q-tooltip :delay="600">ID: {{ props.node.id }}</q-tooltip></span
                    >

                    <q-menu context-menu>
                      <q-list dense style="min-width: 200px">
                        <q-item clickable v-close-popup @click="showEditModal(props.node)">
                          <q-item-section side>
                            <q-icon name="edit" />
                          </q-item-section>
                          <q-item-section>Edit</q-item-section>
                        </q-item>
                        <q-item clickable v-close-popup @click="showDeleteModal(props.node)">
                          <q-item-section side>
                            <q-icon name="delete" />
                          </q-item-section>
                          <q-item-section>Delete</q-item-section>
                        </q-item>

                        <q-separator></q-separator>

                        <q-item
                          v-if="props.node.children"
                          clickable
                          v-close-popup
                          @click="showAddSiteModal(props.node)"
                        >
                          <q-item-section side>
                            <q-icon name="add" />
                          </q-item-section>
                          <q-item-section>Add Site</q-item-section>
                        </q-item>

                        <q-item clickable v-close-popup @click="showToggleMaintenance(props.node)">
                          <q-item-section side>
                            <q-icon name="construction" />
                          </q-item-section>
                          <q-item-section>{{ menuMaintenanceText(props.node) }}</q-item-section>
                        </q-item>

                        <q-item
                          v-if="props.node.children === undefined"
                          clickable
                          v-close-popup
                          @click="showInstallAgent(props.node)"
                        >
                          <q-item-section side>
                            <q-icon name="cloud_download" />
                          </q-item-section>
                          <q-item-section>Install Agent</q-item-section>
                        </q-item>

                        <q-item clickable v-close-popup @click="showPolicyAdd(props.node)">
                          <q-item-section side>
                            <q-icon name="policy" />
                          </q-item-section>
                          <q-item-section>Assign Automation Policy</q-item-section>
                        </q-item>

                        <q-item clickable v-close-popup @click="showAlertTemplateAdd(props.node)">
                          <q-item-section side>
                            <q-icon name="error" />
                          </q-item-section>
                          <q-item-section>Assign Alert Template</q-item-section>
                        </q-item>

                        <q-separator></q-separator>

                        <q-item clickable v-close-popup>
                          <q-item-section>Close</q-item-section>
                        </q-item>
                      </q-list>
                    </q-menu>
                  </div>
                </template>
              </q-tree>
            </q-list>
          </div>
        </template>

        <template v-slot:after>
          <q-splitter
            v-model="innerModel"
            reverse
            horizontal
            style="height: 87vh"
            @update:model-value="setSplitter(innerModel)"
          >
            <template v-slot:before>
              <div class="row">
                <q-tabs
                  v-model="tab"
                  dense
                  no-caps
                  inline-label
                  class="text-grey"
                  active-color="primary"
                  indicator-color="primary"
                  align="left"
                  narrow-indicator
                >
                  <q-tab name="server" icon="fas fa-server" label="Servers" />
                  <q-tab name="workstation" icon="computer" label="Workstations" />
                  <q-tab name="mixed" label="Mixed" />
                </q-tabs>
                <q-space />
                <q-input
                  v-model="search"
                  style="width: 450px"
                  label="Search"
                  dense
                  outlined
                  clearable
                  @clear="clearFilter"
                  class="q-pr-md q-pb-xs"
                >
                  <template v-slot:prepend>
                    <q-icon name="search" color="primary" />
                  </template>
                  <template v-slot:after>
                    <q-btn round dense flat icon="filter_alt" :color="isFilteringTable ? 'green' : ''">
                      <q-menu>
                        <q-list dense>
                          <q-item-label header>Filter Agent Table</q-item-label>

                          <q-item>
                            <q-item-section side>
                              <q-checkbox v-model="filterChecksFailing" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Checks Failing</q-item-label>
                            </q-item-section>
                          </q-item>

                          <q-item>
                            <q-item-section side>
                              <q-checkbox v-model="filterPatchesPending" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Patches Pending</q-item-label>
                            </q-item-section>
                          </q-item>

                          <q-item>
                            <q-item-section side>
                              <q-checkbox v-model="filterActionsPending" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Actions Pending</q-item-label>
                            </q-item-section>
                          </q-item>

                          <q-item>
                            <q-item-section side>
                              <q-checkbox v-model="filterRebootNeeded" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Reboot Needed</q-item-label>
                            </q-item-section>
                          </q-item>

                          <q-item-label header>Availability</q-item-label>

                          <q-item>
                            <q-item-section side>
                              <q-radio val="all" v-model="filterAvailability" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Show All Agents</q-item-label>
                            </q-item-section>
                          </q-item>

                          <q-item>
                            <q-item-section side>
                              <q-radio val="online" v-model="filterAvailability" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Show Online Only</q-item-label>
                            </q-item-section>
                          </q-item>

                          <q-item>
                            <q-item-section side>
                              <q-radio val="offline" v-model="filterAvailability" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Show Offline Only</q-item-label>
                            </q-item-section>
                          </q-item>

                          <q-item>
                            <q-item-section side>
                              <q-radio val="offline_30days" v-model="filterAvailability" />
                            </q-item-section>

                            <q-item-section>
                              <q-item-label>Show Offline for over 30 days</q-item-label>
                            </q-item-section>
                          </q-item>
                        </q-list>

                        <div class="row no-wrap q-pa-md">
                          <div class="column">
                            <q-btn v-close-popup label="Apply" color="primary" @click="applyFilter" />
                          </div>
                          <q-space />
                          <div class="column">
                            <q-btn label="Clear" @click="clearFilter" />
                          </div>
                        </div>
                      </q-menu>
                    </q-btn>
                  </template>
                </q-input>
              </div>
              <AgentTable
                :frame="filteredAgents"
                :columns="columns"
                :userName="user"
                :search="search"
                :visibleColumns="visibleColumns"
                @edit="refreshEntireSite"
              />
            </template>
            <template v-slot:separator>
              <q-avatar color="primary" text-color="white" size="30px" icon="drag_indicator" />
            </template>
            <template v-slot:after>
              <SubTableTabs @edit="refreshEntireSite" />
            </template>
          </q-splitter>
        </template>
      </q-splitter>
    </q-page-container>

    <!-- install agent modal -->
    <q-dialog v-model="showInstallAgentModal" @hide="closeInstallAgent">
      <InstallAgent @close="closeInstallAgent" :sitepk="parseInt(sitePk)" />
    </q-dialog>
    <!-- user preferences modal -->
    <q-dialog v-model="showUserPreferencesModal">
      <UserPreferences @close="showUserPreferencesModal = false" @edit="getDashInfo" />
    </q-dialog>
  </q-layout>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapState, mapGetters } from "vuex";
import { getBaseUrl } from "@/boot/axios";
import FileBar from "@/components/FileBar";
import AgentTable from "@/components/AgentTable";
import SubTableTabs from "@/components/SubTableTabs";
import AlertsIcon from "@/components/AlertsIcon";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import ClientsForm from "@/components/modals/clients/ClientsForm";
import SitesForm from "@/components/modals/clients/SitesForm";
import DeleteClient from "@/components/modals/clients/DeleteClient";
import InstallAgent from "@/components/modals/agents/InstallAgent";
import UserPreferences from "@/components/modals/coresettings/UserPreferences";
import AlertTemplateAdd from "@/components/modals/alerts/AlertTemplateAdd";

export default {
  name: "Dashboard",
  emits: [],
  components: {
    FileBar,
    AgentTable,
    SubTableTabs,
    AlertsIcon,
    InstallAgent,
    UserPreferences,
  },
  mixins: [mixins],
  data() {
    return {
      ws: null,
      showInstallAgentModal: false,
      sitePk: null,
      serverCount: 0,
      serverOfflineCount: 0,
      workstationCount: 0,
      workstationOfflineCount: 0,
      selectedTree: "",
      innerModel: 50,
      clientActive: "",
      siteActive: "",
      frame: [],
      poll: null,
      search: "",
      filterTextLength: 0,
      filterAvailability: "all",
      filterPatchesPending: false,
      filterActionsPending: false,
      filterChecksFailing: false,
      filterRebootNeeded: false,
      currentTRMMVersion: null,
      latestTRMMVersion: "error",
      showUserPreferencesModal: false,
      columns: [
        {
          name: "smsalert",
          align: "left",
        },
        {
          name: "emailalert",
          align: "left",
        },
        {
          name: "dashboardalert",
          align: "left",
        },
        {
          name: "checks-status",
          align: "left",
          field: "checks",
          sortable: true,
          sort: (a, b, rowA, rowB) =>
            parseInt(b.failing) - parseInt(a.failing) ||
            parseInt(b.warning) - parseInt(a.warning) ||
            parseInt(b.info) - parseInt(a.info),
        },
        {
          name: "client_name",
          label: "Client",
          field: "client_name",
          sortable: true,
          align: "left",
        },
        {
          name: "site_name",
          label: "Site",
          field: "site_name",
          sortable: true,
          align: "left",
        },
        {
          name: "hostname",
          label: "Hostname",
          field: "hostname",
          sortable: true,
          align: "left",
        },
        {
          name: "description",
          label: "Description",
          field: "description",
          sortable: true,
          align: "left",
        },
        {
          name: "user",
          label: "User",
          field: "logged_username",
          sortable: true,
          align: "left",
        },
        {
          name: "italic",
          field: "italic",
        },
        {
          name: "patchespending",
          field: "has_patches_pending",
          align: "left",
          sortable: true,
        },
        {
          name: "pendingactions",
          field: "pending_actions_count",
          align: "left",
          sortable: true,
        },
        {
          name: "needs_reboot",
          field: "needs_reboot",
          align: "left",
          sortable: true,
        },
        {
          name: "agentstatus",
          field: "status",
          align: "left",
          sortable: true,
        },
        {
          name: "last_seen",
          label: "Last Response",
          field: "last_seen",
          sortable: true,
          align: "left",
          sort: (a, b) => this.dateStringToUnix(a) - this.dateStringToUnix(b),
        },
        {
          name: "boot_time",
          label: "Boot Time",
          field: "boot_time",
          sortable: true,
          align: "left",
        },
      ],
      visibleColumns: [
        "smsalert",
        "emailalert",
        "dashboardalert",
        "checks-status",
        "client_name",
        "site_name",
        "hostname",
        "description",
        "user",
        "patchespending",
        "pendingactions",
        "agentstatus",
        "needs_reboot",
        "last_seen",
        "boot_time",
      ],
    };
  },
  watch: {
    search(newVal, oldVal) {
      if (newVal === "") this.clearFilter();
      else if (newVal.length < this.filterTextLength) this.clearFilter();
    },
  },
  methods: {
    setupWS() {
      console.log("Starting websocket");
      const proto = process.env.NODE_ENV === "production" || process.env.DOCKER_BUILD ? "wss" : "ws";
      this.ws = new WebSocket(`${proto}://${this.wsUrl}/ws/dashinfo/?access_token=${this.token}`);
      this.ws.onopen = e => {
        console.log("Connected to ws");
      };
      this.ws.onmessage = e => {
        const data = JSON.parse(e.data);
        this.serverCount = data.total_server_count;
        this.serverOfflineCount = data.total_server_offline_count;
        this.workstationCount = data.total_workstation_count;
        this.workstationOfflineCount = data.total_workstation_offline_count;
      };
      this.ws.onclose = e => {
        console.log(`Closed code: ${e.code}`);
        if (e.code !== 1000) {
          setTimeout(() => {
            this.setupWS();
          }, 2 * 1000);
        }
      };
      this.ws.onerror = err => {
        console.log(`ERROR! Code: ${err.code}`);
        this.ws.close();
      };
    },
    refreshEntireSite() {
      this.$store.dispatch("loadTree");
      this.getDashInfo(false);

      if (this.allClientsActive) {
        this.loadAllClients();
      } else {
        this.loadFrame(this.selectedTree, false);
      }

      if (this.selectedAgentPk) {
        const pk = this.selectedAgentPk;
        this.$store.dispatch("loadSummary", pk);
        this.$store.dispatch("loadChecks", pk);
        this.$store.dispatch("loadAutomatedTasks", pk);
        this.$store.dispatch("loadWinUpdates", pk);
        this.$store.dispatch("loadInstalledSoftware", pk);
        this.$store.dispatch("loadNotes", pk);
      }
    },
    loadFrame(activenode, destroySub = true) {
      this.clearFilter();
      if (destroySub) this.$store.commit("destroySubTable");

      let execute = false;
      let urlType, id;
      let data = {};

      if (typeof activenode === "string") {
        urlType = activenode.split("|")[0];
        id = activenode.split("|")[1];

        if (urlType === "Client") {
          data.clientPK = id;
          execute = true;
        } else if (urlType === "Site") {
          data.sitePK = id;
          execute = true;
        }

        if (execute) {
          this.$store.commit("AGENT_TABLE_LOADING", true);
          this.$axios
            .patch("/agents/listagents/", data)
            .then(r => {
              this.frame = r.data;
              this.$store.commit("AGENT_TABLE_LOADING", false);
            })
            .catch(e => {});
        }
      }
    },
    getTree() {
      this.loadAllClients();
      this.$store.dispatch("loadTree");
    },
    clearTreeSelected() {
      this.clearFilter();
      this.selectedTree = "";
      this.getTree();
    },
    clearSite() {
      this.siteActive = "";
      this.$store.commit("destroySubTable");
    },
    loadAllClients() {
      this.$store.commit("AGENT_TABLE_LOADING", true);
      this.$axios
        .patch("/agents/listagents/")
        .then(r => {
          this.frame = r.data;
          this.$store.commit("AGENT_TABLE_LOADING", false);
        })
        .catch(e => {});
    },
    showPolicyAdd(node) {
      this.$q
        .dialog({
          component: PolicyAdd,
          componentProps: {
            type: node.children ? "client" : "site",
            object: node,
          },
        })
        .onOk(() => {
          this.clearTreeSelected();
        });
    },
    showAddSiteModal(node) {
      this.$q.dialog({
        component: SitesForm,
        componentProps: {
          client: node.id,
        },
      });
    },
    showEditModal(node) {
      let props = {};
      if (node.children) {
        props.client = { id: node.id, name: node.label };
      } else {
        props.site = { id: node.id, name: node.label, client: node.client };
      }

      this.$q.dialog({
        component: node.children ? ClientsForm : SitesForm,
        componentProps: {
          ...props,
        },
      });
    },
    showDeleteModal(node) {
      this.$q.dialog({
        component: DeleteClient,
        componentProps: {
          object: { id: node.id, name: node.label },
          type: node.children ? "client" : "site",
        },
      });
    },
    showInstallAgent(node) {
      this.sitePk = node.id;
      this.showInstallAgentModal = true;
    },
    closeInstallAgent() {
      this.showInstallAgentModal = false;
      this.sitePk = null;
    },
    showAlertTemplateAdd(node) {
      this.$q
        .dialog({
          component: AlertTemplateAdd,
          componentProps: {
            type: node.children ? "client" : "site",
            object: node,
          },
        })
        .onOk(() => {
          this.clearTreeSelected();
        });
    },
    reload() {
      this.$store.dispatch("reload");
    },
    livePoll() {
      this.poll = setInterval(() => {
        this.$store.dispatch("checkVer");
        this.getDashInfo(false);
      }, 60 * 5 * 1000);
    },
    setSplitter(val) {
      this.$store.commit("SET_SPLITTER", val);
    },
    getDashInfo(edited = true) {
      this.$store.dispatch("getDashInfo").then(r => {
        if (edited) {
          this.$q.loadingBar.setDefaults({ color: r.data.loading_bar_color });
          this.$store.commit("SET_DEFAULT_AGENT_TBL_TAB", r.data.default_agent_tbl_tab);
          this.$store.commit("SET_CLIENT_TREE_SORT", r.data.client_tree_sort);
          this.$store.commit("SET_CLIENT_SPLITTER", r.data.client_tree_splitter);
        }
        this.$q.dark.set(r.data.dark_mode);
        this.currentTRMMVersion = r.data.trmm_version;
        this.latestTRMMVersion = r.data.latest_trmm_ver;
        this.$store.commit("SET_AGENT_DBLCLICK_ACTION", r.data.dbl_click_action);
        this.$store.commit("SET_URL_ACTION", r.data.url_action);
        this.$store.commit("setShowCommunityScripts", r.data.show_community_scripts);
        this.$store.commit("SET_HOSTED", r.data.hosted);
      });
    },
    showToggleMaintenance(node) {
      let data = {
        id: node.id,
        type: node.raw.split("|")[0],
        action: node.color === "green" ? false : true,
      };

      const text = node.color === "green" ? "Maintenance mode was disabled" : "Maintenance mode was enabled";
      this.$store.dispatch("toggleMaintenanceMode", data).then(response => {
        this.notifySuccess(text);
        this.getTree();
      });
    },
    menuMaintenanceText(node) {
      return node.color === "green" ? "Disable Maintenance Mode" : "Enable Maintenance Mode";
    },
    clearFilter() {
      this.filterTextLength = 0;
      this.filterPatchesPending = false;
      this.filterRebootNeeded = false;
      this.filterChecksFailing = false;
      this.filterActionsPending = false;
      this.filterAvailability = "all";
      this.search = "";
    },
    applyFilter() {
      // clear search if availability changes to all
      if (
        this.filterAvailability === "all" &&
        (this.search.includes("is:online") || this.search.includes("is:offline") || this.search.includes("is:expired"))
      )
        this.clearFilter();

      // don't apply filter if nothing is being filtered
      if (!this.isFilteringTable) return;

      let filterText = "";

      if (this.filterPatchesPending) {
        filterText += "is:patchespending ";
      }

      if (this.filterActionsPending) {
        filterText += "is:actionspending ";
      }

      if (this.filterChecksFailing) {
        filterText += "is:checksfailing ";
      }

      if (this.filterRebootNeeded) {
        filterText += "is:rebootneeded ";
      }

      if (this.filterAvailability !== "all") {
        if (this.filterAvailability === "online") {
          filterText += "is:online ";
        } else if (this.filterAvailability === "offline") {
          filterText += "is:offline ";
        } else if (this.filterAvailability === "offline_30days") {
          filterText += "is:expired ";
        }
      }

      this.search = filterText;
      this.filterTextLength = filterText.length - 1;
    },
  },
  computed: {
    ...mapState({
      user: state => state.username,
      clientsTree: state => state.tree,
      treeReady: state => state.treeReady,
      clients: state => state.clients,
    }),
    ...mapGetters(["selectedAgentPk", "needRefresh"]),
    latestReleaseURL() {
      return this.latestTRMMVersion !== "error"
        ? `https://github.com/wh1te909/tacticalrmm/releases/tag/v${this.latestTRMMVersion}`
        : "";
    },
    wsUrl() {
      return getBaseUrl().split("://")[1];
    },
    token() {
      return this.$store.state.token;
    },
    clientTreeSplitter: {
      get() {
        return this.$store.state.clientTreeSplitter;
      },
      set(newVal) {
        this.$store.commit("SET_CLIENT_SPLITTER", newVal);
      },
    },
    tab: {
      get() {
        return this.$store.state.defaultAgentTblTab;
      },
      set(newVal) {
        this.$store.commit("SET_DEFAULT_AGENT_TBL_TAB", newVal);
      },
    },
    allClientsActive() {
      return this.selectedTree === "";
    },
    filteredAgents() {
      if (this.tab === "mixed") return this.frame;
      else return this.frame.filter(k => k.monitoring_type === this.tab);
    },
    activeNode() {
      return {
        client: this.clientActive,
        site: this.siteActive,
      };
    },
    isFilteringTable() {
      return (
        this.filterPatchesPending ||
        this.filterActionsPending ||
        this.filterChecksFailing ||
        this.filterRebootNeeded ||
        this.filterAvailability !== "all"
      );
    },
    totalAgents() {
      return this.serverCount + this.workstationCount;
    },
    totalOfflineAgents() {
      return this.serverOfflineCount + this.workstationOfflineCount;
    },
    darkMode: {
      get() {
        return this.$q.dark.isActive;
      },
      set(value) {
        this.$axios.patch("/accounts/users/ui/", { dark_mode: value }).catch(e => {});
        this.$q.dark.set(value);
      },
    },
  },
  mounted() {
    this.setupWS();
    this.getDashInfo();
    this.$store.dispatch("getUpdatedSites");
    this.$store.dispatch("checkVer");
    this.getTree();

    this.livePoll();
  },
  beforeUnmount() {
    this.ws.close();
    clearInterval(this.poll);
  },
};
</script>

<style>
.my-menu-link {
  color: white;
  background: lightgray;
}
</style>