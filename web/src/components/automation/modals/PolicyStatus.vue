<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 90vw">
      <q-bar>
        {{ title.slice(0, 27) }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <q-table
          style="max-height: 35vh"
          :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
          class="tabs-tbl-sticky"
          :rows="data"
          :columns="columns"
          v-model:pagination="pagination"
          :rows-per-page-options="[0]"
          row-key="id"
          binary-state-sort
          dense
          virtual-scroll
          hide-pagination
          no-data-label="There are no agents in this policy"
        >
          <!-- header slots -->
          <template v-slot:header-cell-statusicon="props">
            <q-th auto-width :props="props"></q-th>
          </template>
          <!-- body slots -->
          <template v-slot:body="props">
            <q-tr :props="props">
              <!-- tds -->
              <!-- agent hostname -->
              <q-td>{{ props.row.hostname }}</q-td>
              <!-- status icon -->
              <q-td v-if="props.row.status === 'passing'">
                <q-icon style="font-size: 1.3rem" color="positive" name="check_circle">
                  <q-tooltip>Passing</q-tooltip>
                </q-icon>
              </q-td>
              <q-td v-else-if="props.row.status === 'failing'">
                <q-icon v-if="props.row.alert_severity === 'info'" style="font-size: 1.3rem" color="info" name="info">
                  <q-tooltip>Informational</q-tooltip>
                </q-icon>
                <q-icon
                  v-else-if="props.row.alert_severity === 'warning'"
                  style="font-size: 1.3rem"
                  color="warning"
                  name="warning"
                >
                  <q-tooltip>Warning</q-tooltip>
                </q-icon>
                <q-icon v-else style="font-size: 1.3rem" color="negative" name="error">
                  <q-tooltip>Error</q-tooltip>
                </q-icon>
              </q-td>
              <q-td v-else></q-td>
              <!-- status text -->
              <q-td v-if="props.row.status === 'pending'">Awaiting First Synchronization</q-td>
              <q-td v-else-if="props.row.sync_status === 'notsynced'">Will sync on next agent checkin</q-td>
              <q-td v-else-if="props.row.sync_status === 'synced'">Synced with agent</q-td>
              <q-td v-else-if="props.row.sync_status === 'pendingdeletion'">Pending deletion on agent</q-td>
              <q-td v-else-if="props.row.sync_status === 'initial'">Waiting for task creation on agent</q-td>
              <q-td v-else></q-td>
              <!-- more info -->
              <q-td v-if="props.row.check_type === 'ping'">
                <span
                  style="cursor: pointer; text-decoration: underline"
                  @click="pingInfo(props.row)"
                  class="ping-cell text-primary"
                  >output</span
                >
              </q-td>
              <q-td
                v-else-if="
                  props.row.check_type === 'script' || props.row.retcode || props.row.stdout || props.row.stderr
                "
              >
                <span
                  style="cursor: pointer; text-decoration: underline"
                  @click="showScriptOutput(props.row)"
                  class="script-cell text-primary"
                  >output</span
                >
              </q-td>
              <q-td v-else-if="props.row.check_type === 'eventlog'">
                <span
                  style="cursor: pointer; text-decoration: underline"
                  @click="showEventInfo(props.row)"
                  class="eventlog-cell text-primary"
                  >output</span
                >
              </q-td>
              <q-td v-else-if="props.row.check_type === 'cpuload' || props.row.check_type === 'memory'">{{
                props.row.history_info
              }}</q-td>
              <q-td v-else-if="props.row.more_info">{{ props.row.more_info }}</q-td>
              <q-td v-else>Awaiting Output</q-td>
              <!-- last run -->
              <q-td>{{ props.row.last_run ? formatDate(props.row.last_run) : "Never" }}</q-td>
            </q-tr>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import { computed } from "vue";
import { useStore } from "vuex";
import ScriptOutput from "@/components/checks/ScriptOutput";
import EventLogCheckOutput from "@/components/checks/EventLogCheckOutput";

export default {
  name: "PolicyStatus",
  emits: ["hide", "ok", "cancel"],
  props: {
    item: {
      required: true,
      type: Object,
    },
    type: {
      required: true,
      type: String,
      validator: function (value) {
        // The value must match one of these strings
        return ["task", "check"].includes(value);
      },
    },
  },
  setup(props) {
    // setup vuex store
    const store = useStore();
    const formatDate = computed(() => store.getters.formatDate);

    return {
      formatDate,
    };
  },
  data() {
    return {
      data: [],
      columns: [
        { name: "agent", label: "Hostname", field: "agent", align: "left", sortable: true },
        { name: "statusicon", align: "left" },
        { name: "status", label: "Status", field: "status", align: "left", sortable: true },
        {
          name: "moreinfo",
          label: "More Info",
          field: "more_info",
          align: "left",
          sortable: true,
        },
        {
          name: "datetime",
          label: "Date / Time",
          field: "last_run",
          align: "left",
          sortable: true,
        },
      ],
      pagination: {
        rowsPerPage: 0,
        sortBy: "status",
        descending: false,
      },
    };
  },
  computed: {
    title() {
      return !!this.item.readable_desc ? this.item.readable_desc + " Status" : this.item.name + " Status";
    },
  },
  methods: {
    getCheckData() {
      this.$q.loading.show();
      this.$axios
        .get(`/automation/checks/${this.item.id}/status/`)
        .then(r => {
          this.$q.loading.hide();
          this.data = r.data;
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    getTaskData() {
      this.$q.loading.show();
      this.$axios
        .get(`/automation/tasks/${this.item.id}/status/`)
        .then(r => {
          this.$q.loading.hide();
          this.data = r.data;
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    pingInfo(check) {
      this.$q.dialog({
        title: check.readable_desc,
        style: "width: 50vw; max-width: 60vw",
        message: `<pre>${check.more_info}</pre>`,
        html: true,
      });
    },
    showEventInfo(data) {
      this.$q.dialog({
        component: EventLogCheckOutput,
        componentProps: {
          evtLogData: data,
        },
      });
    },
    showScriptOutput(script) {
      this.$q.dialog({
        component: ScriptOutput,
        componentProps: {
          scriptInfo: script,
        },
      });
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
  },
  mounted() {
    if (this.type === "task") {
      this.getTaskData();
    } else {
      this.getCheckData();
    }
  },
};
</script>
