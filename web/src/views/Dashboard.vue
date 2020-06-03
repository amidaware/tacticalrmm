<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-grey-9 text-white">
      <q-toolbar>
        <q-btn dense flat push @click="refreshEntireSite" icon="refresh" />
        <q-toolbar-title>Tactical RMM</q-toolbar-title>

        <AlertsIcon />

        <q-btn-dropdown flat no-caps stretch :label="user">
          <q-list>
            <q-item to="/logout" exact>
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
          <div class="q-pa-sm q-gutter-sm" v-if="treeReady">
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
                        <q-item 
                          clickable 
                          v-close-popup 
                          @click="showEditModal(props.node)"
                        >
                          <q-item-section side>
                            <q-icon name="edit" />
                          </q-item-section>
                          <q-item-section>Edit</q-item-section>
                        </q-item>
                        <!--<q-item
                          clickable
                          v-close-popup
                          @click="showDelete(props.node)"
                        >
                          <q-item-section side>
                            <q-icon name="delete" />
                          </q-item-section>
                          <q-item-section>Delete</q-item-section>
                        </q-item>-->

                        <q-separator></q-separator>

                        <q-item 
                          clickable 
                          v-close-popup 
                          @click="showPolicyAdd(props.node)"
                        >
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
          <div v-else>
            <p>Loading</p>
          </div>
        </template>
        <template v-slot:after>
          <q-splitter v-model="innerModel" horizontal style="height: 88vh">
            <template v-slot:before>
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
              <AgentTable
                :frame="frame"
                :columns="columns"
                :tab="tab"
                :filter="filteredAgents"
                :userName="user"
                @refreshEdit="getTree"
              />
            </template>
            <template v-slot:after>
              <SubTableTabs />
            </template>
          </q-splitter>
        </template>
      </q-splitter>
    </q-page-container>

    <!-- edit client modal -->
    <q-dialog v-model="showEditClientModal">
      <EditClients @close="showEditClientModal = false" />
    </q-dialog>
    <!-- edit site modal -->
    <q-dialog v-model="showEditSiteModal">
      <EditSites @close="showEditSiteModal = false" />
    </q-dialog>
    <!-- add policy modal -->
    <q-dialog v-model="showPolicyAddModal">
      <PolicyAdd 
        @close="showPolicyAddModal = false"
        :type="policyAddType"
        :pk="parseInt(policyAddPk)"
      />
    </q-dialog>
  </q-layout>
</template>

<script>
import axios from "axios";
import { mapState, mapGetters } from "vuex";
import FileBar from "@/components/FileBar";
import AgentTable from "@/components/AgentTable";
import SubTableTabs from "@/components/SubTableTabs";
import AlertsIcon from "@/components/AlertsIcon";
import PolicyAdd from "@/components/automation/modals/PolicyAdd"
import EditSites from "@/components/modals/clients/EditSites"
import EditClients from "@/components/modals/clients/EditClients"

export default {
  components: {
    FileBar,
    AgentTable,
    SubTableTabs,
    AlertsIcon,
    PolicyAdd,
    EditSites,
    EditClients
  },
  data() {
    return {
      showEditClientModal: false,
      showEditSiteModal: false,
      showPolicyAddModal: false,
      policyAddType: null,
      policyAddPk: null,
      outsideModel: 11,
      selectedTree: "",
      innerModel: 55,
      tab: "server",
      left: true,
      clientActive: "",
      siteActive: "",
      frame: [],
      columns: [
        {
          name: "smsalert",
          align: "left"
        },
        {
          name: "emailalert",
          align: "left"
        },
        {
          name: "checks-status",
          align: "left"
        },
        {
          name: "client",
          label: "Client",
          field: "client",
          sortable: true,
          align: "left"
        },
        {
          name: "site",
          label: "Site",
          field: "site",
          sortable: true,
          align: "left"
        },
        {
          name: "hostname",
          label: "Hostname",
          field: "hostname",
          sortable: true,
          align: "left"
        },
        {
          name: "description",
          label: "Description",
          field: "description",
          sortable: true,
          align: "left"
        },
        {
          name: "patchespending",
          align: "left"
        },
        /* {
          name: "antivirus",
          align: "left"
        }, */
        {
          name: "agentstatus",
          field: "status",
          align: "left"
        },
        {
          name: "lastseen",
          label: "Last Response",
          field: "last_seen",
          sortable: true,
          align: "left"
        },
        {
          name: "boottime",
          label: "Boot Time",
          field: "boot_time",
          sortable: true,
          align: "left"
        }
      ]
    };
  },
  methods: {
    refreshEntireSite() {
      this.$store.dispatch("loadTree");

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
      }
    },
    loadFrame(activenode, destroySub = true) {
      if (destroySub) this.$store.commit("destroySubTable");

      let client, site, url;
      try {
        client = this.$refs.tree.meta[activenode].parent.key.split("|")[1];
        site = activenode.split("|")[1];
        url = `/agents/bysite/${client}/${site}/`;
      } catch (e) {
        try {
          client = activenode.split("|")[1];
        } catch (e) {
          return false;
        }
        if (client === null || client === undefined) {
          url = null;
        } else {
          url = `/agents/byclient/${client}/`;
        }
      }
      if (url) {
        this.$store.commit("AGENT_TABLE_LOADING", true);
        axios.get(url).then(r => {
          this.frame = r.data;
          this.$store.commit("AGENT_TABLE_LOADING", false);
        });
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
    showEditModal(node) {
      if (node.children) {
        this.showEditClientModal = true;
      } else {
        this.showEditSiteModal = true;
      }
    }
  },
  computed: {
    ...mapState({
      user: state => state.username,
      clientsTree: state => state.tree,
      treeReady: state => state.treeReady,
      clients: state => state.clients
    }),
    ...mapGetters(["selectedAgentPk"]),
    allClientsActive() {
      return this.selectedTree === "" ? true : false;
    },
    filteredAgents() {
      if (this.tab === "mixed") {
        return this.frame;
      }
      return this.frame.filter(k => k.monitoring_type === this.tab);
    },
    activeNode() {
      return {
        client: this.clientActive,
        site: this.siteActive
      };
    }
  },
  created() {
    this.getTree();
    this.$store.dispatch("getUpdatedSites");
  },
  mounted() {
    if (localStorage.getItem("reloaded")) {
      localStorage.removeItem("reloaded");
    }
    this.loadFrame(this.activeNode);
  }
};
</script>

<style>
.my-menu-link {
  color: white;
  background: lightgray;
}
</style>