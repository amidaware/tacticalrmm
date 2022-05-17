<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else-if="agentPlatform.toLowerCase() !== 'windows'" class="q-pa-sm">
    Only supported for Windows agents at this time
  </div>
  <div v-else>
    <q-table
      :table-class="{
        'table-bgcolor': !$q.dark.isActive,
        'table-bgcolor-dark': $q.dark.isActive,
      }"
      class="tabs-tbl-sticky"
      dense
      :rows="software"
      :columns="columns"
      :filter="filter"
      :style="{ 'max-height': tabHeight }"
      v-model:pagination="pagination"
      binary-state-sort
      row-key="id"
      virtual-scroll
      :rows-per-page-options="[0]"
      :loading="loading"
    >
      <template v-slot:loading>
        <q-inner-loading showing color="primary" />
      </template>

      <template v-slot:top>
        <q-btn
          class="q-mr-sm"
          dense
          flat
          push
          @click="refreshSoftware"
          icon="refresh"
        />
        <q-btn
          icon="add"
          label="Install Software"
          no-caps
          dense
          flat
          push
          @click="showInstallSoftwareModal"
        />

        <q-space />

        <q-input
          v-model="filter"
          outlined
          label="Search"
          dense
          clearable
          class="q-pr-sm"
        >
          <template v-slot:prepend>
            <q-icon name="search" color="primary" />
          </template>
        </q-input>
        <export-table-btn :data="software" :columns="columns" />
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useQuasar } from "quasar";
import { useStore } from "vuex";
import { fetchAgentSoftware, refreshAgentSoftware } from "@/api/software";

// ui imports
import InstallSoftware from "@/components/software/InstallSoftware.vue";
import ExportTableBtn from "@/components/ui/ExportTableBtn.vue";

// static data
const columns = [
  {
    name: "name",
    align: "left",
    label: "Name",
    field: "name",
    sortable: true,
  },
  {
    name: "publisher",
    align: "left",
    label: "Publisher",
    field: "publisher",
    sortable: true,
  },
  {
    name: "install_date",
    align: "left",
    label: "Installed On",
    field: "install_date",
    sortable: false,
    format: (val) => {
      return val === "01/01/1" || val === "01-1-01" ? "" : val;
    },
  },
  {
    name: "size",
    align: "left",
    label: "Size",
    field: "size",
    sortable: false,
  },
  {
    name: "version",
    align: "left",
    label: "Version",
    field: "version",
    sortable: false,
  },
];

export default {
  name: "SoftwareTab",
  components: {
    ExportTableBtn,
  },
  setup() {
    // setup quasar
    const $q = useQuasar();

    // setup vuex
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const tabHeight = computed(() => store.state.tabHeight);
    const agentPlatform = computed(() => store.state.agentPlatform);

    // software tab logic
    const software = ref([]);
    const loading = ref(false);
    const filter = ref("");
    const pagination = ref({
      rowsPerPage: 0,
      sortBy: "name",
      descending: false,
    });

    async function getSoftware() {
      loading.value = true;
      software.value = await fetchAgentSoftware(selectedAgent.value);
      loading.value = false;
    }

    async function refreshSoftware() {
      loading.value = true;
      await refreshAgentSoftware(selectedAgent.value);
      await getSoftware();
      loading.value = false;
    }

    function showInstallSoftwareModal() {
      $q.dialog({
        component: InstallSoftware,
        componentProps: {
          agent_id: selectedAgent.value,
        },
      });
    }

    watch(selectedAgent, (newValue) => {
      if (newValue) {
        getSoftware();
      }
    });

    onMounted(() => {
      if (selectedAgent.value) getSoftware();
    });

    return {
      // reactive data
      software,
      loading,
      filter,
      pagination,
      selectedAgent,
      tabHeight,
      agentPlatform,

      // non-reactive data
      columns,

      // methods
      refreshSoftware,
      showInstallSoftwareModal,
    };
  },
};
</script>
