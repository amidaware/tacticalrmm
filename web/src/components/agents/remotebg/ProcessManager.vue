<template>
  <div class="q-pa-md">
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="remote-bg-tbl-sticky"
      :rows="processes"
      :columns="columns"
      v-model:pagination="pagination"
      :filter="filter"
      row-key="id"
      binary-state-sort
      hide-bottom
    >
      <template v-slot:top>
        <q-btn v-if="isPolling" dense flat push @click="stopPoll" icon="stop" label="Stop Live Refresh" />
        <q-btn v-else dense flat push @click="startPoll" icon="play_arrow" label="Resume Live Refresh" />

        <q-space />

        <div class="q-pa-md q-gutter-sm">
          <q-btn
            :disable="pollInterval === 1"
            dense
            @click="pollIntervalChanged('subtract')"
            push
            icon="remove"
            size="sm"
            color="grey"
          />
          <q-btn dense push icon="add" size="sm" color="grey" @click="pollIntervalChanged('add')" />
        </div>
        <div class="text-overline">
          <q-badge align="middle" size="sm" class="text-h6" color="blue" :label="pollInterval" />
          Refresh interval (seconds)
        </div>

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
              <q-item clickable v-close-popup @click="killProcess(props.row.pid, props.row.name)">
                <q-item-section thumbnail>
                  <q-icon name="fas fa-trash-alt" size="xs" />
                </q-item-section>
                <q-item-section>End task</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <q-td>{{ props.row.name }}</q-td>
          <q-td>{{ props.row.cpu_percent }}%</q-td>
          <q-td>{{ bytes2Human(props.row.membytes) }}</q-td>
          <q-td>{{ props.row.username }}</q-td>
          <q-td>{{ props.row.pid }}</q-td>
          <q-td>{{ props.row.status }}</q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useQuasar } from "quasar";
import { fetchAgent, fetchAgentProcesses, killAgentProcess } from "@/api/agents";
import { bytes2Human } from "@/utils/format";
import { notifySuccess } from "@/utils/notify";

const columns = [
  {
    name: "name",
    label: "Name",
    field: "name",
    align: "left",
    sortable: true,
  },
  {
    name: "cpu_percent",
    label: "CPU",
    field: "cpu_percent",
    align: "left",
    sortable: true,
    sort: (a, b, rowA, rowB) => parseInt(b) < parseInt(a),
  },
  {
    name: "membytes",
    label: "Memory",
    field: "membytes",
    align: "left",
    sortable: true,
  },
  {
    name: "username",
    label: "User",
    field: "username",
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
];

export default {
  name: "ProcessManager",
  props: {
    agent_id: !String,
  },
  setup(props) {
    // setup quasar
    const $q = useQuasar();

    // polling setup
    const pollInterval = ref(2);
    const poll = ref(null);
    const isPolling = computed(() => !!poll.value);

    function startPoll() {
      getProcesses();
      refreshProcesses();
    }

    function stopPoll() {
      clearInterval(poll.value);
      poll.value = null;
    }

    function pollIntervalChanged(action) {
      if (action === "subtract" && pollInterval.value <= 1) {
        stopPoll();
        startPoll();
        return;
      }
      if (action === "add") {
        pollInterval.value++;
      } else {
        pollInterval.value--;
      }
      stopPoll();
      startPoll();
    }

    // process manager logic
    const processes = ref([]);
    const filter = ref("");
    const memory = ref(null);

    async function getProcesses() {
      $q.loading.show({ message: "Loading Processes..." });
      processes.value = await fetchAgentProcesses(props.agent_id);
      $q.loading.hide();
    }

    function refreshProcesses() {
      poll.value = setInterval(() => {
        getProcesses(props.agent_id);
      }, pollInterval.value * 1000);
    }

    async function killProcess(pid, name) {
      $q.loading.show({ message: `Attempting to kill process ${name}` });
      let result = "";
      try {
        result = await killAgentProcess(props.agent_id, pid);
        notifySuccess(result);
      } catch (e) {
        console.log(error);
      }
      $q.loading.hide();
    }

    // table setup
    const pagination = ref({
      rowsPerPage: 99999,
      sortBy: "cpu_percent",
      descending: true,
    });

    // lifecycle hooks
    onMounted(async () => {
      // disable loading bar
      $q.loadingBar.setDefaults({ size: "0px" });

      memory.value = await fetchAgent(props.agent_id).total_ram;
      getProcesses();
      refreshProcesses();
    });

    onBeforeUnmount(() => clearInterval(poll.value));

    return {
      // reactive data
      processes,
      pagination,
      filter,
      memory,
      isPolling,
      pollInterval,

      // non-reactive data
      columns,

      //methods
      getProcesses,
      killProcess,
      startPoll,
      stopPoll,
      pollIntervalChanged,
      bytes2Human,
    };
  },
};
</script>