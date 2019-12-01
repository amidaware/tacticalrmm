<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-grey-9 text-white">
      <q-toolbar>
        <q-toolbar-title>
          <q-avatar>
            <img src="https://cdn.quasar.dev/logo/svg/quasar-logo.svg" />
          </q-avatar>Django RMM
        </q-toolbar-title>
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

    <q-drawer v-model="left" side="left" :width="250" elevated>
      <div class="q-pa-sm q-gutter-sm" v-if="treeReady">
        <q-list dense class="rounded-borders">
          <q-item
            clickable
            v-ripple
            :active="allClientsActive"
            @click="clearTreeSelected"
          >
            <q-item-section avatar>
              <q-icon name="fas fa-home" />
            </q-item-section>
            <q-item-section>All Clients</q-item-section>
            <q-item-section avatar>
              <q-icon name="refresh" color="black" />
            </q-item-section>
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
        </q-tree>
        </q-list>   
      </div>
      <div v-else>
        <p>Loading</p>
      </div>
      
    </q-drawer>

    <q-page-container>
      <FileBar :clients="clients"></FileBar>
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
      <q-splitter v-model="splitterModel" horizontal style="height: 80vh">
        <template v-slot:before>
          <AgentTable :frame="frame" :columns="columns" :tab="tab" :filter="filteredAgents" :userName="user" @refreshEdit="getTree" />
        </template>
        <template v-slot:separator>
          <q-avatar color="primary" text-color="white" size="20px" icon="drag_indicator" />
        </template>
        <template v-slot:after>
          <SubTableTabs />
        </template>
      </q-splitter>
    </q-page-container>
  </q-layout>
</template>

<script>
import axios from "axios";
import { mapState } from 'vuex';
import FileBar from "@/components/FileBar";
import AgentTable from "@/components/AgentTable";
import SubTableTabs from "@/components/SubTableTabs";
export default {
  components: {
    FileBar,
    AgentTable,
    SubTableTabs
  },
  data() {
    return {
      selectedTree: '',
      splitterModel: 50,
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
          name: "platform", 
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
        {
          name: "antivirus",
          align: "left"
        },
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
    loadFrame(activenode) {
      this.$store.commit("destroySubTable");
      let client, site, url;
      try {
        client = this.$refs.tree.meta[activenode].parent.key.split('|')[0];
        site = activenode.split('|')[0];
        url = `/agents/bysite/${client}/${site}/`;
      }
      catch(e) {
        try {
          client = activenode.split('|')[0];
        }
        catch(e) {
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
        })
      }
    },
    getTree() {
      this.loadAllClients();
      this.$store.dispatch("loadTree");
    },
    clearTreeSelected() {
      this.selectedTree = '';
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
        this.siteActive = "";
        this.$store.commit("destroySubTable");
        this.$store.commit("AGENT_TABLE_LOADING", false);
      });
    },
  },
  computed: {
    ...mapState({
      user: state => state.username,
      clientsTree: state => state.tree,
      treeReady: state => state.treeReady,
      clients: state => state.clients
    }),
    allClientsActive() {
      return (this.selectedTree === '') ? true : false
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