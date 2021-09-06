<template>
  <q-card>
    <q-bar v-if="modal">
      <q-btn @click="search" class="q-mr-sm" dense flat push icon="refresh" />
      <q-space />Audit Manager
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <div class="text-h6 q-pl-sm q-pt-sm">Filter</div>
    <div class="row">
      <div class="q-pa-sm col-1" v-if="!agentpk">
        <q-option-group v-model="filterType" :options="filterTypeOptions" color="primary" />
      </div>
      <div class="q-pa-sm col-2" v-if="filterType === 'agents' && !agentpk">
        <tactical-dropdown
          v-model="agentFilter"
          :options="agentOptions"
          label="Agent"
          clearable
          mapOptions
          multiple
          filled
        />
      </div>
      <div class="q-pa-sm col-2" v-if="filterType === 'clients' && !agentpk">
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
      <div class="q-pa-sm col-2" v-if="!agentpk">
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
      <div class="q-pa-sm col-1" v-if="!agentpk">
        <q-btn color="primary" label="Search" @click="search" />
      </div>
      <q-space />
      <div class="q-pa-sm" v-if="!modal">
        <export-table-btn :data="auditLogs" :columns="columns" />
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
          <export-table-btn v-if="modal" :data="auditLogs" :columns="columns" />
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
import { ref, computed, watch, onMounted } from "vue";
import { useClientDropdown } from "@/composables/clients";
import { useAgentDropdown } from "@/composables/agents";
import { useUserDropdown } from "@/composables/accounts";
import { useQuasar } from "quasar";
import { fetchAuditLog } from "@/api/logs";
import { formatDate, formatTableColumnText } from "@/utils/format";

// ui imported
import AuditLogDetailModal from "@/components/logs/AuditLogDetailModal";
import ExportTableBtn from "@/components/ui/ExportTableBtn";
import TacticalDropdown from "@/components/ui/TacticalDropdown";

// static data
const columns = [
  {
    name: "entry_time",
    label: "Time",
    field: "entry_time",
    align: "left",
    sortable: true,
    format: (val, row) => formatDate(val, true),
  },
  { name: "username", label: "Username", field: "username", align: "left", sortable: true },
  { name: "agent", label: "Agent", field: "agent", align: "left", sortable: true },
  {
    name: "action",
    label: "Action",
    field: "action",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  },
  {
    name: "object_type",
    label: "Object",
    field: "object_type",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  },
  { name: "message", label: "Message", field: "message", align: "left", sortable: true },
  { name: "client_ip", label: "Client IP", field: "ip_address", align: "left", sortable: true },
];

const agentActionOptions = [
  { value: "add", label: "Add Object" },
  { value: "modify", label: "Modify Object" },
  { value: "execute_command", label: "Execute Command" },
  { value: "execute_script", label: "Execute Script" },
  { value: "remote_session", label: "Remote Session" },
  { value: "url_action", label: "URL Action" },
];

const actionOptions = [
  { value: "agent_install", label: "Agent Installs" },
  { value: "bulk_action", label: "Bulk Actions" },
  { value: "delete", label: "Delete Object" },
  { value: "failed_login", label: "Failed User login" },
  { value: "login", label: "User Login" },
  { value: "modify", label: "Modify Object" },
  { value: "task_run", label: "Task Run Results" },
];

const objectOptions = [
  { value: "agent", label: "Agent" },
  { value: "automatedtask", label: "Automated Task" },
  { value: "bulk", label: "Bulk Actions" },
  { value: "coresettings", label: "Core Settings" },
  { value: "check", label: "Check" },
  { value: "client", label: "Client" },
  { value: "policy", label: "Policy" },
  { value: "site", label: "Site" },
  { value: "script", label: "Script" },
  { value: "user", label: "User" },
  { value: "winupdatepolicy", label: "Patch Policy" },
  { value: "alerttemplate", label: "Alert Template" },
  { value: "role", label: "Role" },
  { value: "urlaction", label: "URL Action" },
  { value: "keystore", label: "Global Key Store" },
  { value: "customfield", label: "Custom Field" },
];

