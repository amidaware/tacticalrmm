<template>
  <q-card>
    <q-bar v-if="modal">
      <q-btn @click="getDebugLog" class="q-mr-sm" dense flat push icon="refresh" />Debug Log
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-card-section class="row">
      <q-btn v-if="agentpk" dense flat push @click="getDebugLog" icon="refresh" />
      <tactical-dropdown
        v-if="!agentpk"
        class="col-2 q-pr-sm"
        v-model="agentFilter"
        label="Agents Filter"
        :options="agentOptions"
        mapOptions
        outlined
        clearable
      />
      <tactical-dropdown
        class="col-2 q-pr-sm"
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
      <export-table-btn v-if="!modal" :data="debugLog" :columns="columns" />
    </q-card-section>
    <q-separator />
    <q-card-section>
      <q-table
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        :rows="debugLog"
        :columns="columns"
        :title="modal ? 'Debug Logs' : ''"
        :pagination="{ sortBy: 'entry_time', descending: true }"
        :loading="loading"
        dense
        binary-state-sort
      >
        <template v-slot:top-right>
          <export-table-btn v-if="modal" :data="debugLog" :columns="columns" />
        </template>
      </q-table>
    </q-card-section>
  </q-card>
</template>

<script>
// composition api
import { ref, watch, onMounted } from "vue";
import { useAgentDropdown } from "@/composables/agents";
import { fetchDebugLog } from "@/api/logs";
import { formatDate, formatTableColumnText } from "@/utils/format";

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
    format: (val, row) => formatDate(val, true),
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
    agentpk: Number,
    modal: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    // setup dropdowns
    const { agentOptions, getAgentOptions } = useAgentDropdown();

    // set main debug log functionality
    const debugLog = ref([]);
    const agentFilter = ref(null);
    const logLevelFilter = ref("info");
    const logTypeFilter = ref(null);
    const loading = ref(false);

    async function getDebugLog() {
      loading.value = true;
      const data = {
        logLevelFilter: logLevelFilter.value,
      };
      if (agentFilter.value) data["agentFilter"] = agentFilter.value;
      if (logTypeFilter.value) data["logTypeFilter"] = logTypeFilter.value;

      debugLog.value = await fetchDebugLog(data);
      loading.value = false;
    }

    if (props.agentpk) {
      agentFilter.value = props.agentpk;
      watch(
        () => props.agentpk,
        (newValue, oldValue) => {
          if (newValue) {
            agentFilter.value = props.agentpk;
            getDebugLog();
          }
        }
      );
    }

    // watchers
    watch([logLevelFilter, agentFilter, logTypeFilter], getDebugLog);

    // vue component hooks
    onMounted(() => {
      if (!props.agentpk) getAgentOptions();
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

      // non-reactive data
      columns,
      logTypeOptions,

      // methods
      getDebugLog,
    };
  },
};
</script>