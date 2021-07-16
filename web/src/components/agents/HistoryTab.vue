<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else>
    <q-table
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      :rows="history"
      :columns="columns"
      :pagination="{ sortBy: 'entry_time', descending: true }"
      :loading="loading"
      dense
      binary-state-sort
    >
      <template v-slot:top-right>
        <export-table-btn :data="history" :columns="columns" />
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { formatDate, formatTableColumnText } from "@/utils/format";
import { fetchAgentHistory } from "@/api/agents";

// ui imports
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
  {
    name: "status",
    label: "Status",
    field: "status",
    align: "left",
    sortable: true,
    format: (val, row) => formatTableColumnText(val),
  },
  { name: "command", label: "Command", field: "command", align: "left", sortable: true },
  { name: "username", label: "Initiated By", field: "username", align: "left", sortable: true },
  { name: "output", label: "Output", field: "output", align: "left", sortable: true },
];

export default {
  name: "HistoryTab",
  components: {
    ExportTableBtn,
  },
  setup() {
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

      // computed
      selectedAgent,
    };
  },
};
</script>