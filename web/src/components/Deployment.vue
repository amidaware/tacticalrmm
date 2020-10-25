<template>
  <q-card style="min-width: 70vw">
    <q-bar>
      <q-btn @click="getDeployments" class="q-mr-sm" dense flat push icon="refresh" />
      <q-space />Manage Deployments
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary" />
      </q-btn>
    </q-bar>
    <div class="row">
      <div class="q-pa-sm q-ml-sm">
        <q-btn color="primary" icon="add" label="New" @click="showNewDeployment = true" />
      </div>
    </div>
    <q-separator />
    <q-card-section>
      <q-table
        dense
        class="audit-mgr-tbl-sticky"
        binary-state-sort
        virtual-scroll
        :data="deployments"
        :columns="columns"
        :visible-columns="visibleColumns"
        row-key="id"
        :pagination.sync="pagination"
        no-data-label="No Deployments"
      >
        <template slot="body" slot-scope="props" :props="props">
          <q-tr>
            <q-td key="client" :props="props">{{ props.row.client_name }}</q-td>
            <q-td key="site" :props="props">{{ props.row.site_name }}</q-td>
            <q-td key="mon_type" :props="props">{{ props.row.mon_type }}</q-td>
            <q-td key="arch" :props="props"
              ><span v-if="props.row.arch === '64'">64 bit</span><span v-else>32 bit</span></q-td
            >
            <q-td key="expiry" :props="props">{{ props.row.expiry }}</q-td>
            <q-td key="flags" :props="props"
              ><q-badge color="grey-8" label="View Flags" />
              <q-tooltip content-style="font-size: 12px">{{ props.row.install_flags }}</q-tooltip>
            </q-td>
            <q-td key="link" :props="props"
              ><q-btn size="sm" color="primary" icon="content_copy" label="Copy" @click="copyLink(props)"
            /></q-td>
            <q-td key="delete" :props="props"
              ><q-btn size="sm" color="negative" icon="delete" @click="deleteDeployment(props.row.id)"
            /></q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card-section>
    <q-dialog v-model="showNewDeployment">
      <NewDeployment @close="showNewDeployment = false" @added="getDeployments" />
    </q-dialog>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import NewDeployment from "@/components/modals/clients/NewDeployment";
import { copyToClipboard } from "quasar";

export default {
  name: "Deployment",
  mixins: [mixins],
  components: { NewDeployment },
  data() {
    return {
      showNewDeployment: false,
      deployments: [],
      columns: [
        { name: "id", field: "id" },
        { name: "uid", field: "uid" },
        { name: "clientid", field: "client_id" },
        { name: "siteid", field: "site_id" },
        { name: "client", label: "Client", field: "client_name", align: "left", sortable: true },
        { name: "site", label: "Site", field: "site_name", align: "left", sortable: true },
        { name: "mon_type", label: "Type", field: "mon_type", align: "left", sortable: true },
        { name: "arch", label: "Arch", field: "arch", align: "left", sortable: true },
        { name: "expiry", label: "Expiry", field: "expiry", align: "left", sortable: true },
        { name: "flags", label: "Flags", field: "install_flags", align: "left" },
        { name: "link", label: "Download Link", align: "left" },
        { name: "delete", label: "Delete", align: "left" },
      ],
      visibleColumns: ["client", "site", "mon_type", "arch", "expiry", "flags", "link", "delete"],

      pagination: {
        rowsPerPage: 50,
        sortBy: "id",
        descending: true,
      },
    };
  },
  methods: {
    getDeployments() {
      this.$axios.get("/clients/deployments/").then(r => {
        this.deployments = r.data;
      });
    },
    deleteDeployment(pk) {
      this.$q
        .dialog({
          title: "Delete deployment?",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$axios
            .delete(`/clients/${pk}/deployment/`)
            .then(r => {
              this.getDeployments();
              this.notifySuccess("Deployment deleted");
            })
            .catch(() => this.notifyError("Something went wrong"));
        });
    },
    copyLink(props) {
      const api = axios.defaults.baseURL;
      copyToClipboard(`${api}/clients/${props.row.uid}/deploy/`).then(() => {
        this.notifySuccess("Link copied to clipboard", 1500);
      });
    },
  },
  created() {
    this.getDeployments();
  },
};
</script>