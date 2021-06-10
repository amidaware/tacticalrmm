<template>
  <q-card>
    <q-bar>
      <q-btn @click="search" class="q-mr-sm" dense flat push icon="refresh" />
      <q-space />Audit Manager
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <div class="text-h6 q-pl-sm q-pt-sm">Filter</div>
    <div class="row">
      <div class="q-pa-sm col-1">
        <q-option-group v-model="filterType" :options="filterTypeOptions" color="primary" @update:model-value="clear" />
      </div>
      <div class="q-pa-sm col-2" v-if="filterType === 'agents'">
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
          <template v-slot:option="scope">
            <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
              <q-item-section>
                <q-item-label v-html="scope.opt.label"></q-item-label>
              </q-item-section>
            </q-item>
            <q-item-label v-if="scope.opt.category" v-bind="scope.itemProps" header class="q-pa-sm">{{
              scope.opt.category
            }}</q-item-label>
          </template>
        </q-select>
      </div>
      <div class="q-pa-sm col-2" v-if="filterType === 'clients'">
        <q-select
          clearable
          multiple
          filled
          dense
          v-model="clientFilter"
          fill-input
          label="Clients"
          map-options
          emit-value
          :options="clientsOptions"
        />
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
        <q-select
          clearable
          filled
          multiple
          use-chips
          dense
          v-model="actionFilter"
          label="Action"
          emit-value
          map-options
          :options="actionOptions"
        />
      </div>
      <div class="q-pa-sm col-2">
        <q-select
          clearable
          filled
          multiple
          use-chips
          dense
          v-model="objectFilter"
          label="Object"
          emit-value
          map-options
          :options="objectOptions"
        />
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
        @request="onRequest"
        dense
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="audit-mgr-tbl-sticky"
        binary-state-sort
        title="Audit Logs"
        :rows="auditLogs"
        :columns="columns"
        row-key="id"
        v-model:pagination="pagination"
        :rows-per-page-options="[25, 50, 100, 500, 1000]"
        :no-data-label="noDataText"
        @row-click="showDetails"
        virtual-scroll
      >
        <template v-slot:top-right>
          <q-btn color="primary" icon-right="archive" label="Export to csv" no-caps @click="exportLog" />
        </template>
        <template v-slot:body-cell-action="props">
          <q-td :props="props">
            <div>
              <q-badge :color="actionColor(props.value)" :label="actionText(props.value)" />
            </div>
          </q-td>
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
import { formatAgentOptions } from "@/utils/format";

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
      agentFilter: null,
      userFilter: [],
      actionFilter: null,
      clientsOptions: [],
      clientFilter: null,
      objectFilter: null,
      timeFilter: 7,
      filterType: "clients",
      filterTypeOptions: [
        {
          label: "Clients",
          value: "clients",
        },
        {
          label: "Agents",
          value: "agents",
        },
      ],
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
        {
          name: "object_type",
          label: "Object",
          field: "object_type",
          align: "left",
          sortable: true,
          format: (val, row) => this.formatObject(val),
        },
        { name: "message", label: "Message", field: "message", align: "left", sortable: true },
      ],
      actionOptions: [
        { value: "agent_install", label: "Agent Installs" },
        { value: "add", label: "Add Object" },
        { value: "bulk_action", label: "Bulk Actions" },
        { value: "check_run", label: "Check Run Results" },
        { value: "execute_command", label: "Execute Command" },
        { value: "execute_script", label: "Execute Script" },
        { value: "delete", label: "Delete Object" },
        { value: "failed_login", label: "Failed User login" },
        { value: "login", label: "User Login" },
        { value: "modify", label: "Modify Object" },
        { value: "remote_session", label: "Remote Session" },
        { value: "task_run", label: "Task Run Results" },
      ],
      timeOptions: [
        { value: 1, label: "1 Day Ago" },
        { value: 7, label: "1 Week Ago" },
        { value: 30, label: "30 Days Ago" },
        { value: 90, label: "3 Months Ago" },
        { value: 180, label: "6 Months Ago" },
        { value: 365, label: "1 Year Ago" },
        { value: 0, label: "Everything" },
      ],
      objectOptions: [
        { value: "agent", label: "Agent" },
        { value: "automatedtask", label: "Automated Task" },
        { value: "bulk", label: "Bulk Actions" },
        { value: "coresettings", label: "Core Settings" },
        { value: "check", label: "Check" },
        { value: "client", label: "Client" },
        { value: "policy", label: "Policy" },
        { value: "site", label: "Site" },
        { value: "script", label: "Script" },
        { value: "user", label: "User" },
        { value: "winupdatepolicy", label: "Patch Policy" },
      ],
      pagination: {
        rowsPerPage: 25,
        rowsNumber: null,
        sortBy: "entry_time",
        descending: true,
        page: 1,
      },
    };
  },
  methods: {
    getClients() {
      this.$axios
        .get("/clients/clients/")
        .then(r => {
          this.clientsOptions = Object.freeze(r.data.map(client => ({ label: client.name, value: client.id })));
        })
        .catch(e => {});
    },
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

        this.$axios
          .post(`logs/auditlogs/optionsfilter/`, data)
          .then(r => {
            this.userOptions = Object.freeze(r.data.map(user => user.username));
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
            this.agentOptions = Object.freeze(formatAgentOptions(r.data));
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
    onRequest(props) {
      // needed to update external pagination object
      const { page, rowsPerPage, sortBy, descending } = props.pagination;

      this.pagination.page = page;
      this.pagination.rowsPerPage = rowsPerPage;
      this.pagination.sortBy = sortBy;
      this.pagination.descending = descending;

      this.search();
    },
    search() {
      this.$q.loading.show();
      this.searched = true;
      let data = {
        pagination: this.pagination,
      };

      if (!!this.agentFilter && this.agentFilter.length > 0) data["agentFilter"] = this.agentFilter;
      else if (!!this.clientFilter && this.clientFilter.length > 0) data["clientFilter"] = this.clientFilter;
      if (!!this.userFilter && this.userFilter.length > 0) data["userFilter"] = this.userFilter;
      if (!!this.timeFilter) data["timeFilter"] = this.timeFilter;
      if (!!this.actionFilter && this.actionFilter.length > 0) data["actionFilter"] = this.actionFilter;
      if (!!this.objectFilter && this.objectFilter.length > 0) data["objectFilter"] = this.objectFilter;

      this.$axios
        .patch("/logs/auditlogs/", data)
        .then(r => {
          this.$q.loading.hide();
          this.auditLogs = Object.freeze(r.data.audit_logs);
          this.pagination.rowsNumber = r.data.total;
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
    actionColor(action) {
      if (action === "add") return "success";
      else if (action === "agent_install") return "success";
      else if (action === "modify") return "warning";
      else if (action === "delete") return "negative";
      else if (action === "failed_login") return "negative";
      else return "primary";
    },
    actionText(action) {
      if (action.includes("_")) {
        let text = action.split("_");
        return this.capitalize(text[0]) + " " + this.capitalize(text[1]);
      } else {
        return this.capitalize(action);
      }
    },
    formatObject(text) {
      if (text === "winupdatepolicy") return "Patch Policy";
      else if (text === "automatedtask") return "Automated Task";
      else if (text === "coresettings") return "Core Settings";
      else return this.capitalize(text);
    },
    clear() {
      this.clientFilter = null;
      this.agentFilter = null;
    },
  },
  computed: {
    noDataText() {
      return this.searched ? "No data found. Try to refine you search" : "Click search to find audit logs";
    },
  },
  mounted() {
    this.getClients();
  },
};
</script>