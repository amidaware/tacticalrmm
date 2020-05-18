<template>
  <div class="q-pa-md q-gutter-sm">
    <q-dialog :value="togglePendingActions" @hide="hidePendingActions" @show="getPendingActions">
      <q-card style="width: 900px; max-width: 90vw;">
        <q-inner-loading :showing="actionsLoading">
          <q-spinner size="40px" color="primary" />
        </q-inner-loading>
        <q-bar>
          <q-btn @click="getPendingActions" class="q-mr-sm" dense flat push icon="refresh" />
          {{ title }}
          <q-space />
          <q-btn dense flat icon="close" v-close-popup />
        </q-bar>
        <div v-if="actions.length !== 0" class="q-pa-md">
          <div class="row">
            <div class="col-2">
              <q-btn
                label="Cancel Action"
                :disable="selectedRow === null || selectedStatus === 'completed'"
                color="red"
                icon="cancel"
                dense
                unelevated
                no-caps
                size="md"
                @click="cancelPendingAction"
              />
            </div>
            <div class="col"></div>
            <div class="col-2">
              <q-btn
                :label="showCompleted ? 'Hide Completed' : 'Show Completed'"
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
                @click="rowSelected(props.row.id, props.row.status)"
              >
                <q-td v-if="props.row.action_type == 'schedreboot'">
                  <q-icon name="power_settings_new" size="sm" />
                </q-td>
                <q-td>{{ props.row.due }}</q-td>
                <q-td>{{ props.row.description }}</q-td>
                <q-td v-show="agentpk === null">{{ props.row.hostname }}</q-td>
                <q-td v-show="agentpk === null">{{ props.row.client }}</q-td>
                <q-td v-show="agentpk === null">{{ props.row.site }}</q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
        <div v-else class="q-pa-md">No pending actions</div>
        <q-card-section></q-card-section>
        <q-separator />
        <q-card-section></q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";
export default {
  name: "PendingActions",
  mixins: [mixins],
  data() {
    return {
      selectedRow: null,
      showCompleted: false,
      selectedStatus: null,
      pagination: {
        rowsPerPage: 0,
        sortBy: "due",
        descending: true
      },
      all_columns: [
        { name: "id", field: "id" },
        { name: "status", field: "status" },
        { name: "type", label: "Type", align: "left", sortable: true },
        { name: "due", label: "Due", field: "due", align: "left", sortable: true },
        { name: "desc", label: "Description", align: "left", sortable: true },
        { name: "agent", label: "Agent", align: "left", sortable: true },
        { name: "client", label: "Client", align: "left", sortable: true },
        { name: "site", label: "Site", align: "left", sortable: true }
      ],
      all_visibleColumns: ["type", "due", "desc", "agent", "client", "site"],
      agent_columns: [
        { name: "id", field: "id" },
        { name: "status", field: "status" },
        { name: "type", label: "Type", align: "left", sortable: true },
        { name: "due", label: "Due", field: "due", align: "left", sortable: true },
        { name: "desc", label: "Description", align: "left", sortable: true }
      ],
      agent_visibleColumns: ["type", "due", "desc"]
    };
  },
  methods: {
    getPendingActions() {
      this.clearRow();
      this.$store.dispatch("logs/getPendingActions");
    },
    cancelPendingAction() {
      this.$q
        .dialog({
          title: "Delete this pending action?",
          cancel: true,
          ok: { label: "Delete", color: "negative" }
        })
        .onOk(() => {
          this.$q.loading.show();
          const data = { pk: this.selectedRow };
          axios
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
    hidePendingActions() {
      this.showCompleted = false;
      this.selectedStatus = null;
      this.$store.commit("logs/CLEAR_PENDING_ACTIONS");
    },
    rowSelected(pk, status) {
      this.selectedRow = pk;
      this.selectedStatus = status;
    },
    clearRow() {
      this.selectedRow = null;
    },
    rowClass(id, status) {
      if (this.selectedRow === id && status !== "completed") {
        return "highlight";
      } else if (status === "completed") {
        return "action-completed";
      }
    }
  },
  computed: {
    ...mapGetters({
      hostname: "logs/actionsHostname",
      togglePendingActions: "logs/togglePendingActions",
      actions: "logs/allPendingActions",
      agentpk: "logs/actionsAgentPk",
      actionsLoading: "logs/pendingActionsLoading"
    }),
    filter() {
      return this.showCompleted ? this.actions : this.actions.filter(k => k.status === "pending");
    },
    columns() {
      return this.agentpk === null ? this.all_columns : this.agent_columns;
    },
    visibleColumns() {
      return this.agentpk === null ? this.all_visibleColumns : this.agent_visibleColumns;
    },
    title() {
      return this.agentpk === null ? "All Pending Actions" : `Pending Actions for ${this.hostname}`;
    }
  }
};
</script>