<template>
  <q-card>
    <q-bar>
      <q-btn @click="search" class="q-mr-sm" dense flat push icon="refresh" />
      <q-space />Audit Manager
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <div class="text-h6 q-pl-sm q-pt-sm">Filter</div>
    <div class="row">
      <div class="q-pa-sm col-1">
        <q-option-group v-model="filterType" :options="filterTypeOptions" color="primary" />
      </div>
      <div class="q-pa-sm col-2" v-if="filterType === 'agents'">
        <tactical-dropdown v-model="agentFilter" :options="agentOptions" label="Agent" clearable multiple filled />
      </div>
      <div class="q-pa-sm col-2" v-if="filterType === 'clients'">
        <tactical-dropdown
          v-model="clientFilter"
          :options="clientOptions"
          label="Clients"
          clearable
          multiple
          filled
          mapOptions
        />
      </div>
      <div class="q-pa-sm col-2">
        <tactical-dropdown v-model="userFilter" :options="userOptions" label="Users" clearable filled multiple />
      </div>
      <div class="q-pa-sm col-2">
        <tactical-dropdown
          v-model="actionFilter"
          :options="actionOptions"
          label="Action"
          clearable
          filled
          multiple
          mapOptions
        />
      </div>
      <div class="q-pa-sm col-2">
        <tactical-dropdown
          v-model="objectFilter"
          :options="objectOptions"
          label="Object"
          clearable
          filled
          multiple
          mapOptions
        />
      </div>
      <div class="q-pa-sm col-2">
        <tactical-dropdown v-model="timeFilter" :options="timeOptions" label="Time" filled mapOptions />
      </div>
      <div class="q-pa-sm col-1">
        <q-btn color="primary" label="Search" @click="search" />
      </div>
    </div>
    <q-separator />
    <q-card-section>
      <q-table
        @request="onRequest"
        :title="modal ? 'Audit Logs' : ''"
        :rows="auditLogs"
        :columns="columns"
        row-key="id"
        dense
        binary-state-sort
        v-model:pagination="pagination"
        :rows-per-page-options="[25, 50, 100, 500, 1000]"
        :no-data-label="tableNoDataText"
        @row-click="openAuditDetail"
        :loading="loading"
      >
        <template v-slot:top-right>
          <export-table-btn :data="auditLogs" :columns="columns" />
        </template>
        <template v-slot:body-cell-action="props">
          <q-td :props="props">
            <div>
              <q-badge :color="formatActionColor(props.value)" :label="props.value" />
            </div>
          </q-td>
        </template>
      </q-table>
    </q-card-section>
  </q-card>
</template>

<script>
// composition imports
import { onMounted } from "vue";
import { useAuditLog } from "@/composables/logs";
import { useClientDropdown } from "@/composables/clients";
import { useAgentDropdown } from "@/composables/agents";
import { useUserDropdown } from "@/composables/accounts";

// ui imported
import ExportTableBtn from "@/components/ui/ExportTableBtn"
import TacticalDropdown from "@/components/ui/TacticalDropdown";
import ExportTableBtn from '../ui/ExportTableBtn.vue';

export default {
  name: "AuditManager",
  components: { TacticalDropdown, ExportTableBtn },
  props: {
    agentpk:
    ExportTableBtn Number,
    modal: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    // setup dropdowns
    const { clientOptions, getClientOptions } = useClientDropdown();
    const { agentOptions, getAgentOptions } = useAgentDropdown();
    const { userOptions, userDropdownLoading, getUserOptions } = useUserDropdown();

    onMounted(() => {
      getClientOptions();
      getAgentOptions(true);
      getUserOptions(true);
    });

    const AuditLog = useAuditLog();

    return {
      // data
      auditLogs: AuditLog.auditLogs,
      agentFilter: AuditLog.agentFilter,
      userFilter: AuditLog.userFilter,
      actionFilter: AuditLog.actionFilter,
      clientFilter: AuditLog.clientFilter,
      objectFilter: AuditLog.objectFilter,
      timeFilter: AuditLog.timeFilter,
      filterType: AuditLog.filterType,
      loading: AuditLog.loading,
      pagination: AuditLog.pagination,
      userOptions,
      userDropdownLoading,

      // non-reactive data
      clientOptions,
      agentOptions,
      columns: useAuditLog.tableColumns,
      actionOptions: useAuditLog.actionOptions,
      objectOptions: useAuditLog.objectOptions,
      timeOptions: useAuditLog.timeOptions,
      filterTypeOptions: useAuditLog.filterTypeOptions,

      //computed
      tableNoDataText: AuditLog.noDataText,

      // methods
      search: AuditLog.search,
      onRequest: AuditLog.onRequest,
      openAuditDetail: AuditLog.openAuditDetail,
      formatActionColor: AuditLog.formatActionColor,
    };
  },
};
</script>