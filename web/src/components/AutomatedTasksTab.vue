<template>
  <div v-if="!this.selectedAgentPk">No agent selected</div>
  <div v-else-if="Object.keys(automatedTasks).length === 0">No Tasks</div>
  <div class="row" v-else>
    <div class="col-12">
      <q-btn
        size="sm"
        color="grey-5"
        icon="fas fa-plus"
        label="Add Task"
        text-color="black"
        @click="showAddAutomatedTask = true"
      />
      <q-btn dense flat push @click="refreshTasks(automatedTasks.pk)" icon="refresh" />
      <template v-if="tasks === undefined || tasks.length === 0">
        <p>No Tasks</p>
      </template>
      <template v-else>
        <q-table
          dense
          :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
          class="tabs-tbl-sticky"
          :style="{ 'max-height': tabsTableHeight }"
          :rows="tasks"
          :columns="columns"
          :row-key="row => row.id"
          binary-state-sort
          :v-model:pagination="pagination"
          hide-bottom
        >
          <!-- header slots -->
          <template v-slot:header-cell-enabled="props">
            <q-th auto-width :props="props">
              <small>Enabled</small>
            </q-th>
          </template>

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
          <template v-slot:header-cell-policystatus="props">
            <q-th auto-width :props="props"></q-th>
          </template>

          <template v-slot:header-cell-collector="props">
            <q-th auto-width :props="props">
              <q-icon name="mdi-database-arrow-up" size="1.5em">
                <q-tooltip>Collector Task</q-tooltip>
              </q-icon>
            </q-th>
          </template>

          <template v-slot:header-cell-status="props">
            <q-th auto-width :props="props"></q-th>
          </template>
          <!-- body slots -->
          <template v-slot:body="props">
            <q-tr @contextmenu="editTaskPk = props.row.id">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="runTask(props.row.id, props.row.enabled)">
                    <q-item-section side>
                      <q-icon name="play_arrow" />
                    </q-item-section>
                    <q-item-section>Run task now</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="showEditTask(props.row)" v-if="!props.row.managed_by_policy">
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item
                    clickable
                    v-close-popup
                    @click="deleteTask(props.row.name, props.row.id)"
                    v-if="!props.row.managed_by_policy"
                  >
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>
                  <q-separator></q-separator>
                  <q-item clickable v-close-popup>
                    <q-item-section>Close</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
              <!-- tds -->
              <q-td>
                <q-checkbox
                  dense
                  @input="taskEnableorDisable(props.row.id, props.row.enabled, props.row.managed_by_policy)"
                  v-model="props.row.enabled"
                  :disable="props.row.managed_by_policy"
                />
              </q-td>
              <!-- text alert -->
              <q-td>
                <q-checkbox
                  v-if="props.row.alert_template && props.row.alert_template.always_text !== null"
                  :value="props.row.alert_template.always_text"
                  disable
                  dense
                >
                  <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
                </q-checkbox>

                <q-checkbox
                  v-else
                  dense
                  @input="taskAlert(props.row.id, 'Text', props.row.text_alert, props.row.managed_by_policy)"
                  v-model="props.row.text_alert"
                  :disable="props.row.managed_by_policy"
                />
              </q-td>
              <!-- email alert -->
              <q-td>
                <q-checkbox
                  v-if="props.row.alert_template && props.row.alert_template.always_email !== null"
                  :value="props.row.alert_template.always_email"
                  disable
                  dense
                >
                  <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
                </q-checkbox>

                <q-checkbox
                  v-else
                  dense
                  @input="taskAlert(props.row.id, 'Email', props.row.email_alert, props.row.managed_by_policy)"
                  v-model="props.row.email_alert"
                  :disable="props.row.managed_by_policy"
                />
              </q-td>
              <!-- dashboard alert -->
              <q-td>
                <q-checkbox
                  v-if="props.row.alert_template && props.row.alert_template.always_alert !== null"
                  :value="props.row.alert_template.always_alert"
                  disable
                  dense
                >
                  <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
                </q-checkbox>

                <q-checkbox
                  v-else
                  dense
                  @input="taskAlert(props.row.id, 'Dashboard', props.row.dashboard_alert, props.row.managed_by_policy)"
                  v-model="props.row.dashboard_alert"
                  :disable="props.row.managed_by_policy"
                />
              </q-td>
              <!-- policy check icon -->
              <q-td>
                <q-icon v-if="props.row.managed_by_policy" style="font-size: 1.3rem" name="policy">
                  <q-tooltip>This task is managed by a policy</q-tooltip>
                </q-icon>
              </q-td>

              <!-- is collector task -->
              <q-td>
                <q-icon v-if="!!props.row.custom_field" style="font-size: 1.3rem" name="check">
                  <q-tooltip>The task updates a custom field on the agent</q-tooltip>
                </q-icon>
              </q-td>
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
              <!-- name -->
              <q-td>{{ props.row.name }}</q-td>
              <!-- sync status -->
              <q-td v-if="props.row.sync_status === 'notsynced'">Will sync on next agent checkin</q-td>
              <q-td v-else-if="props.row.sync_status === 'synced'">Synced with agent</q-td>
              <q-td v-else-if="props.row.sync_status === 'pendingdeletion'">Pending deletion on agent</q-td>
              <q-td v-else-if="props.row.sync_status === 'initial'">Waiting for task creation on agent</q-td>
              <q-td v-else></q-td>
              <q-td v-if="props.row.retcode !== null || props.row.stdout || props.row.stderr">
                <span
                  style="cursor: pointer; text-decoration: underline"
                  class="text-primary"
                  @click="showScriptOutput(props.row)"
                  >output</span
                >
              </q-td>
              <q-td v-else>Awaiting output</q-td>
              <q-td v-if="props.row.last_run">{{ props.row.last_run }}</q-td>
              <q-td v-else>Has not run yet</q-td>
              <q-td>{{ props.row.schedule }}</q-td>
              <q-td v-if="props.row.assigned_check">{{ props.row.assigned_check.readable_desc }}</q-td>
              <q-td v-else></q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showAddAutomatedTask" position="top">
      <AddAutomatedTask @close="showAddAutomatedTask = false" />
    </q-dialog>
  </div>
