<template>
  <div class="q-pa-md">
    <div class="row">
      <div class="col-2">
        <q-select dense options-dense outlined v-model="days" :options="lastDaysOptions" :label="showDays" />
      </div>
      <div class="col-7"></div>
      <div class="col-3">
        <code>{{ logType }} log total records: {{ events.length }}</code>
      </div>
    </div>
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="remote-bg-tbl-sticky"
      :rows="events"
      :columns="columns"
      v-model:pagination="pagination"
      :filter="filter"
      row-key="uid"
      binary-state-sort
      hide-bottom
      virtual-scroll
    >
      <template v-slot:top>
        <q-btn dense flat push @click="getEventLog" icon="refresh" />
        <q-space />
        <q-radio
          v-model="logType"
          color="cyan"
          val="Application"
          label="Application"
          @update:model-value="getEventLog"
        />
        <q-radio v-model="logType" color="cyan" val="System" label="System" />
        <q-radio v-model="logType" color="cyan" val="Security" label="Security" />
        <q-space />
        <q-input v-model="filter" outlined label="Search" dense clearable>
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>
      <template v-slot:body="props">
        <q-tr :props="props">
          <q-td>{{ props.row.eventType }}</q-td>
          <q-td>{{ props.row.source }}</q-td>
          <q-td>{{ props.row.eventID }}</q-td>
          <q-td>{{ props.row.time }}</q-td>
          <q-td @click="showEventMessage(props.row.message)">
            <span style="cursor: pointer; text-decoration: underline" class="text-primary">{{
              truncateText(props.row.message, 30)
            }}</span>
          </q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
// compisition imports
import { ref, computed, watch, onMounted } from "vue";
import { useQuasar } from "quasar";
import { fetchAgentEventLog } from "@/api/agents";
import { truncateText } from "@/utils/format";

// static data
const columns = [
  { name: "eventType", label: "Type", field: "eventType", align: "left", sortable: true },
  { name: "source", label: "Source", field: "source", align: "left", sortable: true },
  { name: "eventID", label: "Event ID", field: "eventID", align: "left", sortable: true },
  { name: "time", label: "Time", field: "time", align: "left", sortable: true },
  { name: "message", label: "Message (click to view full)", field: "message", align: "left", sortable: true },
];

const lastDaysOptions = [1, 2, 3, 4, 5, 10, 30, 60, 90, 180, 360, 9999];

export default {
  name: "EventLogManager",
  props: {
    agent_id: !String,
  },
  setup(props) {
    // quasar setup
    const $q = useQuasar();

    // eventlog manager
    const events = ref([]);
    const logType = ref("Application");
    const days = ref(1);
    const filter = ref("");
    const pagination = ref({
      rowsPerPage: 0,
      sortBy: "record",
      descending: true,
    });

    const showDays = computed(() => `Show last ${days.value} days`);

    watch([logType, days], getEventLog);

    async function getEventLog() {
      $q.loading.show({ message: `Loading ${logType.value} event log...please wait` });
      events.value = await fetchAgentEventLog(props.agent_id, logType.value, days.value);
      $q.loading.hide();
    }

    function showEventMessage(message) {
      $q.dialog({
        message: `<pre>${message}</pre>`,
        html: true,
        fullWidth: true,
      });
    }

    // vue lifecycle hooks
    onMounted(getEventLog);

    return {
      // reactive data
      events,
      logType,
      days,
      filter,
      pagination,
      showDays,

      // non-reactive data
      columns,
      lastDaysOptions,

      // methods
      getEventLog,
      showEventMessage,
      truncateText,
    };
  },
};
</script>