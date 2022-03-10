<template>
  <q-page>
    <FileBar />
    <q-splitter v-model="clientTreeSplitter" :style="{ height: `${$q.screen.height - 50 - 40}px` }">
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
              @update:selected="$store.dispatch('refreshDashboard')"
            >
              <template v-slot:default-header="props">
                <div class="row items-center">
                  <q-icon :name="props.node.icon" :color="props.node.color" class="q-mr-sm" />
                  <div>
                    {{ props.node.label }}
                    <q-tooltip :delay="600">
                      ID: {{ props.node.id }}<br />
                      Agent Count:
                      {{ props.node.children ? props.node.client.agent_count : props.node.site.agent_count }}
                    </q-tooltip>
                  </div>

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

                      <q-item v-if="props.node.children" clickable v-close-popup @click="showAddSiteModal(props.node)">
                        <q-item-section side>
                          <q-icon name="add" />
                        </q-item-section>
                        <q-item-section>Add Site</q-item-section>
                      </q-item>

                      <q-item clickable v-close-popup @click="showToggleMaintenance(props.node)">
                        <q-item-section side>
                          <q-icon name="construction" />
                        </q-item-section>
                        <q-item-section>{{
                          props.node.color === "green" ? "Disable Maintenance Mode" : "Enable Maintenance Mode"
                        }}</q-item-section>
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

                      <q-item clickable v-ripple @click="getURLActions">
                        <q-item-section side>
                          <q-icon name="open_in_new" />
                        </q-item-section>
                        <q-item-section>Run URL Action</q-item-section>
                        <q-item-section side>
                          <q-icon name="keyboard_arrow_right" />
                        </q-item-section>
                        <q-menu auto-close anchor="top end" self="top start">
                          <q-list>
                            <q-item
                              v-for="action in urlActions"
                              :key="action.id"
                              dense
                              clickable
                              v-close-popup
                              @click="runURLAction(props.node.id, action.id, props.node.children ? 'client' : 'site')"
                            >
                              {{ action.name }}
                            </q-item>
                          </q-list>
                        </q-menu>
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
          unit="px"
          horizontal
          @update:model-value="$store.commit('SET_SPLITTER', innerModel)"
          after-class="hide-scrollbar"
          before-class="hide-scrollbar"
          emit-immediately
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
                            <q-radio val="overdue" v-model="filterAvailability" />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>Show Overdue Only</q-item-label>
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
            <AgentTable :agents="filteredAgents" :columns="columns" :search="search" :visibleColumns="visibleColumns" />
          </template>
          <template v-slot:separator>
            <q-avatar color="primary" text-color="white" size="20px" icon="drag_indicator" />
          </template>
          <template v-slot:after>
            <SubTableTabs />
          </template>
        </q-splitter>
      </template>
    </q-splitter>

    <!-- install agent modal -->
    <q-dialog v-model="showInstallAgentModal" @hide="closeInstallAgent">
      <InstallAgent @close="closeInstallAgent" :sitepk="parseInt(sitePk)" />
    </q-dialog>
  </q-page>
</template>

<script>
import mixins from "@/mixins/mixins";
import { openURL } from "quasar";
import { mapState } from "vuex";
import FileBar from "@/components/FileBar";
import AgentTable from "@/components/AgentTable";
import SubTableTabs from "@/components/SubTableTabs";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import ClientsForm from "@/components/clients/ClientsForm";
import SitesForm from "@/components/clients/SitesForm";
import DeleteClient from "@/components/clients/DeleteClient";
import InstallAgent from "@/components/modals/agents/InstallAgent";
import AlertTemplateAdd from "@/components/modals/alerts/AlertTemplateAdd";

import { removeClient, removeSite } from "@/api/clients";

