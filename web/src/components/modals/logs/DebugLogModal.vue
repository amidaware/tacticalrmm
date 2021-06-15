<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card class="q-dialog-plugin bg-grey-10 text-white">
      <q-bar>
        <q-btn @click="getDebugLog" class="q-mr-sm" dense flat push icon="refresh" />Debug Log
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section class="row">
        <tactical-dropdown
          class="col-2 q-pr-sm"
          v-model="agentFilter"
          label="Agents Filter"
          :options="agentOptions"
          dark
          clearable
        />
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
      </q-card-section>
      <q-separator />
      <q-card-section>
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
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
// composition api
import { watch, onMounted } from "vue";
import { useDialogPluginComponent } from "quasar";
import { useDebugLog } from "@/composables/logs";
import { useAgentDropdown } from "@/composables/agents";
import { exportTableToCSV } from "@/utils/csv";

// ui components
import TacticalDropdown from "@/components/ui/TacticalDropdown";

export default {
  name: "LogModal",
  components: {
    TacticalDropdown,
  },
  emits: [...useDialogPluginComponent.emits],
  setup() {
    const { debugLog, logLevelFilter, logTypeFilter, agentFilter, getDebugLog } = useDebugLog();
    const { dialogRef, onDialogHide } = useDialogPluginComponent();
    const { agentOptions, getAgentOptions } = useAgentDropdown();

    watch([logLevelFilter, agentFilter, logTypeFilter], getDebugLog);

    onMounted(() => {
      getAgentOptions();
      getDebugLog();
    });

    return {
      // data
      debugLog,
      logLevelFilter,
      logTypeFilter,
      agentFilter,
      agentOptions,

      // non-reactive data
      columns: useDebugLog.debugLogTableColumns,
      logTypeOptions: useDebugLog.logTypeOptions,

      // methods
      getDebugLog,
      exportDebugLog: () => {
        exportTableToCSV(debugLog.value, useDebugLog.debugLogTableColumns);
      },

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>