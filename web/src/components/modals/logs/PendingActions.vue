<template>
  <q-card style="width: 900px; max-width: 90vw">
    <q-bar>
      <q-btn @click="getPendingActions" class="q-mr-sm" dense flat push icon="refresh" />
      {{ title }}
      <q-space />
      <q-btn dense flat icon="close" v-close-popup />
    </q-bar>
    <div v-if="actions.length !== 0" class="q-pa-md">
      <div class="row">
        <div class="col">
          <q-btn
            label="Cancel Action"
            :disable="selectedRow === null || selectedStatus === 'completed' || actionType === 'taskaction'"
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
            @click="showCompleted = !showCompleted"
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
        :data="filter"
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
            <q-td>{{ props.row.due }}</q-td>
            <q-td>{{ props.row.description }}</q-td>
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
      actionType: null,
      hostname: "",
      pagination: {
        rowsPerPage: 0,
        sortBy: "due",
        descending: true,
      },
      all_columns: [
        { name: "id", field: "id" },
        { name: "status", field: "status" },
        { name: "type", label: "Type", align: "left", sortable: true },
        { name: "due", label: "Due", field: "due", align: "left", sortable: true },
        { name: "desc", label: "Description", align: "left", sortable: true },
        { name: "agent", label: "Agent", align: "left", sortable: true },
        { name: "client", label: "Client", align: "left", sortable: true },
        { name: "site", label: "Site", align: "left", sortable: true },
      ],
      all_visibleColumns: ["type", "due", "desc", "agent", "client", "site"],
      agent_columns: [
        { name: "id", field: "id" },
        { name: "status", field: "status" },
        { name: "type", label: "Type", align: "left", sortable: true },
        { name: "due", label: "Due", field: "due", align: "left", sortable: true },
        { name: "desc", label: "Description", align: "left", sortable: true },
      ],
      agent_visibleColumns: ["type", "due", "desc"],
    };
  },
  methods: {
    getPendingActions() {
      this.$q.loading.show();
      this.clearRow();
      this.$axios
        .get(this.url)
        .then(r => {
          this.actions = Object.freeze(r.data);
          if (!!this.agentpk) this.hostname = r.data[0].hostname;
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
            .delete("/logs/cancelpendingaction/", { data: data })
            .then(r => {
              this.$q.loading.hide();
              this.getPendingActions();
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
    url() {
      return !!this.agentpk ? `/logs/${this.agentpk}/pendingactions/` : "/logs/allpendingactions/";
    },
    filter() {
      return this.showCompleted ? this.actions : this.actions.filter(k => k.status === "pending");
    },
    columns() {
      return !!this.agentpk ? this.agent_columns : this.all_columns;
    },
    visibleColumns() {
      return !!this.agentpk ? this.agent_visibleColumns : this.all_visibleColumns;
    },
    title() {
      return !!this.agentpk ? `Pending Actions for ${this.hostname}` : "All Pending Actions";
    },
    completedCount() {
      return this.actions.filter(k => k.status === "completed").length;
    },
  },
  created() {
    this.getPendingActions();
  },
};
</script>