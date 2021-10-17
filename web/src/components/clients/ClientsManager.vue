<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 70vw">
      <q-bar>
        <q-btn @click="getClients" class="q-mr-sm" dense flat push icon="refresh" />Clients Manager
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-table
        :rows="clients"
        :columns="columns"
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="settings-tbl-sticky"
        style="height: 70vh"
        :pagination="{ rowsPerPage: 0, sortBy: 'name', descending: false }"
        dense
        row-key="id"
        binary-state-sort
        virtual-scroll
        :rows-per-page-options="[0]"
        no-data-label="No Clients"
        :loading="loading"
      >
        <!-- top slot -->
        <template v-slot:top>
          <q-btn label="New" dense flat push no-caps icon="add" @click="showAddClient" />
        </template>

        <!-- loading slot -->
        <template v-slot:loading>
          <q-inner-loading showing color="primary" />
        </template>

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
                >Show Sites ({{ props.row.sites.length }})</span
              >
            </q-td>
            <q-td>{{ props.row.agent_count }}</q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, onMounted } from "vue";
import { useStore } from "vuex";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { fetchClients, removeClient } from "@/api/clients";
import { notifySuccess } from "@/utils/notify";

// ui imports
import ClientsForm from "@/components/clients/ClientsForm";
import SitesForm from "@/components/clients/SitesForm";
import DeleteClient from "@/components/clients/DeleteClient";
import SitesTable from "@/components/clients/SitesTable";

// static data
const columns = [
  { name: "name", label: "Name", field: "name", align: "left" },
  { name: "sites", label: "Sites", field: "sites", align: "left" },
  { name: "agent_count", label: "Total Agents", field: "agent_count", align: "left" },
];

export default {
  name: "ClientsManager",
  emits: [...useDialogPluginComponent.emits],
  setup(props) {
    // setup vuex
    const store = useStore();

    // setup quasar dialog
    const $q = useQuasar();
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    // clients manager logic
    const clients = ref([]);
    const loading = ref(false);

    async function getClients() {
      loading.value = true;
      clients.value = await fetchClients();
      loading.value = false;
    }

    function showClientDeleteModal(client) {
      // agents are still assigned to client. Need to open modal to select which site to move to
      if (client.agent_count > 0) {
        $q.dialog({
          component: DeleteClient,
          componentProps: {
            object: client,
            type: "client",
          },
        }).onOk(getClients);

        // can delete the client since there are no agents
      } else {
        $q.dialog({
          title: "Are you sure?",
          message: `Delete client: ${client.name}.`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        }).onOk(async () => {
          loading.value = true;
          try {
            const result = await removeClient(client.id);
            notifySuccess(result);
            await getClients();
            store.dispatch("loadTree");
          } catch (e) {
            console.error(e);
          }
          loading.value = false;
        });
      }
    }

    function showEditClient(client) {
      $q.dialog({
        component: ClientsForm,
        componentProps: {
          client: client,
        },
      }).onOk(getClients);
    }

    function showAddClient() {
      $q.dialog({
        component: ClientsForm,
      }).onOk(getClients);
    }

    function showAddSite(client) {
      $q.dialog({
        component: SitesForm,
        componentProps: {
          client: client.id,
        },
      }).onOk(getClients);
    }

    function showSitesTable(client) {
      $q.dialog({
        component: SitesTable,
        componentProps: {
          client: client,
        },
      });
    }

    onMounted(getClients);

    return {
      // reactive data
      clients,
      loading,

      // non-reactive data
      columns,

      // methods
      getClients,
      showClientDeleteModal,
      showEditClient,
      showAddClient,
      showAddSite,
      showSitesTable,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>