</template>

<script>
import { mapState, mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import AddAutomatedTask from "@/components/modals/tasks/AddAutomatedTask";
import EditAutomatedTask from "@/components/modals/tasks/EditAutomatedTask";
import ScriptOutput from "@/components/modals/checks/ScriptOutput";

export default {
  name: "AutomatedTasksTab",
  components: { AddAutomatedTask },
  mixins: [mixins],
  data() {
    return {
      showAddAutomatedTask: false,
      showEditAutomatedTask: false,
      editTaskPk: null,
      scriptInfo: {},
      columns: [
        { name: "enabled", align: "left", field: "enabled" },
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "dashboardalert", field: "dashboard_alert", align: "left" },
        { name: "policystatus", align: "left" },
        { name: "collector", label: "Collector", field: "custom_field", align: "left", sortable: true },
        { name: "status", align: "left" },
        { name: "name", label: "Name", field: "name", align: "left", sortable: true },
        { name: "sync_status", label: "Sync Status", field: "sync_status", align: "left", sortable: true },
        {
          name: "moreinfo",
          label: "More Info",
          field: "more_info",
          align: "left",
          sortable: true,
        },
        {
          name: "datetime",
          label: "Last Run Time",
          field: "last_run",
          align: "left",
          sortable: true,
        },
        {
          name: "schedule",
          label: "Schedule",
          field: "schedule",
          align: "left",
          sortable: true,
        },
        {
          name: "assignedcheck",
          label: "Assigned Check",
          field: "assigned_check",
          align: "left",
          sortable: true,
        },
      ],
      pagination: {
        rowsPerPage: 9999,
        sortBy: "name",
        descending: false,
      },
    };
  },
  methods: {
    taskEnableorDisable(pk, action, managed_by_policy) {
      if (managed_by_policy) {
        return;
      }
      const data = { enableordisable: action };
      this.$axios
        .patch(`/tasks/${pk}/automatedtasks/`, data)
        .then(r => {
          this.$store.dispatch("loadAutomatedTasks", this.automatedTasks.pk);
          this.notifySuccess(r.data);
        })
        .catch(e => {});
    },
    taskAlert(pk, alert_type, action, managed_by_policy) {
      if (managed_by_policy) {
        return;
      }
      this.$q.loading.show();

      const data = {
        id: pk,
      };

      if (alert_type === "Email") {
        data.email_alert = action;
      } else if (alert_type === "Text") {
        data.text_alert = action;
      } else {
        data.dashboard_alert = action;
      }

      const act = action ? "enabled" : "disabled";
      this.$axios
        .put(`/tasks/${pk}/automatedtasks/`, data)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(`${alert_type} alerts ${act}`);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    refreshTasks(id) {
      this.$store.dispatch("loadAutomatedTasks", id);
    },
    showScriptOutput(script) {
      this.$q.dialog({
        component: ScriptOutput,
        componentProps: {
          scriptInfo: script,
        },
      });
    },
    showEditTask(task) {
      this.$q
        .dialog({
          component: EditAutomatedTask,
          componentProps: {
            task: task,
          },
        })
        .onOk(() => {
          this.refreshTasks(this.automatedTasks.pk);
        });
    },
    runTask(pk, enabled) {
      if (!enabled) {
        this.notifyError("Task cannot be run when it's disabled. Enable it first.");
        return;
      }
      this.$axios
        .get(`/tasks/runwintask/${pk}/`)
        .then(r => this.notifySuccess(r.data))
        .catch(e => {});
    },
    deleteTask(name, pk) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete ${name} task`,
          cancel: true,
          persistent: true,
        })
        .onOk(() => {
          this.$axios
            .delete(`/tasks/${pk}/automatedtasks/`)
            .then(r => {
              this.$store.dispatch("loadAutomatedTasks", this.automatedTasks.pk);
              this.$store.dispatch("loadChecks", this.automatedTasks.pk);
              this.notifySuccess(r.data);
            })
            .catch(e => {});
        });
    },
  },
  computed: {
    ...mapGetters(["selectedAgentPk", "tabsTableHeight"]),
    ...mapState({
      automatedTasks: state => state.automatedTasks,
    }),
    tasks() {
      return this.automatedTasks.autotasks.filter(task => task.sync_status !== "pendingdeletion");
    },
  },
};
</script>