const timeOptions = [
  { value: 1, label: "1 Day Ago" },
  { value: 7, label: "1 Week Ago" },
  { value: 30, label: "30 Days Ago" },
  { value: 90, label: "3 Months Ago" },
  { value: 180, label: "6 Months Ago" },
  { value: 365, label: "1 Year Ago" },
  { value: 0, label: "Everything" },
];

const filterTypeOptions = [
  {
    label: "Clients",
    value: "clients",
  },
  {
    label: "Agents",
    value: "agents",
  },
];

export default {
  name: "AuditManager",
  components: { TacticalDropdown, ExportTableBtn },
  props: {
    agentpk: Number,
    modal: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    // setup dropdowns
    const { clientOptions, getClientOptions } = useClientDropdown();
    const { agentOptions, getAgentOptions } = useAgentDropdown();
    const { userOptions, getUserOptions } = useUserDropdown();

    // setup main audit log functionality
    const auditLogs = ref([]);
    const agentFilter = ref(null);
    const userFilter = ref(null);
    const actionFilter = ref(null);
    const clientFilter = ref(null);
    const objectFilter = ref(null);
    const timeFilter = ref(7);
    const filterType = ref("clients");
    const loading = ref(false);
    const searched = ref(false);

    const pagination = ref({
      rowsPerPage: 25,
      rowsNumber: null,
      sortBy: "entry_time",
      descending: true,
      page: 1,
    });

    async function search() {
      loading.value = true;
      searched.value = true;

      const data = {
        pagination: pagination.value,
      };

      if (agentFilter.value && agentFilter.value.length > 0) data["agentFilter"] = agentFilter.value;
      else if (clientFilter.value && clientFilter.value.length > 0) data["clientFilter"] = clientFilter.value;
      if (userFilter.value && userFilter.value.length > 0) data["userFilter"] = userFilter.value;
      if (timeFilter.value) data["timeFilter"] = timeFilter.value;
      if (actionFilter.value && actionFilter.value.length > 0) data["actionFilter"] = actionFilter.value;
      if (objectFilter.value && objectFilter.value.length > 0) data["objectFilter"] = objectFilter.value;

      const { audit_logs, total } = await fetchAuditLog(data);
      auditLogs.value = audit_logs;
      pagination.value.rowsNumber = total;

      loading.value = false;
    }

    function onRequest(data) {
      const { page, rowsPerPage, sortBy, descending } = data.pagination;

      pagination.value.page = page;
      pagination.value.rowsPerPage = rowsPerPage;
      pagination.value.sortBy = sortBy;
      pagination.value.descending = descending;

      search();
    }

    // audit detail modal
    const { dialog } = useQuasar();
    function openAuditDetail(evt, log) {
      dialog({
        component: AuditLogDetailModal,
        componentProps: {
          log,
        },
      });
    }

    function formatActionColor(action) {
      if (action === "add") return "success";
      else if (action === "agent_install") return "success";
      else if (action === "modify") return "warning";
      else if (action === "delete") return "negative";
      else if (action === "failed_login") return "negative";
      else return "primary";
    }

    // watchers
    watch(filterType, () => {
      agentFilter.value = null;
      clientFilter.value = null;
    });

    if (props.agentpk) {
      agentFilter.value = [props.agentpk];
      watch([userFilter, actionFilter, timeFilter], search);
    }

    // vue component hooks
    onMounted(() => {
      if (!props.agentpk) {
        getClientOptions();
        getAgentOptions();
      } else {
        search();
      }

      getUserOptions(true);
    });

    return {
      // data
      auditLogs,
      agentFilter,
      userFilter,
      actionFilter,
      clientFilter,
      objectFilter,
      timeFilter,
      filterType,
      loading,
      searched,
      pagination,
      userOptions,

      // non-reactive data
      clientOptions,
      agentOptions,
      columns,
      actionOptions: props.agentpk ? [...agentActionOptions] : [...agentActionOptions, ...actionOptions],
      objectOptions,
      timeOptions,
      filterTypeOptions,

      //computed
      tableNoDataText: computed(() =>
        searched.value ? "No data found. Try to refine you search" : "Click search to find audit logs"
      ),

      // methods
      search,
      onRequest,
      openAuditDetail,
      formatActionColor,
    };
  },
};
</script>