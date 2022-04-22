<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="min-width: 70vw; height: 70vh">
      <q-bar>
        <q-btn @click="getDeployments" class="q-mr-sm" dense flat push icon="refresh" />
        Manage Deployments
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary" />
        </q-btn>
      </q-bar>
      <q-table
        dense
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="audit-mgr-tbl-sticky"
        style="max-height: 65vh"
        binary-state-sort
        virtual-scroll
        :rows="deployments"
        :columns="columns"
        :rows-per-page-options="[0]"
        row-key="id"
        :pagination="{ rowsPerPage: 0, sortBy: 'id', descending: true }"
        no-data-label="No Deployments"
        :loading="loading"
      >
        <template v-slot:top>
          <q-btn dense flat icon="add" label="New" @click="showAddDeployment" />
        </template>

        <template v-slot:body="props">
          <q-tr :props="props" class="cursor-pointer" @dblclick="copyLink(props.row)">
            <q-menu context-menu auto-close>
              <q-list dense style="min-width: 200px">
                <q-item clickable @click="deleteDeployment(props.row)">
                  <q-item-section side>
                    <q-icon name="delete" />
                  </q-item-section>
                  <q-item-section>Delete</q-item-section>
                </q-item>
                <q-separator />
                <q-item clickable>
                  <q-item-section>Close</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
            <q-td key="client" :props="props">{{ props.row.client_name }}</q-td>
            <q-td key="site" :props="props">{{ props.row.site_name }}</q-td>
            <q-td key="mon_type" :props="props">{{ props.row.mon_type }}</q-td>
            <q-td key="arch" :props="props"
              ><span v-if="props.row.arch === '64'">64 bit</span><span v-else>32 bit</span></q-td
            >
            <q-td key="expiry" :props="props">{{ formatDate(props.row.expiry) }}</q-td>
            <q-td key="created" :props="props">{{ formatDate(props.row.created) }}</q-td>
            <q-td key="flags" :props="props"
              ><q-badge color="grey-8" label="View Flags" />
              <q-tooltip style="font-size: 12px">{{ props.row.install_flags }}</q-tooltip>
            </q-td>
            <q-td key="link" :props="props">
              <q-btn
                flat
                dense
                size="sm"
                color="primary"
                icon="content_copy"
                label="Copy"
                @click="copyLink(props.row)"
              />
            </q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, computed, onMounted } from "vue";
import { useStore } from "vuex";
import { useQuasar, useDialogPluginComponent, copyToClipboard } from "quasar";
import { fetchDeployments, removeDeployment } from "@/api/clients";
import { notifySuccess } from "@/utils/notify";
import { getBaseUrl } from "@/boot/axios";

// ui imports
import NewDeployment from "@/components/clients/NewDeployment";

// static data
const columns = [
  { name: "client", label: "Client", field: "client_name", align: "left", sortable: true },
  { name: "site", label: "Site", field: "site_name", align: "left", sortable: true },
  { name: "mon_type", label: "Type", field: "mon_type", align: "left", sortable: true },
  { name: "arch", label: "Arch", field: "arch", align: "left", sortable: true },
  { name: "expiry", label: "Expiry", field: "expiry", align: "left", sortable: true },
  { name: "created", label: "Created", field: "created", align: "left", sortable: true },
  { name: "flags", label: "Flags", field: "install_flags", align: "left" },
  { name: "link", label: "Download Link", align: "left" },
];

export default {
  name: "Deployment",
  emits: [...useDialogPluginComponent.emits],
  setup(props) {
    // quasar dialog setup
    const { dialogRef, onDialogHide } = useDialogPluginComponent();
    const $q = useQuasar();

    // setup vuex
    const store = useStore();
    const formatDate = computed(() => store.getters.formatDate);

    // deployment logic
    const deployments = ref([]);
    const loading = ref(false);

    async function getDeployments() {
      loading.value = true;
      deployments.value = await fetchDeployments();
      loading.value = false;
    }

    function deleteDeployment(deployment) {
      $q.dialog({
        title: "Delete deployment?",
        cancel: true,
        ok: { label: "Delete", color: "negative" },
      }).onOk(async () => {
        loading.value = true;
        try {
          const result = await removeDeployment(deployment.id);
          notifySuccess(result);
          await getDeployments();
        } catch (e) {
          console.error(e);
        }
        loading.value = false;
      });
    }

    function copyLink(deployment) {
      const api = getBaseUrl();
      copyToClipboard(`${api}/clients/${deployment.uid}/deploy/`).then(() => {
        notifySuccess("Link copied to clipboard", 1500);
      });
    }

    function showAddDeployment() {
      $q.dialog({
        component: NewDeployment,
      }).onOk(getDeployments);
    }

    onMounted(getDeployments);

    return {
      // reactive data
      deployments,
      loading,

      // non-reactive data
      columns,

      // mehtods
      getDeployments,
      deleteDeployment,
      showAddDeployment,
      copyLink,
      formatDate,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>