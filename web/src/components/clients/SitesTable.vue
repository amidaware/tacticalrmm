<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        <q-btn @click="getSites" class="q-mr-sm" dense flat push icon="refresh" />Sites for {{ client.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-table
        dense
        :rows="sites"
        :columns="columns"
        :pagination="{ rowsPerPage: 0, sortBy: 'name', descending: true }"
        row-key="id"
        binary-state-sort
        virtual-scroll
        :rows-per-page-options="[0]"
        no-data-label="No Sites"
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="settings-tbl-sticky"
        style="height: 65vh"
        :loading="loading"
      >
        <template v-slot:top>
          <q-btn label="New" dense flat push unelevated no-caps icon="add" @click="showAddSite" />
        </template>

        <!-- loading slot -->
        <template v-slot:loading>
          <q-inner-loading showing color="primary" />
        </template>

        <!-- body slots -->
        <template v-slot:body="props">
          <q-tr :props="props" class="cursor-pointer" @dblclick="showEditSite(props.row)">
            <!-- context menu -->
            <q-menu context-menu>
              <q-list dense style="min-width: 200px">
                <q-item clickable v-close-popup @click="showEditSite(props.row)">
                  <q-item-section side>
                    <q-icon name="edit" />
                  </q-item-section>
                  <q-item-section>Edit</q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="showSiteDeleteModal(props.row)">
                  <q-item-section side>
                    <q-icon name="delete" />
                  </q-item-section>
                  <q-item-section>Delete</q-item-section>
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
            <!-- agent count -->
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
import { fetchClient, removeSite } from "@/api/clients";
import { notifySuccess } from "@/utils/notify";

// ui imports
import SitesForm from "@/components/clients/SitesForm";
import DeleteClient from "@/components/clients/DeleteClient";

// static data
const columns = [
  { name: "name", label: "Name", field: "name", align: "left" },
  { name: "agent_count", label: "Total Agents", field: "agent_count", align: "left" },
];

export default {
  name: "SitesTable",
  emits: [...useDialogPluginComponent.emits],
  props: {
    client: !Object,
  },
  setup(props) {
    // setup vuex
    const store = useStore();

    // setup quasar dialog
    const $q = useQuasar();
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    // sites table logic
    const sites = ref([]);
    const loading = ref(false);

    async function getSites() {
      loading.value = true;
      const client = await fetchClient(props.client.id);
      sites.value = client.sites;
      loading.value = false;
    }

    function showSiteDeleteModal(site) {
      // agents are still assigned to client. Need to open modal to select which site to move to
      if (site.agent_count > 0) {
        $q.dialog({
          component: DeleteClient,
          componentProps: {
            object: site,
            type: "site",
          },
        }).onOk(getSites);

        // can delete the client since there are no agents
      } else {
        $q.dialog({
          title: "Are you sure?",
          message: `Delete site: ${site.name}.`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        }).onOk(async () => {
          loading.value = true;
          try {
            const result = await removeSite(site.id);
            notifySuccess(result);
            await getSites();
            store.dispatch("loadTree");
          } catch (e) {
            console.error(e);
          }
          loading.value = false;
        });
      }
    }

    function showEditSite(site) {
      $q.dialog({
        component: SitesForm,
        componentProps: {
          site: site,
        },
      }).onOk(getSites);
    }

    function showAddSite() {
      $q.dialog({
        component: SitesForm,
        componentProps: {
          client: props.client.id,
        },
      }).onOk(getSites);
    }

    onMounted(getSites);

    return {
      // reactive data
      sites,
      loading,

      // non-reactive data
      columns,

      // methods
      getSites,
      showSiteDeleteModal,
      showEditSite,
      showAddSite,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>