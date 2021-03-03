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
          Tactical RMM<span class="text-overline">&nbsp;&nbsp;&nbsp;v{{ currentTRMMVersion }}</span>
        </q-toolbar-title>

        <!-- temp dark mode toggle -->
        <q-toggle
          v-model="darkMode"
          class="q-mr-sm"
          @input="toggleDark(darkMode)"
          checked-icon="nights_stay"
          unchecked-icon="wb_sunny"
        />

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
      <FileBar :clients="clients" @edited="refreshEntireSite" />
      <q-splitter v-model="outsideModel">
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
                :selected.sync="selectedTree"
                @update:selected="loadFrame(selectedTree)"
              >
                <template v-slot:default-header="props">
                  <div class="row">
                    <q-icon :name="props.node.icon" :color="props.node.color" class="q-mr-sm" />
                    <span>{{ props.node.label }}</span>

                    <q-menu context-menu>
                      <q-list dense style="min-width: 200px">
                        <q-item clickable v-close-popup @click="showEditModal(props.node, 'edit')">
                          <q-item-section side>
                            <q-icon name="edit" />
                          </q-item-section>
                          <q-item-section>Edit</q-item-section>
                        </q-item>
                        <q-item clickable v-close-popup @click="showDeleteModal(props.node, 'delete')">
                          <q-item-section side>
                            <q-icon name="delete" />
                          </q-item-section>
                          <q-item-section>Delete</q-item-section>
                        </q-item>

                        <q-separator></q-separator>

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
          <q-splitter v-model="innerModel" reverse horizontal style="height: 87vh" @input="setSplitter(innerModel)">
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
                :tab="tab"
                :userName="user"
                :search="search"
                :visibleColumns="visibleColumns"
                @refreshEdit="refreshEntireSite"
              />
            </template>
            <template v-slot:separator>
              <q-avatar color="primary" text-color="white" size="30px" icon="drag_indicator" />
            </template>
            <template v-slot:after>
              <SubTableTabs />
            </template>
          </q-splitter>
        </template>
      </q-splitter>
    </q-page-container>

    <!-- client form modal -->
    <q-dialog v-model="showClientsFormModal" @hide="closeClientsFormModal">
      <ClientsForm
        @close="closeClientsFormModal"
        :op="clientOp"
        :clientpk="deleteEditModalPk"
        @edited="refreshEntireSite"
      />
    </q-dialog>
    <!-- edit site modal -->
    <q-dialog v-model="showSitesFormModal" @hide="closeClientsFormModal">
      <SitesForm
        @close="closeClientsFormModal"
        :op="clientOp"
        :sitepk="deleteEditModalPk"
        @edited="refreshEntireSite"
      />
    </q-dialog>
    <!-- install agent modal -->
    <q-dialog v-model="showInstallAgentModal" @hide="closeInstallAgent">
      <InstallAgent @close="closeInstallAgent" :sitepk="parseInt(sitePk)" />
    </q-dialog>
    <!-- user preferences modal -->
    <q-dialog v-model="showUserPreferencesModal">
      <UserPreferences @close="showUserPreferencesModal = false" @edited="getDashInfo" />
    </q-dialog>
  </q-layout>
</template>

