<template>
  <q-card>
    <q-bar v-if="modal">
      <q-btn @click="getDebugLog" class="q-mr-sm" dense flat push icon="refresh" />Debug Log
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-table
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="tabs-tbl-sticky"
      :style="{ 'max-height': tabHeight ? tabHeight : `${$q.screen.height - 33}px` }"
      :rows="debugLog"
      :columns="columns"
      :title="modal ? 'Debug Logs' : ''"
      :pagination="{ sortBy: 'entry_time', descending: true, rowsPerPage: 0 }"
      :loading="loading"
      :filter="filter"
      virtual-scroll
      dense
      binary-state-sort
      :rows-per-page-options="[0]"
    >
      <template v-slot:top>
        <q-btn v-if="agent" class="q-pr-sm" dense flat push @click="getDebugLog" icon="refresh" />
        <tactical-dropdown
          v-if="!agent"
          class="q-pr-sm"
          style="width: 250px"
          v-model="agentFilter"
          label="Agents Filter"
          :options="agentOptions"
          mapOptions
          outlined
          clearable
          filterable
        />
        <tactical-dropdown
          class="q-pr-sm"
          style="width: 250px"
          v-model="logTypeFilter"
          label="Log Type Filter"
          :options="logTypeOptions"
          mapOptions
          outlined
          clearable
        />
        <q-radio v-model="logLevelFilter" color="cyan" val="info" label="Info" />
        <q-radio v-model="logLevelFilter" color="red" val="critical" label="Critical" />
        <q-radio v-model="logLevelFilter" color="red" val="error" label="Error" />
        <q-radio v-model="logLevelFilter" color="yellow" val="warning" label="Warning" />
        <q-space />
        <q-input v-model="filter" outlined label="Search" dense clearable class="q-pr-sm">
          <template v-slot:prepend>
            <q-icon name="search" color="primary" />
          </template>
        </q-input>
        <export-table-btn :data="debugLog" :columns="columns" />
      </template>

      <template v-slot:top-row>
        <q-tr v-if="Array.isArray(debugLog) && debugLog.length === 1000">
          <q-td colspan="100%">
            <q-icon name="warning" color="warning" />
            Results are limited to 1000 rows.
          </q-td>
        </q-tr>
      </template>

      <template v-slot:body-cell-entry_time="props">
        <q-td :props="props">
          {{ formatDate(props.value) }}
        </q-td>
      </template>
    </q-table>
  </q-card>
</template>

<script>
// composition api
import { ref, watch, computed, onMounted } from "vue";
import { useStore } from "vuex";
import { useAgentDropdown } from "@/composables/agents";
import { fetchDebugLog } from "@/api/logs";
import { formatTableColumnText } from "@/utils/format";

// ui components
import TacticalDropdown from "@/components/ui/TacticalDropdown";
import ExportTableBtn from "@/components/ui/ExportTableBtn.vue";

// static data
const logTypeOptions = [
  { label: "Agent Update", value: "agent_update" },
  { label: "Agent Issues", value: "agent_issues" },
  { label: "Windows Updates", value: "windows_updates" },
  { label: "System Issues", value: "system_issues" },
  { label: "Scripting", value: "scripting" },
];

const columns = [
  {
    name: "entry_time",
    label: "Time",
    field: "entry_time",
    align: "left",
    sortable: true,
  },
  { name: "log_level", label: "Log Level", field: "log_level", align: "left", sortable: true },
  { name: "agent", label: "Agent", field: "agent", align: "left", sortable: true },
  {
    name: "log_type",
    label: "Log Type",
    field: "log_type",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  },
  { name: "message", label: "Message", field: "message", align: "left", sortable: true },
];

export default {
  name: "LogModal",
  components: {
    TacticalDropdown,
    ExportTableBtn,
  },
  props: {
    agent: String,
    tabHeight: String,
    modal: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    // setup vuex
    const store = useStore();

    const formatDate = computed(() => store.getters.formatDate);

    // setup dropdowns
    const { agentOptions, getAgentOptions } = useAgentDropdown();

    // set main debug log functionality
    const debugLog = ref([]);
    const agentFilter = ref(null);
    const logLevelFilter = ref("info");
    const logTypeFilter = ref(null);
    const loading = ref(false);
    const filter = ref("");

    async function getDebugLog() {
      loading.value = true;
      try {
        const data = {
          logLevelFilter: logLevelFilter.value,
        };
        if (agentFilter.value) data["agentFilter"] = agentFilter.value;
        if (logTypeFilter.value) data["logTypeFilter"] = logTypeFilter.value;

        debugLog.value = await fetchDebugLog(data);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    if (props.agent) {
      agentFilter.value = props.agent;
      watch(
        () => props.agent,
        (newValue, oldValue) => {
          if (newValue) {
            agentFilter.value = props.agent;
            getDebugLog();
          }
        }
      );
    }

    // watchers
    watch([logLevelFilter, agentFilter, logTypeFilter], getDebugLog);

    // vue component hooks
    onMounted(() => {
      if (!props.agent) getAgentOptions();
      getDebugLog();
    });

    return {
      // data
      debugLog,
      logLevelFilter,
      logTypeFilter,
      agentFilter,
      agentOptions,
      loading,
      filter,

      // non-reactive data
      columns,
      logTypeOptions,

      // methods
      getDebugLog,
      formatDate,
    };
  },
};
</script>