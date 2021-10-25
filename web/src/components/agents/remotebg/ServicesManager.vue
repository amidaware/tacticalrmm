<template>
  <q-table
    dense
    :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
    class="remote-bg-tbl-sticky"
    style="max-height: 85vh"
    :rows="services"
    :columns="columns"
    :pagination="{ rowsPerPage: 0, sortBy: 'display_name', descending: false }"
    :filter="filter"
    row-key="display_name"
    binary-state-sort
    :rows-per-page-options="[0]"
    :loading="loading"
  >
    <template v-slot:top>
      <q-btn dense flat push @click="getServices" icon="refresh" />
      <q-space />
      <q-input v-model="filter" outlined label="Search" dense clearable>
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
      </q-input>
      <!-- file download doesn't work so disabling -->
      <export-table-btn v-show="false" class="q-ml-sm" :columns="columns" :data="services" />
    </template>
    <template v-slot:body="props">
      <q-tr :props="props" class="cursor-pointer" @dblclick="showServiceDetail(props.row)">
        <q-menu context-menu>
          <q-list dense style="min-width: 200px">
            <q-item clickable v-close-popup @click="sendServiceAction(props.row, 'start')">
              <q-item-section>Start</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="sendServiceAction(props.row, 'stop')">
              <q-item-section>Stop</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="sendServiceAction(props.row, 'restart')">
              <q-item-section>Restart</q-item-section>
            </q-item>
            <q-separator />
            <q-item clickable v-close-popup @click="showServiceDetail(props.row)">
              <q-item-section>Service Details</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
        <q-td key="display_name" :props="props">
          <q-icon name="fas fa-cogs" />
          &nbsp;&nbsp;&nbsp;{{ truncateText(props.row.display_name, 30) }}
        </q-td>
        <q-td key="name" :props="props">{{ props.row.name }}</q-td>
        <q-td key="start_type" :props="props">{{
          props.row.start_type.toLowerCase() === "automatic" && props.row.autodelay
            ? `${props.row.start_type} (Delayed)`
            : `${props.row.start_type}`
        }}</q-td>
        <q-td key="pid" :props="props">{{ props.row.pid === 0 ? "" : props.row.pid }}</q-td>
        <q-td key="status" :props="props">{{ props.row.status }}</q-td>
        <q-td key="username" :props="props">{{ props.row.username ? props.row.username : "LocalSystem" }}</q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
// composition imports
import { ref, onMounted } from "vue";
import { useQuasar } from "quasar";
import { getAgentServices, sendAgentServiceAction } from "@/api/services";
import { notifySuccess } from "@/utils/notify";
import { truncateText } from "@/utils/format";

// ui imports
import ServiceDetail from "@/components/agents/remotebg/ServiceDetail";
import ExportTableBtn from "@/components/ui/ExportTableBtn";

// static data
const columns = [
  {
    name: "display_name",
    label: "Display Name",
    field: "display_name",
    align: "left",
    sortable: true,
  },
  {
    name: "name",
    label: "Name",
    field: "name",
    align: "left",
    sortable: true,
  },
  {
    name: "start_type",
    label: "Startup",
    field: "start_type",
    align: "left",
    sortable: true,
  },
  {
    name: "pid",
    label: "PID",
    field: "pid",
    align: "left",
    sortable: true,
  },
  {
    name: "status",
    label: "Status",
    field: "status",
    align: "left",
    sortable: true,
  },
  {
    name: "username",
    label: "Log On As",
    field: "username",
    align: "left",
    sortable: true,
  },
];

// static data
const startupOptions = [
  {
    label: "Automatic (Delayed Start)",
    value: "autodelay",
  },
  {
    label: "Automatic",
    value: "automatic",
  },
  {
    label: "Manual",
    value: "manual",
  },
  {
    label: "Disabled",
    value: "disabled",
  },
];

export default {
  name: "ServicesManager",
  components: {
    ExportTableBtn,
  },
  props: {
    agent_id: !String,
  },
  setup(props) {
    // quasar setup
    const $q = useQuasar();

    // services manager setup
    const services = ref([]);
    const filter = ref("");
    const loading = ref(false);

    function showServiceDetail(service) {
      $q.dialog({
        component: ServiceDetail,
        componentProps: {
          service: service,
          agent_id: props.agent_id,
        },
      }).onOk(getServices);
    }

    async function getServices() {
      loading.value = true;
      services.value = await getAgentServices(props.agent_id);
      loading.value = false;
    }

    async function sendServiceAction(service, action) {
      loading.value = true;

      try {
        const result = await sendAgentServiceAction(props.agent_id, service.name, { sv_action: action });
        notifySuccess(result);
        await getServices();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    // vue lifecycle hooks
    onMounted(getServices);

    return {
      // reactive data
      services,
      filter,
      loading,

      // dialogs
      showServiceDetail,

      // non-reactive data
      columns,
      startupOptions,

      // methods
      getServices,
      sendServiceAction,
      truncateText,
    };
  },
};
</script>