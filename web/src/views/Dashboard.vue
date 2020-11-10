<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-grey-9 text-white">
      <q-banner v-if="needRefresh" inline-actions class="bg-red text-white text-center">
        You are viewing an outdated version of this page.
        <q-btn color="dark" icon="refresh" label="Refresh" @click="reload" />
      </q-banner>
      <q-toolbar>
        <q-btn dense flat push @click="refreshEntireSite" icon="refresh" />
        <q-toolbar-title
          >Tactical RMM<span class="text-overline">&nbsp;&nbsp;&nbsp;v{{ currentTRMMVersion }}</span></q-toolbar-title
        >

        <!-- Devices Chip -->
        <q-chip color="white" class="cursor-pointer">
          <q-avatar size="md" icon="devices" color="primary" text-color="white" />
          <q-tooltip :delay="600" anchor="top middle" self="top middle">Agent Count</q-tooltip>
          {{ totalAgents }}
          <q-menu>
            <q-list dense>
              <q-item-label header>Servers</q-item-label>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="fa fa-server" size="sm" color="primary" text-color="white" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Total: {{ serverCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="power_off" size="sm" color="negative" text-color="white" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Offline: {{ serverOfflineCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item-label header>Workstations</q-item-label>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="computer" size="sm" color="primary" text-color="white" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Total: {{ workstationCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="power_off" size="sm" color="negative" text-color="white" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Offline: {{ workstationOfflineCount }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <!--<AlertsIcon />-->

        <q-btn-dropdown flat no-caps stretch :label="user">
          <q-list>
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
          <div v-else class="q-pa-sm q-gutter-sm">
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

                        <q-item clickable v-close-popup @click="showPolicyAdd(props.node)">
                          <q-item-section side>
                            <q-icon name="policy" />
                          </q-item-section>
                          <q-item-section>Edit Policies</q-item-section>
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
                  autogrow
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
                    <q-btn round dense flat icon="filter_alt" :color="isFilteringTable ? 'green' : 'black'">
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
                :frame="frame"
                :columns="columns"
                :tab="tab"
                :filter="filteredAgents"
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
    <!-- add policy modal -->
    <q-dialog v-model="showPolicyAddModal">
      <PolicyAdd @close="showPolicyAddModal = false" :type="policyAddType" :pk="parseInt(policyAddPk)" />
    </q-dialog>
  </q-layout>
</template>

<script>
import axios from "axios";
import { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";
import { mapState, mapGetters } from "vuex";
import FileBar from "@/components/FileBar";
import AgentTable from "@/components/AgentTable";
import SubTableTabs from "@/components/SubTableTabs";
import AlertsIcon from "@/components/AlertsIcon";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import ClientsForm from "@/components/modals/clients/ClientsForm";
import SitesForm from "@/components/modals/clients/SitesForm";

export default {
  components: {
    FileBar,
    AgentTable,
    SubTableTabs,
    AlertsIcon,
    PolicyAdd,
    ClientsForm,
    SitesForm,
  },
  data() {
    return {
      showClientsFormModal: false,
      showSitesFormModal: false,
      showPolicyAddModal: false,
      deleteEditModalPk: null,
      clientOp: null,
      policyAddType: null,
      policyAddPk: null,
      serverCount: 0,
      serverOfflineCount: 0,
      workstationCount: 0,
      workstationOfflineCount: 0,
      outsideModel: 11,
      selectedTree: "",
      innerModel: 50,
      tab: "server",
      clientActive: "",
      siteActive: "",
      frame: [],
      poll: null,
      search: "",
      filterTextLength: 0,
      filterAvailability: "all",
      filterPatchesPending: false,
      filterChecksFailing: false,
      filterRebootNeeded: false,
      currentTRMMVersion: null,
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
          field: "logged_in_username",
          sortable: true,
          align: "left",
        },
        {
          name: "lastuser",
          label: "Last User",
          field: "last_logged_in_user",
          sortable: true,
          align: "left",
        },
        {
          name: "patchespending",
          field: "patches_pending",
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
          name: "needsreboot",
          field: "needs_reboot",
          align: "left",
          sortable: true,
        },
        {
          name: "lastseen",
          label: "Last Response",
          field: "last_seen",
          sortable: true,
          align: "left",
        },
        {
          name: "boottime",
          label: "Boot Time",
          field: "boot_time",
          sortable: true,
          align: "left",
        },
      ],
      visibleColumns: [
        "smsalert",
        "emailalert",
        "checks-status",
        "client_name",
        "site_name",
        "hostname",
        "description",
        "user",
        "patchespending",
        "agentstatus",
        "needsreboot",
        "lastseen",
        "boottime",
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
    refreshEntireSite() {
      this.$store.dispatch("loadTree");
      this.getDashInfo();
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

      let url, urlType, id;
      if (typeof activenode === "string") {
        urlType = activenode.split("|")[0];
        id = activenode.split("|")[1];

        if (urlType === "Client") {
          url = `/agents/byclient/${id}/`;
        } else if (urlType === "Site") {
          url = `/agents/bysite/${id}/`;
        }

        if (url) {
          this.$store.commit("AGENT_TABLE_LOADING", true);
          axios.get(url).then(r => {
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
      axios.get("/agents/listagents/").then(r => {
        this.frame = r.data;
        //this.siteActive = "";
        //this.$store.commit("destroySubTable");
        this.$store.commit("AGENT_TABLE_LOADING", false);
      });
    },
    showPolicyAdd(node) {
      if (node.children) {
        this.policyAddType = "client";
        this.policyAddPk = node.id;
        this.showPolicyAddModal = true;
      } else {
        this.policyAddType = "site";
        this.policyAddPk = node.id;
        this.showPolicyAddModal = true;
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
    reload() {
      this.$store.dispatch("reload");
    },
    livePoll() {
      this.poll = setInterval(() => {
        this.$store.dispatch("checkVer");
        this.getAgentCounts();
        this.getDashInfo();
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
    getDashInfo() {
      this.$store.dispatch("getDashInfo").then(r => (this.currentTRMMVersion = r.data.trmm_version));
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
      this.filterPatchesPending = false;
      this.filterRebootNeeded = false;
      this.filterChecksFailing = false;
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
    allClientsActive() {
      return this.selectedTree === "" ? true : false;
    },
    filteredAgents() {
      if (this.tab === "mixed") {
        return Object.freeze(this.frame);
      }
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
    this.getTree();
    this.$store.dispatch("getUpdatedSites");
    this.$store.dispatch("checkVer");
    this.getDashInfo();
    this.getAgentCounts();
  },
  mounted() {
    this.loadFrame(this.activeNode);
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