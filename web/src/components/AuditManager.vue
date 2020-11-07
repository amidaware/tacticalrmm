<template>
  <q-card>
    <q-bar>
      <q-btn @click="search" class="q-mr-sm" dense flat push icon="refresh" />
      <q-space />Audit Manager
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <div class="text-h6 q-pl-sm q-pt-sm">Filter Results</div>
    <div class="row">
      <div class="q-pa-sm col-2">
        <q-select
          new-value-mode="add"
          multiple
          filled
          dense
          v-model="agentFilter"
          use-input
          use-chips
          fill-input
          input-debounce="3"
          label="Agent"
          emit-value
          :options="agentOptions"
          @filter="getAgentOptions"
          hint="Start typing the agents name"
        >
          <template v-slot:no-option>
            <q-item>
              <q-item-section class="text-grey">No results</q-item-section>
            </q-item>
          </template>
        </q-select>
      </div>
      <div class="q-pa-sm col-2">
        <q-select
          new-value-mode="add"
          multiple
          filled
          dense
          v-model="userFilter"
          use-input
          use-chips
          fill-input
          input-debounce="3"
          label="User"
          emit-value
          :options="userOptions"
          @filter="getUserOptions"
          hint="Start typing the username"
        >
          <template v-slot:no-option>
            <q-item>
              <q-item-section class="text-grey">No results</q-item-section>
            </q-item>
          </template>
        </q-select>
      </div>
      <div class="q-pa-sm col-2">
        <q-select filled dense v-model="timeFilter" label="Time" emit-value map-options :options="timeOptions">
          <template v-slot:no-option>
            <q-item>
              <q-item-section class="text-grey">No results</q-item-section>
            </q-item>
          </template>
        </q-select>
      </div>
      <div class="q-pa-sm col-1">
        <q-btn color="primary" label="Search" @click="search" />
      </div>
    </div>
    <q-separator />
    <q-card-section>
      <q-table
        dense
        class="audit-mgr-tbl-sticky"
        binary-state-sort
        virtual-scroll
        title="Audit Logs"
        :data="auditLogs"
        :columns="columns"
        row-key="id"
        :pagination.sync="pagination"
        :no-data-label="noDataText"
        @row-click="showDetails"
      >
        <template v-slot:top-right>
          <q-btn color="primary" icon-right="archive" label="Export to csv" no-caps @click="exportLog" />
        </template>
      </q-table>
    </q-card-section>
    <div class="q-pa-md q-gutter-sm">
      <q-dialog v-model="showLogDetails" @hide="closeDetails">
        <AuditLogDetail :log="logDetails" />
      </q-dialog>
    </div>
  </q-card>
</template>

<script>
import AuditLogDetail from "@/components/modals/logs/AuditLogDetail";
import mixins from "@/mixins/mixins";
import { exportFile } from "quasar";

function wrapCsvValue(val, formatFn) {
  let formatted = formatFn !== void 0 ? formatFn(val) : val;

  formatted = formatted === void 0 || formatted === null ? "" : String(formatted);

  formatted = formatted.split('"').join('""');
  /**
   * Excel accepts \n and \r in strings, but some other CSV parsers do not
   * Uncomment the next two lines to escape new lines
   */
  // .split('\n').join('\\n')
  // .split('\r').join('\\r')

  return `"${formatted}"`;
}

export default {
  name: "AuditManager",
  mixins: [mixins],
  components: { AuditLogDetail },
  data() {
    return {
      showLogDetails: false,
      logDetails: null,
      searched: false,
      auditLogs: [],
      userOptions: [],
      agentOptions: [],
      agentFilter: [],
      userFilter: [],
      timeFilter: 30,
      columns: [
        {
          name: "entry_time",
          label: "Time",
          field: "entry_time",
          align: "left",
          sortable: true,
          format: (val, row) => this.formatDate(val, true),
        },
        { name: "username", label: "Username", field: "username", align: "left", sortable: true },
        { name: "agent", label: "Agent", field: "agent", align: "left", sortable: true },
        { name: "action", label: "Action", field: "action", align: "left", sortable: true },
        { name: "object_type", label: "Object", field: "object_type", align: "left", sortable: true },
        { name: "message", label: "Message", field: "message", align: "left", sortable: true },
      ],
      timeOptions: [
        { value: 1, label: "1 Day Ago" },
        { value: 7, label: "1 Week Ago" },
        { value: 30, label: "30 Days Ago" },
        { value: 180, label: "6 Months Ago" },
        { value: 365, label: "1 Year Ago" },
        { value: 0, label: "Everything" },
      ],
      pagination: {
        rowsPerPage: 50,
        sortBy: "entry_time",
        descending: true,
      },
    };
  },
  methods: {
    getUserOptions(val, update, abort) {
      if (val.length < 2) {
        abort();
        return;
      }

      update(() => {
        this.$q.loading.show();

        const needle = val.toLowerCase();

        let data = {
          type: "user",
          pattern: needle,
        };

        this.$store
          .dispatch("logs/optionsFilter", data)
          .then(r => {
            this.userOptions = r.data.map(user => user.username);
            this.$q.loading.hide();
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      });
    },
    getAgentOptions(val, update, abort) {
      if (val.length < 2) {
        abort();
        return;
      }

      update(() => {
        this.$q.loading.show();

        const needle = val.toLowerCase();

        let data = {
          type: "agent",
          pattern: needle,
        };

        this.$axios
          .post(`logs/auditlogs/optionsfilter/`, data)
          .then(r => {
            this.agentOptions = r.data.map(agent => agent.hostname);
            this.$q.loading.hide();
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      });
    },
    exportLog() {
      // naive encoding to csv format
      const content = [this.columns.map(col => wrapCsvValue(col.label))]
        .concat(
          this.auditLogs.map(row =>
            this.columns
              .map(col =>
                wrapCsvValue(
                  typeof col.field === "function" ? col.field(row) : row[col.field === void 0 ? col.name : col.field],
                  col.format
                )
              )
              .join(",")
          )
        )
        .join("\r\n");

      const status = exportFile("rmm-audit-export.csv", content, "text/csv");

      if (status !== true) {
        this.$q.notify({
          message: "Browser denied file download...",
          color: "negative",
          icon: "warning",
        });
      }
    },
    search() {
      this.$q.loading.show();
      this.searched = true;
      let data = {};

      if (this.agentFilter.length > 0) {
        data["agentFilter"] = this.agentFilter;
      }

      if (this.userFilter.length > 0) {
        data["userFilter"] = this.userFilter;
      }

      if (this.timeFilter) {
        data["timeFilter"] = this.timeFilter;
      }

      this.$axios
        .patch("/logs/auditlogs/", data)
        .then(r => {
          this.$q.loading.hide();
          this.auditLogs = r.data;
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    showDetails(evt, row, index) {
      this.logDetails = row;
      this.showLogDetails = true;
    },
    closeDetails() {
      this.logDetails = null;
      this.showLogDetails = false;
    },
  },
  computed: {
    noDataText() {
      return this.searched ? "No data found. Try to refine you search" : "Click search to find audit logs";
    },
  },
};
</script>