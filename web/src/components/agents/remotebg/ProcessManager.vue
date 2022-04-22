<template>
  <q-table
    dense
    :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
    class="remote-bg-tbl-sticky"
    :style="{ 'max-height': `${$q.screen.height - 36}px` }"
    :rows="processes"
    :columns="columns"
    :pagination="{ rowsPerPage: 0, sortBy: 'cpu_percent', descending: true }"
    :filter="filter"
    row-key="id"
    binary-state-sort
    :rows-per-page-options="[0]"
    :loading="loading"
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
      <!-- file download doesn't work so disabling -->
      <export-table-btn v-show="false" class="q-ml-sm" :columns="columns" :data="processes" />
    </template>
    <template v-slot:body="props">
      <q-tr :props="props" class="cursor-pointer">
        <q-menu context-menu auto-close>
          <q-list dense style="min-width: 200px">
            <q-item clickable @click="killProcess(props.row.pid, props.row.name)">
              <q-item-section side>
                <q-icon name="fas fa-trash-alt" size="xs" />
              </q-item-section>
              <q-item-section>End Process</q-item-section>
            </q-item>
            <q-separator />
            <q-item clickable>
              <q-item-section>Close</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
        <q-td>{{ props.row.name }}</q-td>
        <q-td>{{ props.row.cpu_percent }}%</q-td>
        <q-td>{{ bytes2Human(props.row.membytes) }}</q-td>
        <q-td>{{ props.row.username }}</q-td>
        <q-td>{{ props.row.pid }}</q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { fetchAgent, fetchAgentProcesses, killAgentProcess } from "@/api/agents";
import { bytes2Human } from "@/utils/format";
import { notifySuccess } from "@/utils/notify";

// ui imports
import ExportTableBtn from "@/components/ui/ExportTableBtn.vue";

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
    sort: (a, b, rowA, rowB) => parseFloat(b) < parseFloat(a),
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
];

export default {
  components: { ExportTableBtn },
  name: "ProcessManager",
  props: {
    agent_id: !String,
  },
  setup(props) {
    // polling setup
    const pollInterval = ref(2);
    const poll = ref(null);
    const isPolling = computed(() => !!poll.value);

    async function startPoll() {
      await getProcesses();
      if (processes.value.length > 0) {
        refreshProcesses();
      }
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

    const loading = ref(false);

    async function getProcesses() {
      loading.value = true;
      processes.value = await fetchAgentProcesses(props.agent_id);
      loading.value = false;
    }

    function refreshProcesses() {
      poll.value = setInterval(() => {
        getProcesses(props.agent_id);
      }, pollInterval.value * 1000);
    }

    async function killProcess(pid, name) {
      loading.value = true;
      let result = "";
      try {
        result = await killAgentProcess(props.agent_id, pid);
        notifySuccess(result);
      } catch (e) {
        console.error(error);
      }
      loading.value = false;
    }

    // lifecycle hooks
    onMounted(async () => {
      memory.value = await fetchAgent(props.agent_id).total_ram;
      await getProcesses();
      if (processes.value.length > 0) {
        refreshProcesses();
      }
    });

    onBeforeUnmount(() => clearInterval(poll.value));

    return {
      // reactive data
      processes,
      filter,
      memory,
      isPolling,
      pollInterval,
      loading,

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