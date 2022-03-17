<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else>
    <q-table
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      :rows="history"
      :columns="columns"
      :pagination="{ sortBy: 'time', descending: true, rowsPerPage: 0 }"
      :style="{ 'max-height': tabHeight }"
      :loading="loading"
      :rows-per-page-options="[0]"
      :filter="filter"
      virtual-scroll
      dense
      binary-state-sort
    >
      <template v-slot:top>
        <q-btn dense flat push @click="getHistory" icon="refresh" />
        <q-space />
        <q-input v-model="filter" outlined label="Search" dense clearable class="q-pr-sm">
          <template v-slot:prepend>
            <q-icon name="search" color="primary" />
          </template>
        </q-input>
        <export-table-btn :data="history" :columns="columns" />
      </template>

      <template v-slot:loading>
        <q-inner-loading showing color="primary" />
      </template>

      <template v-slot:body-cell-command="props">
        <q-td :props="props">
          <span v-if="props.row.type === 'script_run' || props.row.type === 'task_run'">{{
            props.row.script_name
          }}</span>
          <span v-else-if="props.row.type === 'cmd_run'"
            >{{ truncateText(props.row.command, 30) }}
            <q-tooltip v-if="props.row.command.length >= 30" style="font-size: 12px">
              {{ props.row.command }}
            </q-tooltip>
          </span>
        </q-td>
      </template>

      <template v-slot:body-cell-output="props">
        <q-td :props="props">
          <span
            style="cursor: pointer; text-decoration: underline"
            class="text-primary"
            @click="
              props.row.type === 'cmd_run'
                ? showCommandOutput(props.row.results)
                : showScriptOutput(props.row.script_results)
            "
            >Output
          </span>
        </q-td>
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { useQuasar } from "quasar";
import { formatDate, formatTableColumnText, truncateText, dateStringToUnix } from "@/utils/format";
import { fetchAgentHistory } from "@/api/agents";

// ui imports
import ScriptOutput from "@/components/checks/ScriptOutput";
import ExportTableBtn from "@/components/ui/ExportTableBtn";

// static data
const columns = [
  {
    name: "time",
    label: "Time",
    field: "time",
    align: "left",
    sortable: true,
    sort: (a, b, rowA, rowB) => dateStringToUnix(a) - dateStringToUnix(b),
    format: (val, row) => formatDate(val, true),
  },
  {
    name: "type",
    label: "Action",
    field: "type",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  },
  /* {
    name: "status",
    label: "Status",
    field: "status",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  }, */
  {
    name: "command",
    label: "Script/Command",
    field: "command",
    align: "left",
    sort: (a, b, rowa, rowb) => {
      let tmp1 = rowa.type === "script_run" || rowa.type === "task_run" ? rowa.script_name : a;
      let tmp2 = rowb.type === "script_run" || rowb.type === "task_run" ? rowb.script_name : b;
      return tmp1.localeCompare(tmp2);
    },
    sortable: true,
  },
  { name: "username", label: "Initiated By", field: "username", align: "left", sortable: true },
  { name: "output", label: "Output", field: "output", align: "left", sortable: true },
];

export default {
  name: "HistoryTab",
  components: {
    ExportTableBtn,
  },
  setup() {
    const $q = useQuasar();

    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const tabHeight = computed(() => store.state.tabHeight);

    // setup main history functionality
    const history = ref([]);
    const loading = ref(false);
    const filter = ref("");

    async function getHistory() {
      loading.value = true;
      history.value = await fetchAgentHistory(selectedAgent.value);
      loading.value = false;
    }

    watch(selectedAgent, (newValue, oldValue) => {
      if (newValue) {
        getHistory();
      }
    });

    // quasar dialogs
    function showScriptOutput(output) {
      $q.dialog({
        component: ScriptOutput,
        componentProps: {
          scriptInfo: output,
        },
      });
    }

    function showCommandOutput(output) {
      $q.dialog({
        style: "width: 70vw; max-width: 80vw",
        message: `<pre>${output}</pre>`,
        html: true,
      });
    }

    // vue component hooks
    onMounted(() => {
      if (selectedAgent.value) getHistory();
    });

    return {
      // reactive
      history,
      loading,
      tabHeight,
      filter,

      // non-reactive data
      columns,

      // methods
      showScriptOutput,
      showCommandOutput,
      getHistory,
      truncateText,

      // computed
      selectedAgent,
    };
  },
};
</script>