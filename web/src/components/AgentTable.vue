<template>
  <div class="q-pa-none">
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="agents-tbl-sticky"
      :table-style="{ 'max-height': tableHeight }"
      :rows="agents"
      :filter="search"
      :filter-method="filterTable"
      :columns="columns"
      :visible-columns="visibleColumns"
      row-key="id"
      binary-state-sort
      virtual-scroll
      v-model:pagination="pagination"
      :rows-per-page-options="[0]"
      no-data-label="No Agents"
      :loading="agentTableLoading"
    >
      <!-- header slots -->
      <template v-slot:header-cell-smsalert="props">
        <q-th auto-width :props="props">
          <q-icon name="phone_android" size="1.5em">
            <q-tooltip>SMS Alert</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-emailalert="props">
        <q-th auto-width :props="props">
          <q-icon name="email" size="1.5em">
            <q-tooltip>Email Alert</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-dashboardalert="props">
        <q-th auto-width :props="props">
          <q-icon name="notifications" size="1.5em">
            <q-tooltip>Dashboard Alert</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-plat="props">
        <q-th auto-width :props="props"></q-th>
      </template>
      <template v-slot:header-cell-checks-status="props">
        <q-th :props="props">
          <q-icon name="fas fa-check-double" size="1.2em">
            <q-tooltip>Checks Status</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-patchespending="props">
        <q-th auto-width :props="props">
          <q-icon name="verified_user" size="1.5em">
            <q-tooltip>Patches Pending</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-pendingactions="props">
        <q-th auto-width :props="props">
          <q-icon name="far fa-clock" size="1.5em">
            <q-tooltip>Pending Actions</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-agentstatus="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-signal" size="1.2em">
            <q-tooltip>Agent Status</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-needs_reboot="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-power-off" size="1.2em">
            <q-tooltip>Reboot</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <!-- body slots -->
      <template v-slot:body="props">
        <q-tr
          @contextmenu="agentRowSelected(props.row.agent_id, props.row.plat)"
          :props="props"
          :class="rowSelectedClass(props.row.agent_id)"
          @click="agentRowSelected(props.row.agent_id, props.row.plat)"
          @dblclick="rowDoubleClicked(props.row.agent_id, props.row.plat)"
        >
          <q-menu context-menu>
            <AgentActionMenu :agent="props.row" />
          </q-menu>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_text !== null"
              v-model="props.row.alert_template.always_text"
              disable
              dense
            >
              <q-tooltip> Setting is overridden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="overdueAlert('text', props.row, props.row.overdue_text_alert)"
              v-model="props.row.overdue_text_alert"
            />
          </q-td>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_email !== null"
              v-model="props.row.alert_template.always_email"
              disable
              dense
            >
              <q-tooltip> Setting is overridden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="overdueAlert('email', props.row, props.row.overdue_email_alert)"
              v-model="props.row.overdue_email_alert"
            />
          </q-td>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_alert !== null"
              v-model="props.row.alert_template.always_alert"
              disable
              dense
            >
              <q-tooltip> Setting is overridden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="overdueAlert('dashboard', props.row, props.row.overdue_dashboard_alert)"
              v-model="props.row.overdue_dashboard_alert"
            />
          </q-td>

          <q-td key="plat" :props="props">
            <q-icon v-if="props.row.plat === 'windows'" name="mdi-microsoft-windows" size="sm" color="primary">
              <q-tooltip>Microsoft Windows</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.plat === 'linux'" name="mdi-linux" size="sm" color="primary">
              <q-tooltip>Linux</q-tooltip>
            </q-icon>
          </q-td>

          <q-td key="checks-status" :props="props">
            <q-icon v-if="props.row.maintenance_mode" name="construction" size="1.2em" color="green">
              <q-tooltip>Maintenance Mode Enabled</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.checks.failing > 0" name="fas fa-check-double" size="1.2em" color="negative">
              <q-tooltip>Checks failing</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.checks.warning > 0" name="fas fa-check-double" size="1.2em" color="warning">
              <q-tooltip>Checks warning</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.checks.info > 0" name="fas fa-check-double" size="1.2em" color="info">
              <q-tooltip>Checks info</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-check-double" size="1.2em" color="positive">
              <q-tooltip>Checks passing</q-tooltip>
            </q-icon>
          </q-td>

          <q-td key="client_name" :props="props">{{ props.row.client_name }}</q-td>
          <q-td key="site_name" :props="props">{{ props.row.site_name }}</q-td>
          <q-td key="hostname" :props="props">{{ props.row.hostname }}</q-td>
          <q-td key="description" :props="props">{{ props.row.description }}</q-td>
          <q-td key="user" :props="props">
            <span class="text-italic" v-if="props.row.italic">{{ props.row.logged_username }}</span>
            <span v-else>{{ props.row.logged_username }}</span>
          </q-td>
          <q-td :props="props" key="patchespending">
            <q-icon v-if="props.row.has_patches_pending" name="verified_user" size="1.5em" color="primary">
              <q-tooltip>Patches Pending</q-tooltip>
            </q-icon>
          </q-td>
          <q-td :props="props" key="pendingactions">
            <q-icon
              v-if="props.row.pending_actions_count !== 0"
              @click="showPendingActionsModal(props.row)"
              name="far fa-clock"
              size="1.4em"
              color="warning"
              class="cursor-pointer"
            >
              <q-tooltip>Pending Action Count: {{ props.row.pending_actions_count }}</q-tooltip>
            </q-icon>
          </q-td>
          <!-- needs reboot -->
          <q-td key="needsreboot">
            <q-icon v-if="props.row.needs_reboot" name="fas fa-power-off" color="primary">
              <q-tooltip>Reboot required</q-tooltip>
            </q-icon>
          </q-td>
          <q-td key="agentstatus">
            <q-icon v-if="props.row.status === 'overdue'" name="fas fa-signal" size="1.2em" color="negative">
              <q-tooltip>Agent overdue</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.status === 'offline'" name="fas fa-signal" size="1.2em" color="warning">
              <q-tooltip>Agent offline</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-signal" size="1.2em" color="positive">
              <q-tooltip>Agent online</q-tooltip>
            </q-icon>
          </q-td>
          <q-td key="last_seen" :props="props">{{ formatDate(props.row.last_seen) }}</q-td>
          <q-td key="boot_time" :props="props">{{ bootTime(props.row.boot_time) }}</q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import { date } from "quasar";
