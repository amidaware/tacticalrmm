<template>
  <div class="q-pa-md">
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="remote-bg-tbl-sticky"
      :rows="services"
      :columns="columns"
      v-model:pagination="pagination"
      :filter="filter"
      row-key="display_name"
      binary-state-sort
      hide-bottom
    >
      <template v-slot:top>
        <q-btn dense flat push @click="getServices" icon="refresh" />
        <q-space />
        <q-input v-model="filter" outlined label="Search" dense clearable>
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>
      <template v-slot:body="props">
        <q-tr :props="props">
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

    <q-dialog v-if="service" v-model="showServiceDetailModal" @hide="closeServiceDetail">
      <q-card style="width: 600px; max-width: 80vw">
        <q-bar>
          Service Details - {{ service.display_name }}
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>

        <q-card-section>
          <div class="row">
            <div class="col-3">Service name:</div>
            <div class="col-9">{{ service.name }}</div>
          </div>
          <br />
          <div class="row">
            <div class="col-3">Display name:</div>
            <div class="col-9">{{ service.display_name }}</div>
          </div>
          <br />
          <div class="row">
            <div class="col-3">Description:</div>
            <div class="col-9">
              <q-field outlined :color="$q.dark.isActive ? 'white' : 'black'">{{ service.description }}</q-field>
            </div>
          </div>
          <br />
          <div class="row">
            <div class="col-3">Path:</div>
            <div class="col-9">
              <code>{{ service.binpath }}</code>
            </div>
          </div>
          <br />
          <br />
          <div class="row">
            <div class="col-3">Startup type:</div>
            <div class="col-5">
              <q-select
                dense
                options-dense
                outlined
                v-model="startupType"
                :options="startupOptions"
                map-options
                emit-value
              />
            </div>
          </div>
        </q-card-section>
        <hr />
        <q-card-section>
          <div class="row">
            <div class="col-3">Service status:</div>
            <div class="col-9">{{ service.status }}</div>
          </div>
          <br />
          <div class="row">
            <q-btn-group push>
              <q-btn
                color="gray"
                glossy
                :text-color="$q.dark.isActive ? 'white' : 'black'"
                push
                label="Start"
                @click="sendServiceAction(service, 'start')"
              />
              <q-btn
                color="gray"
                glossy
                :text-color="$q.dark.isActive ? 'white' : 'black'"
                push
                label="Stop"
                @click="sendServiceAction(service, 'stop')"
              />
              <q-btn
                color="gray"
                glossy
                :text-color="$q.dark.isActive ? 'white' : 'black'"
                push
                label="Restart"
                @click="sendServiceAction(service, 'restart')"
              />
            </q-btn-group>
          </div>
        </q-card-section>
        <hr />
        <q-card-actions align="right">
          <q-btn
            :loading="modalLoading"
            :disable="!startupTypeEdited"
            dense
            label="Save"
            color="primary"
            @click="editServiceStartup()"
          />
          <q-btn dense label="Cancel" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
// composition imports
import { ref, computed, onMounted } from "vue";
import { useQuasar } from "quasar";
import { getAgentServices, editAgentServiceStartType, sendAgentServiceAction } from "@/api/services";
import { notifySuccess } from "@/utils/notify";
import { truncateText } from "@/utils/format";

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
  props: {
    agent_id: !String,
  },
  setup(props) {
    // quasar setup
    const $q = useQuasar();

    // services manager setup
    const services = ref([]);
    const filter = ref("");
    const pagination = ref({
      rowsPerPage: 9999,
      sortBy: "display_name",
      descending: false,
    });

    // services detail modal
    const service = ref(null);
    const showServiceDetailModal = ref(false);
    const startupType = ref("");
    const modalLoading = ref(false);

    const startupTypeEdited = computed(() => {
      if (!service.value) return false;
      else if (service.value.start_type.toLowerCase() === "automatic" && service.value.autodelay)
        return startupType.value !== "autodelay";
      else return service.value.start_type.toLowerCase() !== startupType.value;
    });

    function showServiceDetail(svc) {
      service.value = svc;

      if (svc.start_type.toLowerCase() === "automatic" && svc.autodelay) startupType.value = "autodelay";
      else startupType.value = svc.start_type.toLowerCase();
      showServiceDetailModal.value = true;
    }

    function closeServiceDetail() {
      service.value = null;
      startupType.value = false;
      showServiceDetailModal.value = false;
    }

    async function getServices() {
      $q.loading.show({ message: "Loading services..." });
      services.value = await getAgentServices(props.agent_id);
      $q.loading.hide();
    }

    async function sendServiceAction(service, action) {
      let msg, status;
      switch (action) {
        case "start":
          msg = "Starting";
          status = "started";
          break;
        case "stop":
          msg = "Stopping";
          status = "stopped";
          break;
        case "restart":
          msg = "Restarting";
          status = "restarted";
          break;
        default:
          msg = "error";
      }
      $q.loading.show({ message: `${msg} service ${service.display_name}` });
      const data = {
        sv_action: action,
      };

      try {
        modalLoading.value = true;
        await sendAgentServiceAction(props.agent_id, service.name, data);
        getServices();
        notifySuccess(`Service ${service.display_name} was ${status}!`);
      } catch (e) {
        console.error(e);
      }
      modalLoading.value = false;
      $q.loading.hide();
    }

    async function editServiceStartup() {
      const data = {
        startType: startupType.value === "automatic" ? "auto" : startupType.value,
      };

      console.log(data);

      try {
        modalLoading.value = true;
        await editAgentServiceStartType(props.agent_id, service.value.name, data);
        notifySuccess(`Service ${service.value.name} was edited!`);
        getServices();
        closeServiceDetail();
      } catch (e) {
        console.error(e);
      }
      modalLoading.value = false;
    }

    // vue lifecycle hooks
    onMounted(getServices);

    return {
      // reactive data
      services,
      service,
      filter,
      pagination,
      startupType,
      modalLoading,
      startupTypeEdited,

      // dialogs
      showServiceDetailModal,
      showServiceDetail,
      closeServiceDetail,

      // non-reactive data
      columns,
      startupOptions,

      // methods
      getServices,
      sendServiceAction,
      editServiceStartup,
      truncateText,
    };
  },
};
</script>