<template>
  <q-card style="width: 90vw" >
    <q-card-section class="row items-center">
      <div class="text-h6">{{ this.description }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section>
      <q-table
        dense
        class="tabs-tbl-sticky"
        :data="tableData"
        :columns="columns"
        row-key="id"
        binary-state-sort
        :pagination.sync="pagination"
        hide-bottom
      >
        <!-- header slots -->
        <template v-slot:header-cell-statusicon="props">
          <q-th auto-width :props="props"></q-th>
        </template>
        <!-- body slots -->
        <template v-slot:body="props" :props="props">
          <q-tr>
            <!-- tds -->
            <q-td>{{ props.row.hostname }}</q-td>
            <!-- status icon -->
            <q-td v-if="props.row.status === 'pending'"></q-td>
            <q-td v-else-if="props.row.status === 'passing'">
              <q-icon style="font-size: 1.3rem;" color="positive" name="check_circle" />
            </q-td>
            <q-td v-else-if="props.row.status === 'failing'">
              <q-icon style="font-size: 1.3rem;" color="negative" name="error" />
            </q-td>
            <!-- status text -->
            <q-td v-if="props.row.status === 'pending'">Awaiting First Synchronization</q-td>
            <q-td v-else-if="props.row.status === 'passing'">
              <q-badge color="positive">Passing</q-badge>
            </q-td>
            <q-td v-else-if="props.row.status === 'failing'">
              <q-badge color="negative">Failing</q-badge>
            </q-td>
            <!-- more info -->
            <q-td v-if="props.row.check_type === 'ping'">
              <span
                style="cursor:pointer;color:blue;text-decoration:underline"
                @click="pingInfo(props.row.readable_desc, props.row.more_info)"
              >output</span>
            </q-td>
            <q-td v-else-if="props.row.check_type === 'script'">
              <span
                style="cursor:pointer;color:blue;text-decoration:underline"
                @click="scriptMoreInfo(props.row)"
              >output</span>
            </q-td>
            <q-td v-else-if="props.row.check_type === 'eventlog'">
              <span
                style="cursor:pointer;color:blue;text-decoration:underline"
                @click="eventLogMoreInfo(props.row)"
              >output</span>
            </q-td>
            <q-td
              v-else-if="props.row.check_type === 'cpuload' || props.row.check_type === 'memory'"
            >{{ props.row.history_info }}</q-td>
            <q-td v-else>{{ props.row.more_info }}</q-td>
            <!-- last run -->
            <q-td>{{ props.row.last_run }}</q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card-section>

    <q-dialog v-model="showScriptOutput" @hide="closeScriptOutput">
      <ScriptOutput @close="closeScriptOutput" :scriptInfo="scriptInfo" />
    </q-dialog>
    <q-dialog v-model="showEventLogOutput" @hide="closeEventLogOutput">
      <EventLogCheckOutput
        @close="closeEventLogOutput"
        :evtlogdata="evtLogData"
      />
    </q-dialog>
  </q-card>
</template>

<script>
import { mapGetters } from "vuex";
import ScriptOutput from "@/components/modals/checks/ScriptOutput";
import EventLogCheckOutput from "@/components/modals/checks/EventLogCheckOutput";

export default {
  name: "PolicyStatus",
  components: {
    ScriptOutput,
    EventLogCheckOutput
  },
  props: {
    item: {
      required: true,
      type: Object
    },
    type: {
      required: true,
      type: String,
      validator: function (value) {
        // The value must match one of these strings
        return ["task", "check"].includes(value);
      }
    },
    description: {
      type: String
    }
  },
  data() {
    return {
      showScriptOutput: false,
      showEventLogOutput: false,
      evtLogData: {},
      scriptInfo: {},
      tableData: [],
      columns: [
        { name: "agent", label: "Hostname", field: "agent", align: "left" },
        { name: "statusicon", align: "left" },
        { name: "status", label: "Status", field: "status", align: "left" },
        {
          name: "moreinfo",
          label: "More Info",
          field: "more_info",
          align: "left"
        },
        {
          name: "datetime",
          label: "Date / Time",
          field: "last_run",
          align: "left"
        }
      ],
      pagination: {
        rowsPerPage: 9999
      }
    }
  },
  methods: {
    getCheckData() {
      this.$q.loading.show();
      this.$store
        .dispatch("automation/loadCheckStatus", { policypk: this.item.policy, checkpk: this.item.id })
        .then(r => {
          this.$q.loading.hide();
          this.tableData = r.data
        })
        .catch(e => {
          this.$q.loading.hide();
          // TODO: Return Error message from api and display
        });
    },
    getTaskData() {
      this.$q.loading.show();
      this.$store
        .dispatch("automation/loadAutomatedTaskStatus", { policypk: this.item.policy, taskpk: this.item.id })
        .then(r => {
          this.$q.loading.hide();
          this.tableData = r.data
        })
        .catch(e => {
          this.$q.loading.hide();
          // TODO: Return Error message from api and display
        });;
    },
    closeEventLogOutput() {
      this.showEventLogOutput = false; 
      this.evtLogdata = {};
    },
    closeScriptOutput() {
      this.showScriptOutput = false; 
      this.scriptInfo = {}
    }
  },
  mounted() {
    if (this.type === "task") {
      this.getTaskData();
    } 
    else {
      this.getCheckData();
    } 

  }
}
</script>
