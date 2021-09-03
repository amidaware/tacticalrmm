<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else>
    <q-table
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      :rows="history"
      :columns="columns"
      :pagination="{ sortBy: 'time', descending: true, rowsPerPage: 10 }"
      :loading="loading"
      dense
      binary-state-sort
    >
      <template v-slot:top-left>
        <q-btn dense flat push @click="getHistory" icon="refresh" />
      </template>

      <template v-slot:top-right>
        <export-table-btn :data="history" :columns="columns" />
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
            v-if="props.row.type === 'script_run' || props.row.type === 'task_run'"
            style="cursor: pointer; text-decoration: underline"
            class="text-primary"
            @click="showScriptOutput(props.row.script_results)"
            >Output
          </span>
          <span v-else-if="props.row.type === 'cmd_run'"
            >{{ truncateText(props.row.results, 30) }}
            <q-tooltip v-if="props.row.results !== null && props.row.results.length >= 30" style="font-size: 12px">
              {{ props.row.results }}
            </q-tooltip>
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
import { formatDate, formatTableColumnText, truncateText } from "@/utils/format";
import { fetchAgentHistory } from "@/api/agents";

// ui imports
import ScriptOutput from "@/components/modals/checks/ScriptOutput";
import ExportTableBtn from "@/components/ui/ExportTableBtn";

// static data
const columns = [
  {
    name: "time",
    label: "Time",
    field: "time",
    align: "left",
    sortable: true,
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
  { name: "command", label: "Script/Command", field: "command", align: "left", sortable: true },
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

    // setup main history functionality
    const history = ref([]);
    const loading = ref(false);

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

    // vue component hooks
    onMounted(() => {
      if (!!selectedAgent.value) getHistory();
    });

    return {
      // reactive
      history,
      loading,

      // non-reactive data
      columns,

      // methods
      showScriptOutput,
      getHistory,
      truncateText,

      // computed
      selectedAgent,
    };
  },
};
</script>