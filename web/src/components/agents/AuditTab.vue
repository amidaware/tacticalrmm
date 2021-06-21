<template>
  <div v-if="!selectedAgentPk">No agent selected</div>
  <div v-else class="q-pa-none">
    <div class="q-gutter-y-md">
      <q-card>
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
          :rows-per-page-options="[25, 50, 100, 500]"
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
      </q-card>
    </div>
  </div>
</template>

<script>
import { mapGetters } from "vuex";
export default {
  name: "AuditTab",
  data() {
    return {
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
      timeOptions: [
        { value: 1, label: "1 Day Ago" },
        { value: 7, label: "1 Week Ago" },
        { value: 30, label: "30 Days Ago" },
        { value: 90, label: "3 Months Ago" },
        { value: 180, label: "6 Months Ago" },
        { value: 365, label: "1 Year Ago" },
        { value: 0, label: "Everything" },
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
  computed: {
    ...mapGetters(["selectedAgentPk"]),
  },
  methods: {
    onRequest(props) {
      // needed to update external pagination object
      const { page, rowsPerPage, sortBy, descending } = props.pagination;

      this.pagination.page = page;
      this.pagination.rowsPerPage = rowsPerPage;
      this.pagination.sortBy = sortBy;
      this.pagination.descending = descending;

      this.search();
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
  },
};
</script>