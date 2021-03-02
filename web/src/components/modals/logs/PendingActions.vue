<template>
  <q-card style="width: 900px; max-width: 90vw">
    <q-bar>
      <q-btn @click="getPendingActions" class="q-mr-sm" dense flat push icon="refresh" />
      {{ title }}
      <q-space />
      <q-btn dense flat icon="close" v-close-popup />
    </q-bar>
    <div v-if="totalCount !== 0" class="q-pa-md">
      <div class="row">
        <div class="col">
          <q-btn
            label="Cancel Action"
            :disable="selectedRow === null || selectedStatus === 'completed' || actionType !== 'schedreboot'"
            color="red"
            icon="cancel"
            dense
            unelevated
            no-caps
            size="md"
            @click="cancelPendingAction"
          />
        </div>
        <div class="col-7"></div>
        <div class="col">
          <q-btn
            :label="showCompleted ? `Hide ${completedCount} Completed` : `Show ${completedCount} Completed`"
            :icon="showCompleted ? 'visibility_off' : 'visibility'"
            @click="toggleShowCompleted"
            dense
            unelevated
            no-caps
            size="md"
          />
        </div>
      </div>

      <q-table
        dense
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="remote-bg-tbl-sticky"
        :data="actions"
        :columns="columns"
        :visible-columns="visibleColumns"
        :pagination.sync="pagination"
        row-key="id"
        binary-state-sort
        hide-bottom
        virtual-scroll
        flat
        :rows-per-page-options="[0]"
      >
        <template slot="body" slot-scope="props" :props="props">
          <q-tr
            :class="rowClass(props.row.id, props.row.status)"
            @click="rowSelected(props.row.id, props.row.status, props.row.action_type)"
          >
            <q-td v-if="props.row.action_type === 'schedreboot'">
              <q-icon name="power_settings_new" size="sm" />
            </q-td>
            <q-td v-else-if="props.row.action_type === 'taskaction'">
              <q-icon name="fas fa-tasks" size="sm" />
            </q-td>
            <q-td v-else-if="props.row.action_type === 'agentupdate'">
              <q-icon name="update" size="sm" />
            </q-td>
            <q-td v-else-if="props.row.action_type === 'chocoinstall'">
              <q-icon name="download" size="sm" />
            </q-td>
            <q-td v-if="props.row.status !== 'completed'">{{ props.row.due }}</q-td>
            <q-td v-else>Completed</q-td>
            <q-td>{{ props.row.description }}</q-td>
            <q-td v-if="props.row.action_type === 'chocoinstall' && props.row.status === 'completed'">
              <q-btn
                color="primary"
                icon="preview"
                size="sm"
                label="View output"
                @click="showOutput(props.row.details.output)"
              />
            </q-td>
            <q-td v-else></q-td>
            <q-td v-show="!!!agentpk">{{ props.row.hostname }}</q-td>
            <q-td v-show="!!!agentpk">{{ props.row.client }}</q-td>
            <q-td v-show="!!!agentpk">{{ props.row.site }}</q-td>
          </q-tr>
        </template>
      </q-table>
    </div>
    <div v-else class="q-pa-md">No pending actions</div>
    <q-card-section></q-card-section>
    <q-separator />
    <q-card-section></q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
export default {
  name: "PendingActions",
  mixins: [mixins],
  props: {
    agentpk: Number,
  },
  data() {
    return {
      actions: [],
      selectedRow: null,
      showCompleted: false,
      selectedStatus: null,
      completedCount: 0,
      totalCount: 0,
      actionType: null,
      hostname: "",
      pagination: {
        rowsPerPage: 0,
        sortBy: "status",
        descending: false,
      },
      all_columns: [
        { name: "id", field: "id" },
        { name: "status", field: "status" },
        { name: "type", label: "Type", field: "action_type", align: "left", sortable: true },
        { name: "due", label: "Due", field: "due", align: "left", sortable: true },
        { name: "desc", label: "Description", field: "description", align: "left", sortable: true },
        { name: "details", field: "details", align: "left", sortable: false },
        { name: "agent", label: "Agent", field: "hostname", align: "left", sortable: true },
        { name: "client", label: "Client", field: "client", align: "left", sortable: true },
        { name: "site", label: "Site", field: "site", align: "left", sortable: true },
      ],
      all_visibleColumns: ["type", "due", "desc", "agent", "client", "site", "details"],
      agent_columns: [
        { name: "id", field: "id" },
        { name: "status", field: "status" },
        { name: "type", label: "Type", field: "action_type", align: "left", sortable: true },
        { name: "due", label: "Due", field: "due", align: "left", sortable: true },
        { name: "desc", label: "Description", field: "description", align: "left", sortable: true },
        { name: "details", field: "details", align: "left", sortable: false },
      ],
      agent_visibleColumns: ["type", "due", "desc", "details"],
    };
  },
  methods: {
    showOutput(details) {
      this.$q.dialog({
        style: "width: 75vw; max-width: 85vw; max-height: 65vh;",
        class: "scroll",
        message: `<pre>${details}</pre>`,
        html: true,
      });
    },
    toggleShowCompleted() {
      this.showCompleted = !this.showCompleted;
      this.getPendingActions();
    },
    getPendingActions() {
      let data = { showCompleted: this.showCompleted };
      if (!!this.agentpk) data.agentPK = this.agentpk;
      this.$q.loading.show();
      this.clearRow();
      this.$axios
        .patch("/logs/pendingactions/", data)
        .then(r => {
          this.totalCount = r.data.total;
          this.completedCount = r.data.completed_count;
          this.actions = Object.freeze(r.data.actions);
          if (!!this.agentpk) this.hostname = r.data.actions[0].hostname;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    cancelPendingAction() {
      this.$q
        .dialog({
          title: "Delete this pending action?",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          const data = { pk: this.selectedRow };
          this.$axios
            .delete("/logs/pendingactions/", { data: data })
            .then(r => {
              this.$q.loading.hide();
              this.getPendingActions();
              this.$emit("edited");
              this.notifySuccess(r.data, 3000);
            })
            .catch(e => {
              this.$q.loading.hide();
              this.notifyError(e.response.data);
            });
        });
    },
    rowSelected(pk, status, actiontype) {
      this.selectedRow = pk;
      this.selectedStatus = status;
      this.actionType = actiontype;
    },
    clearRow() {
      this.selectedRow = null;
      this.selectedStatus = null;
      this.actionType = null;
    },
    rowClass(id, status) {
      if (this.selectedRow === id && status !== "completed") {
        return this.$q.dark.isActive ? "highlight-dark" : "highlight";
      } else if (status === "completed") {
        return "action-completed";
      }
    },
  },
  computed: {
    columns() {
      return !!this.agentpk ? this.agent_columns : this.all_columns;
    },
    visibleColumns() {
      return !!this.agentpk ? this.agent_visibleColumns : this.all_visibleColumns;
    },
    title() {
      return !!this.agentpk ? `Pending Actions for ${this.hostname}` : "All Pending Actions";
    },
  },
  created() {
    this.getPendingActions();
  },
};
</script>