export default {
  name: "Dashboard",
  components: {
    FileBar,
    AgentTable,
    SubTableTabs,
    InstallAgent,
  },
  // allow child components to refresh table
  provide() {
    return {
      refreshDashboard: (clearTreeSelected, clearSubTable) => {
        if (clearSubTable) this.$store.commit("destroySubTable");

        this.$store.dispatch("refreshDashboard", clearTreeSelected);
      },
    };
  },
  mixins: [mixins],
  data() {
    return {
      showInstallAgentModal: false,
      sitePk: null,
      innerModel: (this.$q.screen.height - 82) / 2,
      search: "",
      filterTextLength: 0,
      filterAvailability: "all",
      filterPatchesPending: false,
      filterActionsPending: false,
      filterChecksFailing: false,
      filterRebootNeeded: false,
      urlActions: [],
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
          name: "plat",
          label: "",
          field: "plat",
          sortable: true,
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
        "plat",
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
    selectedTree(newVal, oldVal) {
      if (this.clearSearchWhenSwitching) this.clearFilter();
    },
  },
  methods: {
    getTree() {
      this.$store.dispatch("loadAgents");
      this.$store.dispatch("loadTree");
    },
    clearTreeSelected() {
      if (this.clearSearchWhenSwitching) this.clearFilter();
      this.$store.dispatch("refreshDashboard", true);
    },
    showPolicyAdd(node) {
      this.$q
        .dialog({
          component: PolicyAdd,
          componentProps: {
            type: node.children ? "client" : "site",
            object: node.children ? node.client : node.site,
          },
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showAddSiteModal(node) {
      this.$q
        .dialog({
          component: SitesForm,
          componentProps: {
            client: node.id,
          },
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showEditModal(node) {
      let props = {};
      if (node.children) {
        props.client = { id: node.id, name: node.label };
      } else {
        props.site = { id: node.id, name: node.label, client: node.client };
      }

      this.$q
        .dialog({
          component: node.children ? ClientsForm : SitesForm,
          componentProps: node.children ? { client: node.client } : { site: node.site },
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showDeleteModal(node) {
      if ((node.children && node.client.agent_count > 0) || (!node.children && node.site.agent_count > 0)) {
        this.$q
          .dialog({
            component: DeleteClient,
            componentProps: {
              object: node.children ? node.client : node.site,
              type: node.children ? "client" : "site",
            },
          })
          .onOk(this.clearTreeSelected);
      } else {
        this.$q
          .dialog({
            title: "Are you sure?",
            message: `Delete site: ${node.label}.`,
            cancel: true,
            ok: { label: "Delete", color: "negative" },
          })
          .onOk(async () => {
            this.$q.loading.show();
            try {
              const result = node.children ? await removeClient(node.id) : await removeSite(node.id);
              this.notifySuccess(result);
              this.clearTreeSelected();
            } catch (e) {
              console.error(e);
            }
            this.$q.loading.hide();
          });
      }
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
            object: node.children ? node.client : node.site,
          },
        })
        .onOk(() => this.$store.dispatch("refreshDashboard"));
    },
    showToggleMaintenance(node) {
      let data = {
        id: node.id,
        type: node.raw.split("|")[0],
        action: node.color === "green" ? false : true,
      };

      this.$axios
        .post("/agents/maintenance/bulk/", data)
        .then(r => {
          this.notifySuccess(r.data);
          this.$store.dispatch("refreshDashboard");
          this.$store.commit("setRefreshSummaryTab", true);
        })
        .catch(e => {
          console.error(e);
        });
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
        (this.search.includes("is:online") ||
          this.search.includes("is:offline") ||
          this.search.includes("is:expired") ||
          this.search.includes("is:overdue"))
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
        } else if (this.filterAvailability === "overdue") {
          filterText += "is:overdue ";
        }
      }

      this.search = filterText;
      this.filterTextLength = filterText.length - 1;
    },
    getURLActions() {
      this.$axios
        .get("/core/urlaction/")
        .then(r => {
          if (r.data.length === 0) {
            this.notifyWarning("No URL Actions configured. Go to Settings > Global Settings > URL Actions");
            return;
          }
          this.urlActions = r.data;
        })
        .catch(() => {});
    },
    runURLAction(id, action, model) {
      const data = {
        [model]: id,
        action: action,
      };
      this.$axios
        .patch("/core/urlaction/run/", data)
        .then(r => {
          openURL(r.data);
        })
        .catch(() => {});
    },
  },
  computed: {
    ...mapState({
      clientsTree: state => state.tree,
      treeReady: state => state.treeReady,
      clearSearchWhenSwitching: state => state.clearSearchWhenSwitching,
      agents: state => state.agents,
    }),
    clientTreeSplitter: {
      get() {
        return this.$store.state.clientTreeSplitter;
      },
      set(newVal) {
        this.$store.dispatch("setClientTreeSplitter", newVal);
      },
    },
    tab: {
      get() {
        return this.$store.state.defaultAgentTblTab;
      },
      set(newVal) {
        this.$store.commit("SET_DEFAULT_AGENT_TBL_TAB", newVal);
        this.$store.commit("destroySubTable");
      },
    },
    selectedTree: {
      get() {
        return this.$store.state.selectedTree;
      },
      set(newVal) {
        this.$store.commit("setSelectedTree", newVal);
        this.$store.commit("destroySubTable");
      },
    },
    allClientsActive() {
      return this.selectedTree === "";
    },
    filteredAgents() {
      if (this.tab === "mixed") return this.agents;
      else return this.agents.filter(k => k.monitoring_type === this.tab);
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
  },
  mounted() {
    this.getTree();

    // set initial value for agent table and agent tabs
    this.$store.commit("SET_SPLITTER", this.innerModel);
  },
};
</script>

<style>
.my-menu-link {
  color: white;
  background: lightgray;
}
</style>