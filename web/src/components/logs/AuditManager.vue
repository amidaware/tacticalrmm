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
    <q-table
      @request="onRequest"
      :title="modal ? 'Audit Logs' : ''"
      :rows="auditLogs"
      :columns="columns"
      class="tabs-tbl-sticky"
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      :style="{ 'max-height': tabHeight ? tabHeight : `${$q.screen.height - 33}px` }"
      row-key="id"
      dense
      binary-state-sort
      v-model:pagination="pagination"
      :rows-per-page-options="[25, 50, 100, 500, 1000]"
      :no-data-label="tableNoDataText"
      @row-click="openAuditDetail"
      virtual-scroll
      :loading="loading"
    >
      <template v-slot:top>
        <q-btn v-if="agent" class="q-pr-sm" dense flat push @click="search" icon="refresh" />
        <q-option-group
          v-if="!agent"
          class="q-pr-sm"
          v-model="filterType"
          :options="filterTypeOptions"
          color="primary"
        />
        <tactical-dropdown
          v-if="filterType === 'agents' && !agent"
          class="q-pr-sm"
          style="width: 200px"
          v-model="agentFilter"
          :options="agentOptions"
          label="Agent"
          clearable
          mapOptions
          multiple
          filled
        />
        <tactical-dropdown
          v-if="filterType === 'clients' && !agent"
          class="q-pr-sm"
          style="width: 200px"
          v-model="clientFilter"
          :options="clientOptions"
          label="Clients"
          clearable
          multiple
          filled
          mapOptions
        />
        <tactical-dropdown
          class="q-pr-sm"
          style="width: 200px"
          v-model="userFilter"
          :options="userOptions"
          label="Users"
          clearable
          filled
          multiple
        />
        <tactical-dropdown
          class="q-pr-sm"
          style="width: 200px"
          v-model="actionFilter"
          :options="actionOptions"
          label="Action"
          clearable
          filled
          multiple
          mapOptions
        />
        <tactical-dropdown
          class="q-pr-sm"
          style="width: 200px"
          v-if="!agent"
          v-model="objectFilter"
          :options="objectOptions"
          label="Object"
          clearable
          filled
          multiple
          mapOptions
        />
        <tactical-dropdown
          class="q-pr-sm"
          style="width: 200px"
          v-model="timeFilter"
          :options="timeOptions"
          label="Time"
          filled
          mapOptions
        />
        <q-btn v-if="!agent" color="primary" label="Search" @click="search" />

        <q-space />
        <export-table-btn :data="auditLogs" :columns="columns" />
      </template>
      <template v-slot:body-cell-action="props">
        <q-td :props="props">
          <div>
            <q-badge :color="formatActionColor(props.value)" :label="props.value" />
          </div>
        </q-td>
      </template>
      <template v-slot:body-cell-client="props">
        <q-td :props="props">
          <span v-if="props.value">{{ props.value.client_name }}</span>
        </q-td>
      </template>
      <template v-slot:body-cell-site="props">
        <q-td :props="props">
          <span v-if="props.value">{{ props.value.name }}</span>
        </q-td>
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
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { useClientDropdown } from "@/composables/clients";
import { useAgentDropdown } from "@/composables/agents";
import { useUserDropdown } from "@/composables/accounts";
import { useQuasar } from "quasar";
import { fetchAuditLog } from "@/api/logs";
import { formatTableColumnText } from "@/utils/format";

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
  },
  { name: "username", label: "Username", field: "username", align: "left", sortable: true },
  { name: "agent", label: "Agent", field: "agent", align: "left", sortable: true },
  { name: "client", label: "Client", field: "site", align: "left", sortable: true },
  { name: "site", label: "Site", field: "site", align: "left", sortable: true },
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
      try {
        const { audit_logs, total } = await fetchAuditLog(data);
        auditLogs.value = audit_logs;
        pagination.value.rowsNumber = total;
      } catch (e) {}

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

    if (props.agent) {
      agentFilter.value = [props.agent];
      watch([userFilter, actionFilter, timeFilter], search);
      watch(
        () => props.agent,
        (newValue, oldValue) => {
          if (newValue) {
            agentFilter.value = [props.agent];
            search();
          }
        }
      );
    }

    // vue component hooks
    onMounted(() => {
      if (!props.agent) {
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
      actionOptions: props.agent ? [...agentActionOptions] : [...agentActionOptions, ...actionOptions],
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
      formatDate,
    };
  },
};
</script>