<script>
import mixins from "@/mixins/mixins";
import { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";
import { mapState, mapGetters } from "vuex";
import FileBar from "@/components/FileBar";
import AgentTable from "@/components/AgentTable";
import SubTableTabs from "@/components/SubTableTabs";
import AlertsIcon from "@/components/AlertsIcon";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import ClientsForm from "@/components/modals/clients/ClientsForm";
import SitesForm from "@/components/modals/clients/SitesForm";
import InstallAgent from "@/components/modals/agents/InstallAgent";
import UserPreferences from "@/components/modals/coresettings/UserPreferences";
import AlertTemplateAdd from "@/components/modals/alerts/AlertTemplateAdd";

export default {
  components: {
    FileBar,
    AgentTable,
    SubTableTabs,
    AlertsIcon,
    ClientsForm,
    SitesForm,
    InstallAgent,
    UserPreferences,
  },
  mixins: [mixins],
  data() {
    return {
      darkMode: true,
      showClientsFormModal: false,
      showSitesFormModal: false,
      deleteEditModalPk: null,
      showInstallAgentModal: false,
      sitePk: null,
      clientOp: null,
      serverCount: 0,
      serverOfflineCount: 0,
      workstationCount: 0,
      workstationOfflineCount: 0,
      outsideModel: 11,
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
          sort: (a, b, rowA, rowB) => parseInt(b.failing) - a.failing,
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
          field: "patches_pending",
          align: "left",
          sortable: true,
        },
        {
          name: "pendingactions",
          field: "pending_actions",
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
          sortable: false,
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
    toggleDark(val) {
      this.$q.dark.set(val);
      this.$axios.patch("/accounts/users/ui/", { dark_mode: val });
    },
    refreshEntireSite() {
      this.$store.dispatch("loadTree");
      this.getDashInfo(false);
      this.getAgentCounts();

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
          this.$axios.patch("/agents/listagents/", data).then(r => {
            this.frame = r.data;
            this.$store.commit("AGENT_TABLE_LOADING", false);
          });
        }
      }
    },
    getTree() {
      this.loadAllClients();
      this.$store.dispatch("loadTree");
    },
    clearTreeSelected() {
      this.selectedTree = "";
      this.getTree();
    },
    clearSite() {
      this.siteActive = "";
      this.$store.commit("destroySubTable");
    },
    loadAllClients() {
      this.$store.commit("AGENT_TABLE_LOADING", true);
      this.$axios.patch("/agents/listagents/").then(r => {
        this.frame = r.data;
        this.$store.commit("AGENT_TABLE_LOADING", false);
      });
    },
    showPolicyAdd(node) {
      if (node.children) {
        this.$q
          .dialog({
            component: PolicyAdd,
            parent: this,
            type: "client",
            object: node,
          })
          .onOk(() => {
            this.getTree();
          });
      } else {
        this.$q
          .dialog({
            component: PolicyAdd,
            parent: this,
            type: "site",
            object: node,
          })
          .onOk(() => {
            this.getTree();
          });
      }
    },
    showEditModal(node, op) {
      this.deleteEditModalPk = node.id;
      this.clientOp = op;
      if (node.children) {
        this.showClientsFormModal = true;
      } else {
        this.showSitesFormModal = true;
      }
    },
    showDeleteModal(node, op) {
      this.deleteEditModalPk = node.id;
      this.clientOp = op;
      if (node.children) {
        this.showClientsFormModal = true;
      } else {
        this.showSitesFormModal = true;
      }
    },
    closeClientsFormModal() {
      this.showClientsFormModal = false;
      this.showSitesFormModal = false;
      this.deleteEditModalPk = null;
      this.clientOp = null;
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
          parent: this,
          type: node.children ? "client" : "site",
          object: node,
        })
        .onOk(() => {
          this.getTree();
        });
    },
    reload() {
      this.$store.dispatch("reload");
    },
    livePoll() {
      this.poll = setInterval(() => {
        this.$store.dispatch("checkVer");
        this.getAgentCounts();
        this.getDashInfo(false);
      }, 60 * 5 * 1000);
    },
    setSplitter(val) {
      this.$store.commit("SET_SPLITTER", val);
    },
    getAgentCounts(selected) {
      this.$store.dispatch("getAgentCounts").then(r => {
        this.serverCount = r.data.total_server_count;
        this.serverOfflineCount = r.data.total_server_offline_count;
        this.workstationCount = r.data.total_workstation_count;
        this.workstationOfflineCount = r.data.total_workstation_offline_count;
      });
    },
    getDashInfo(edited = true) {
      this.$store.dispatch("getDashInfo").then(r => {
        if (edited) this.$store.commit("SET_DEFAULT_AGENT_TBL_TAB", r.data.default_agent_tbl_tab);
        this.darkMode = r.data.dark_mode;
        this.$q.dark.set(this.darkMode);
        this.currentTRMMVersion = r.data.trmm_version;
        this.$store.commit("SET_AGENT_DBLCLICK_ACTION", r.data.dbl_click_action);
        this.$store.commit("setShowCommunityScripts", r.data.show_community_scripts);
      });
    },
    showToggleMaintenance(node) {
      let data = {
        id: node.id,
        type: node.raw.split("|")[0],
        action: node.color === "warning" ? false : true,
      };

      const text = node.color === "warning" ? "Maintenance mode was disabled" : "Maintenance mode was enabled";
      this.$store
        .dispatch("toggleMaintenanceMode", data)
        .then(response => {
          this.$q.notify(notifySuccessConfig(text));
          this.getTree();
        })
        .catch(error => {
          this.$q.notify(notifyErrorConfig("An Error occured. Please try again"));
        });
    },
    menuMaintenanceText(node) {
      return node.color === "warning" ? "Disable Maintenance Mode" : "Enable Maintenance Mode";
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
    tab: {
      get: function () {
        return this.$store.state.defaultAgentTblTab;
      },
      set: function (newVal) {
        this.$store.commit("SET_DEFAULT_AGENT_TBL_TAB", newVal);
      },
    },
    allClientsActive() {
      return this.selectedTree === "";
    },
    filteredAgents() {
      if (this.tab === "mixed") return Object.freeze(this.frame);
      return Object.freeze(this.frame.filter(k => k.monitoring_type === this.tab));
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
  },
  created() {
    this.getDashInfo();
    this.$store.dispatch("getUpdatedSites");
    this.$store.dispatch("checkVer");
    this.getAgentCounts();
    this.getTree();
  },
  mounted() {
    this.livePoll();
  },
  beforeDestroy() {
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