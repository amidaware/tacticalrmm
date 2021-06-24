<template>
  <q-dialog ref="dialog" @hide="onHide">
    <div class="q-dialog-plugin" style="width: 90vw; max-width: 90vw">
      <q-card>
        <q-bar>
          <q-btn @click="getClients" class="q-mr-sm" dense flat push icon="refresh" />Clients Manager
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-sm" style="min-height: 65vh; max-height: 65vh">
          <div class="q-gutter-sm">
            <q-btn label="New" dense flat push unelevated no-caps icon="add" @click="showAddClient" />
          </div>
          <q-table
            dense
            :rows="clients"
            :columns="columns"
            v-model:pagination="pagination"
            row-key="id"
            binary-state-sort
            hide-pagination
            virtual-scroll
            :rows-per-page-options="[0]"
            no-data-label="No Clients"
            :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
            class="settings-tbl-sticky"
          >
            <!-- body slots -->
            <template v-slot:body="props">
              <q-tr :props="props" class="cursor-pointer" @dblclick="showEditClient(props.row)">
                <!-- context menu -->
                <q-menu context-menu>
                  <q-list dense style="min-width: 200px">
                    <q-item clickable v-close-popup @click="showEditClient(props.row)">
                      <q-item-section side>
                        <q-icon name="edit" />
                      </q-item-section>
                      <q-item-section>Edit</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="showClientDeleteModal(props.row)">
                      <q-item-section side>
                        <q-icon name="delete" />
                      </q-item-section>
                      <q-item-section>Delete</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup @click="showAddSite(props.row)">
                      <q-item-section side>
                        <q-icon name="add" />
                      </q-item-section>
                      <q-item-section>Add Site</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup>
                      <q-item-section>Close</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
                <!-- name -->
                <q-td>
                  {{ props.row.name }}
                </q-td>
                <q-td>
                  <span
                    style="cursor: pointer; text-decoration: underline"
                    class="text-primary"
                    @click="showSitesTable(props.row)"
                    >Show Sites</span
                  >
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
      </q-card>
    </div>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import ClientsForm from "@/components/modals/clients/ClientsForm";
import SitesForm from "@/components/modals/clients/SitesForm";
import DeleteClient from "@/components/modals/clients/DeleteClient";
import SitesTable from "@/components/modals/clients/SitesTable";

export default {
  name: "ClientsManager",
  emits: ["hide", "ok", "cancel"],
  mixins: [mixins],
  data() {
    return {
      clients: [],
      columns: [
        { name: "name", label: "Name", field: "name", align: "left" },
        { name: "sites", label: "Sites", field: "sites", align: "left" },
      ],
      pagination: {
        rowsPerPage: 0,
        sortBy: "name",
        descending: false,
      },
    };
  },
  methods: {
    getClients() {
      this.$q.loading.show();
      this.$axios
        .get("clients/clients/")
        .then(r => {
          this.clients = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    showClientDeleteModal(client) {
      this.$q
        .dialog({
          component: DeleteClient,
          componentProps: {
            object: client,
            type: "client",
          },
        })
        .onOk(() => {
          this.getClients();
        });
    },
    showEditClient(client) {
      this.$q
        .dialog({
          component: ClientsForm,
          componentProps: {
            client: client,
          },
        })
        .onOk(() => {
          this.getClients();
        });
    },
    showAddClient() {
      this.$q
        .dialog({
          component: ClientsForm,
        })
        .onOk(() => {
          this.getClients();
        });
    },
    showAddSite(client) {
      this.$q
        .dialog({
          component: SitesForm,
          componentProps: {
            client: client.id,
          },
        })
        .onOk(() => {
          this.getClients();
        });
    },
    showSitesTable(client) {
      this.$q.dialog({
        component: SitesTable,
        componentProps: {
          client: client,
        },
      });
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
  },
  mounted() {
    this.getClients();
  },
};
</script>