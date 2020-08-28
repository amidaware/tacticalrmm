<template>
  <div v-if="!selectedAgentPk">No agent selected</div>
  <div
    v-else-if="managedByWsus"
  >Patch management is not available for this agent because it is managed by WSUS</div>
  <div v-else-if="Object.keys(sortedUpdates).length === 0">No Patches</div>
  <div v-else class="q-pa-xs">
    <q-btn label="Refresh" dense flat push @click="refreshUpdates(updates.pk)" icon="refresh" />
    <q-table
      dense
      class="tabs-tbl-sticky"
      :style="{'max-height': tabsTableHeight}"
      :data="sortedUpdates"
      :columns="columns"
      :visible-columns="visibleColumns"
      :pagination.sync="pagination"
      :filter="filter"
      row-key="id"
      binary-state-sort
      hide-bottom
      virtual-scroll
      :rows-per-page-options="[0]"
    >
      <template slot="body" slot-scope="props" :props="props">
        <q-tr :props="props">
          <q-menu context-menu>
            <q-list dense style="min-width: 100px">
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editPolicy(props.row.id, 'inherit')"
              >
                <q-item-section>Inherit</q-item-section>
              </q-item>
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editPolicy(props.row.id, 'approve')"
              >
                <q-item-section>Approve</q-item-section>
              </q-item>
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editPolicy(props.row.id, 'ignore')"
              >
                <q-item-section>Ignore</q-item-section>
              </q-item>
              <q-item
                v-if="!props.row.installed"
                clickable
                v-close-popup
                @click="editPolicy(props.row.id, 'nothing')"
              >
                <q-item-section>Do Nothing</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <!-- policy -->
          <q-td>
            <q-icon v-if="props.row.action === 'nothing'" name="fiber_manual_record" color="grey">
              <q-tooltip>Do Nothing</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action === 'approve'" name="fas fa-check" color="primary">
              <q-tooltip>Approve</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action === 'ignore'" name="fas fa-check" color="negative">
              <q-tooltip>Ignore</q-tooltip>
            </q-icon>
            <q-icon
              v-else-if="props.row.action === 'inherit'"
              name="fiber_manual_record"
              color="accent"
            >
              <q-tooltip>Inherit</q-tooltip>
            </q-icon>
          </q-td>
          <q-td>
            <q-icon v-if="props.row.installed" name="fas fa-check" color="positive">
              <q-tooltip>Installed</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action == 'approve'" name="fas fa-tasks" color="primary">
              <q-tooltip>Pending</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.action == 'ignore'" name="fas fa-ban" color="negative">
              <q-tooltip>Ignored</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-exclamation" color="warning">
              <q-tooltip>Missing</q-tooltip>
            </q-icon>
          </q-td>
          <q-td>{{ props.row.severity }}</q-td>
          <q-td>{{ formatMessage(props.row.title) }}</q-td>
          <q-td @click.native="showFullMsg(props.row.title, props.row.description)">
            <span
              style="cursor:pointer;color:blue;text-decoration:underline"
            >{{ formatMessage(props.row.description) }}</span>
          </q-td>
          <q-td>{{ props.row.date_installed }}</q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "WindowsUpdates",
  mixins: [mixins],
  data() {
    return {
      filter: "",
      pagination: {
        rowsPerPage: 0,
        sortBy: "installed",
        descending: false,
      },
      columns: [
        { name: "id", label: "ID", field: "id" },
        {
          name: "action",
          field: "action",
          align: "left",
        },
        {
          name: "installed",
          field: "installed",
          align: "left",
        },
        {
          name: "severity",
          label: "Severity",
          field: "severity",
          align: "left",
          sortable: true,
        },
        {
          name: "title",
          label: "Name",
          field: "title",
          align: "left",
          sortable: true,
        },
        {
          name: "description",
          label: "Description",
          field: "description",
          align: "left",
          sortable: true,
        },
        {
          name: "date_installed",
          label: "Installed On",
          field: "date_installed",
          align: "left",
          sortable: true,
        },
      ],
      visibleColumns: ["action", "installed", "severity", "title", "description", "date_installed"],
    };
  },
  methods: {
    editPolicy(pk, policy) {
      const data = { pk: pk, policy: policy };
      axios.patch(`/winupdate/editpolicy/`, data).then(r => {
        this.refreshUpdates(this.updates.pk);
        this.notifySuccess("Policy edited!");
      });
    },
    refreshUpdates(pk) {
      this.$store.dispatch("loadWinUpdates", pk);
    },
    formatMessage(msg) {
      return msg.substring(0, 80) + "...";
    },
    showFullMsg(title, msg) {
      this.$q.dialog({
        title: title,
        message: msg.split(". ").join(".<br />"),
        html: true,
        fullWidth: true,
      });
    },
  },
  computed: {
    ...mapState({
      updates: state => Object.freeze(state.winUpdates),
    }),
    ...mapGetters(["sortedUpdates", "selectedAgentPk", "managedByWsus", "tabsTableHeight"]),
  },
};
</script>