import EditAgent from "@/components/modals/agents/EditAgent";
import PendingActions from "@/components/logs/PendingActions";
import AgentActionMenu from "@/components/agents/AgentActionMenu";
import { runURLAction } from "@/api/core";
import { runTakeControl, runRemoteBackground } from "@/api/agents";

export default {
  name: "AgentTable",
  components: {
    AgentActionMenu,
  },
  props: ["agents", "columns", "search", "visibleColumns"],
  inject: ["refreshDashboard"],
  mixins: [mixins],
  data() {
    return {
      pagination: {
        rowsPerPage: 0,
        sortBy: "hostname",
        descending: false,
      },
    };
  },
  methods: {
    filterTable(rows, terms, cols, cellValue) {
      const lowerTerms = terms ? terms.toLowerCase() : "";
      let advancedFilter = false;
      let availability = null;
      let checks = false;
      let patches = false;
      let actions = false;
      let reboot = false;
      let search = "";

      const params = lowerTerms.trim().split(" ");
      // parse search text and set variables
      params.forEach(param => {
        if (param.includes("is:")) {
          advancedFilter = true;
          let filter = param.split(":")[1];
          if (filter === "patchespending") patches = true;
          if (filter === "actionspending") actions = true;
          else if (filter === "checksfailing") checks = true;
          else if (filter === "rebootneeded") reboot = true;
          else if (filter === "online" || filter === "offline" || filter === "expired" || filter === "overdue")
            availability = filter;
        } else {
          search = param + "";
        }
      });

      return rows.filter(row => {
        if (advancedFilter) {
          if (checks && !row.checks.has_failing_checks) return false;
          if (patches && !row.has_patches_pending) return false;
          if (actions && row.pending_actions_count === 0) return false;
          if (reboot && !row.needs_reboot) return false;
          if (availability === "online" && row.status !== "online") return false;
          else if (availability === "offline" && row.status !== "offline") return false;
          else if (availability === "overdue" && row.status !== "overdue") return false;
          else if (availability === "expired") {
            let now = new Date();
            let lastSeen = date.extractDate(row.last_seen, "MM DD YYYY HH:mm");
            let diff = date.getDateDiff(now, lastSeen, "days");
            if (diff < 30) return false;
          }
        }

        // Normal text filter
        return cols.some(col => {
          const val = cellValue(col, row) + "";
          const haystack = val === "undefined" || val === "null" ? "" : val.toLowerCase();
          return haystack.indexOf(search) !== -1;
        });
      });
    },
    rowDoubleClicked(agent_id, agentPlatform) {
      this.$store.commit("setActiveRow", agent_id);
      this.$q.loading.show();
      // give time for store to change active row
      setTimeout(() => {
        this.$q.loading.hide();
        switch (this.agentDblClickAction) {
          case "editagent":
            this.showEditAgent(agent_id);
            break;
          case "takecontrol":
            runTakeControl(agent_id);
            break;
          case "remotebg":
            runRemoteBackground(agent_id, agentPlatform);
            break;
          case "urlaction":
            runURLAction({ agent_id: agent_id, action: this.agentUrlAction });
            break;
        }
      }, 500);
    },
    showPendingActionsModal(agent) {
      this.$q.dialog({
        component: PendingActions,
        componentProps: {
          agent: agent,
        },
      });
    },
    agentRowSelected(agent_id, agentPlatform) {
      this.$store.commit("setActiveRow", agent_id);
      this.$store.commit("setAgentPlatform", agentPlatform);
    },
    overdueAlert(category, agent, alert_action) {
      let db_field = "";
      if (category === "email") db_field = "overdue_email_alert";
      else if (category === "text") db_field = "overdue_text_alert";
      else if (category === "dashboard") db_field = "overdue_dashboard_alert";

      const action = !alert_action ? "enabled" : "disabled";
      const data = {
        [db_field]: !alert_action,
      };
      const alertColor = !alert_action ? "positive" : "warning";
      this.$axios
        .put(`/agents/${agent.agent_id}/`, data)
        .then(r => {
          this.$q.notify({
            color: alertColor,
            icon: "fas fa-check-circle",
            message: `Overdue ${category} alerts ${action} on ${agent.hostname}`,
          });
        })
        .catch(e => {});
    },
    agentClass(status) {
      if (status === "offline") {
        return "agent-offline";
      } else if (status === "overdue") {
        return "agent-overdue";
      } else {
        return "agent-normal";
      }
    },
    rowSelectedClass(agent_id) {
      if (agent_id === this.selectedRow) {
        return this.$q.dark.isActive ? "highlight-dark" : "highlight";
      } else {
        return "";
      }
    },
    showEditAgent(agent_id) {
      this.$q
        .dialog({
          component: EditAgent,
          componentProps: {
            agent_id: agent_id,
          },
        })
        .onOk(() => {
          this.refreshDashboard();
          this.$store.commit("setRefreshSummaryTab", true);
        });
    },
  },
  computed: {
    ...mapState(["tableHeight"]),
    agentDblClickAction() {
      return this.$store.state.agentDblClickAction;
    },
    agentUrlAction() {
      return this.$store.state.agentUrlAction;
    },
    selectedRow() {
      return this.$store.state.selectedRow;
    },
    agentTableLoading() {
      return this.$store.state.agentTableLoading;
    },
    formatDate() {
      return this.$store.getters.formatDate;
    },
  },
};
</script>

