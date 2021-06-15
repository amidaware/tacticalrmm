<template>
  <div v-if="!selectedAgent">No agent selected</div>
  <div v-else class="bg-grey-10 text-white">
    <div class="q-pa-md row">
      <tactical-dropdown
        class="col-2 q-pr-sm"
        v-model="logTypeFilter"
        label="Log Type Filter"
        :options="logTypeOptions"
        dark
        clearable
      />
      <q-radio dark v-model="logLevelFilter" color="cyan" val="info" label="Info" />
      <q-radio dark v-model="logLevelFilter" color="red" val="critical" label="Critical" />
      <q-radio dark v-model="logLevelFilter" color="red" val="error" label="Error" />
      <q-radio dark v-model="logLevelFilter" color="yellow" val="warning" label="Warning" />
    </div>
    <q-separator />

    <q-table
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      :rows="debugLog"
      :columns="columns"
      dense
      title="Debug Logs"
      :pagination="{ sortBy: 'entry_time', descending: true }"
    >
      <template v-slot:top-right>
        <q-btn color="primary" icon-right="archive" label="Export to csv" no-caps @click="exportDebugLog" />
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { watch, computed } from "vue";
import { useStore } from "vuex";
import { useDebugLog } from "@/composables/logs";
import { exportTableToCSV } from "@/utils/csv";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown";

export default {
  name: "DebugTab",
  components: {
    TacticalDropdown,
  },
  setup() {
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const { debugLog, logLevelFilter, logTypeFilter, agentFilter, getDebugLog } = useDebugLog();

    watch([logLevelFilter, logTypeFilter], () => getDebugLog());
    watch(selectedAgent, (newValue, oldValue) => {
      if (newValue) {
        agentFilter.value = selectedAgent.value;
        getDebugLog();
      }
    });

    return {
      // data
      debugLog,
      logLevelFilter,
      logTypeFilter,

      // non-reactive data
      columns: useDebugLog.debugLogTableColumns,
      logTypeOptions: useDebugLog.logTypeOptions,

      // computed
      selectedAgent,

      // methods
      getDebugLog,
      exportDebugLog: () => {
        exportTableToCSV(debugLog.value, useDebugLog.debugLogTableColumns);
      },
    };
  },
};
</script>