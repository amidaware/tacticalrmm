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
import { watch, onMounted } from "vue";
import { useDebugLog } from "@/composables/logs";
import { useAgentDropdown } from "@/composables/agents";

// ui components
import TacticalDropdown from "@/components/ui/TacticalDropdown";
import ExportTableBtn from "@/components/ui/ExportTableBtn.vue";

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
    const { debugLog, logLevelFilter, logTypeFilter, agentFilter, getDebugLog } = useDebugLog();
    const { agentOptions, getAgentOptions } = useAgentDropdown();

    if (props.agentpk) {
      agentFilter.value = props.agentpk;
    }

    watch([logLevelFilter, agentFilter, logTypeFilter], getDebugLog);

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

      // non-reactive data
      columns: useDebugLog.tableColumns,
      logTypeOptions: useDebugLog.logTypeOptions,

      // methods
      getDebugLog,
    };
  },
};
</script>