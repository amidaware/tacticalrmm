<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else-if="agentPlatform.toLowerCase() !== 'windows'" class="q-pa-sm">
    Only supported for Windows agents at this time
  </div>
  <div v-else>
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="tabs-tbl-sticky"
      :style="{ 'max-height': tabHeight }"
      :rows="updates"
      :columns="columns"
      v-model:pagination="pagination"
      :filter="filter"
      row-key="id"
      binary-state-sort
      virtual-scroll
      :loading="loading"
      :rows-per-page-options="[0]"
      no-data-label="No Windows Updates"
    >
      <template v-slot:top>
        <q-btn dense flat push @click="getUpdates" icon="refresh" class="q-mr-sm" />
        <q-btn label="Run Update Scan" dense flat push no-caps @click="updateScan" class="q-mr-sm" />
        <q-btn label="Install Approved Updates" dense flat push no-caps @click="installUpdates" class="q-mr-sm" />
        <q-space />

        <q-input v-model="filter" outlined label="Search" dense clearable class="q-pr-sm">
          <template v-slot:prepend>
            <q-icon name="search" color="primary" />
          </template>
        </q-input>
        <export-table-btn :data="updates" :columns="columns" />
      </template>

      <template v-slot:loading>
        <q-inner-loading showing color="primary" />
      </template>

      <template v-slot:body="props">
        <q-tr :props="props">
          <q-menu context-menu>
            <q-list dense style="min-width: 100px">
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editWinUpdate(props.row.id, 'inherit')"
              >
                <q-item-section>Inherit</q-item-section>
              </q-item>
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editWinUpdate(props.row.id, 'approve')"
              >
                <q-item-section>Approve</q-item-section>
              </q-item>
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editWinUpdate(props.row.id, 'ignore')"
              >
                <q-item-section>Ignore</q-item-section>
              </q-item>
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editWinUpdate(props.row.id, 'nothing')"
              >
                <q-item-section>Do Nothing</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <!-- policy -->
          <q-td>
            <q-icon v-if="props.row.action === 'nothing'" name="fiber_manual_record" color="grey">
              <q-tooltip>Do Nothing</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action === 'approve'" name="fas fa-check" color="primary">
              <q-tooltip>Approve</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action === 'ignore'" name="fas fa-check" color="negative">
              <q-tooltip>Ignore</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action === 'inherit'" name="fiber_manual_record" color="accent">
              <q-tooltip>Inherit</q-tooltip>
            </q-icon>
          </q-td>
          <q-td>
            <q-icon v-if="props.row.installed" name="fas fa-check" color="positive">
              <q-tooltip>Installed</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action == 'approve'" name="fas fa-tasks" color="primary">
              <q-tooltip>Pending</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action == 'ignore'" name="fas fa-ban" color="negative">
              <q-tooltip>Ignored</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-exclamation" color="warning">
              <q-tooltip>Missing</q-tooltip>
            </q-icon>
          </q-td>
          <q-td>{{ !props.row.severity ? "Other" : props.row.severity }}</q-td>
          <q-td>{{ truncateText(props.row.title, 50) }}</q-td>
          <q-td @click="showUpdateDetails(props.row)">
            <span style="cursor: pointer; text-decoration: underline" class="text-primary">{{
              truncateText(props.row.description, 50)
            }}</span>
          </q-td>
          <q-td>{{ formatDate(props.row.date_installed) }}</q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, inject, onMounted } from "vue";
import { useStore } from "vuex";
import { useQuasar } from "quasar";
import { fetchAgentUpdates, editAgentUpdate, runAgentUpdateScan, runAgentUpdateInstall } from "@/api/winupdates";
import { notifySuccess } from "@/utils/notify";
import { truncateText } from "@/utils/format";

// ui imports
import ExportTableBtn from "@/components/ui/ExportTableBtn";

// static data
const columns = [
  {
    name: "action",
    field: "action",
    align: "left",
  },
  {
    name: "installed",
    field: "installed",
    align: "left",
  },
  {
    name: "severity",
    label: "Severity",
    field: "severity",
    align: "left",
    sortable: true,
  },
  {
    name: "title",
    label: "Name",
    field: "title",
    align: "left",
    sortable: true,
  },
  {
    name: "description",
    label: "More Info",
    field: "description",
    align: "left",
    sortable: true,
  },
  {
    name: "date_installed",
    label: "Installed On",
    field: "date_installed",
    align: "left",
    sortable: true,
  },
];

export default {
  name: "WindowsUpdates",
  components: { ExportTableBtn },
  setup(props) {
    // setup vuex
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const tabHeight = computed(() => store.state.tabHeight);
    const agentPlatform = computed(() => store.state.agentPlatform);
    const formatDate = computed(() => store.getters.formatDate);

    // setup quasar
    const $q = useQuasar();

    // inject function to refresh dashboard
    const refreshDashboard = inject("refreshDashboard");

    // setup win update tab component
    const updates = ref([]);
    const filter = ref("");
    const pagination = ref({
      rowsPerPage: 0,
      sortBy: "installed",
      descending: false,
    });
    const loading = ref(false);

    async function getUpdates() {
      loading.value = true;
      updates.value = await fetchAgentUpdates(selectedAgent.value);
      loading.value = false;
    }

    async function editWinUpdate(pk, action) {
      loading.value = true;
      try {
        const result = await editAgentUpdate(pk, { action: action });
        await getUpdates(selectedAgent.value);
        notifySuccess(result);
        refreshDashboard();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    async function updateScan() {
      loading.value = true;
      try {
        const result = await runAgentUpdateScan(selectedAgent.value);
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    async function installUpdates() {
      loading.value = true;
      try {
        const result = await runAgentUpdateInstall(selectedAgent.value);
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    function showUpdateDetails(update) {
      let support_urls = "";
      update.more_info_urls.forEach(u => {
        support_urls += `<a href='${u}' target='_blank'>${u}</a><br/>`;
      });
      let cats = update.categories.join(", ");
      $q.dialog({
        title: update.title,
        message:
          `<b>Categories:</b> ${cats}<br/><br/>` +
          "<b>Description</b><br/>" +
          update.description.split(". ").join(".<br />") +
          `<br/><br/><b>Support Urls</b><br/>${support_urls}`,
        html: true,
        fullWidth: true,
      });
    }

    watch(selectedAgent, (newValue, oldValue) => {
      if (newValue) {
        getUpdates();
      }
    });

    // vue lifecycle hooks
    onMounted(() => {
      if (selectedAgent.value) getUpdates();
    });

    return {
      // reactive data
      updates,
      filter,
      pagination,
      loading,
      selectedAgent,
      tabHeight,
      agentPlatform,

      // non-reactive data
      columns,

      // methods
      getUpdates,
      editWinUpdate,
      updateScan,
      installUpdates,
      showUpdateDetails,
      notifySuccess,
      truncateText,
      formatDate,
    };
  },
};
</script>