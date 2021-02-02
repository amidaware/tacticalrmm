<template>
  <div class="row">
    <div class="col-12">
      <q-btn
        v-if="!!selectedPolicy"
        size="sm"
        color="grey-5"
        icon="fas fa-plus"
        label="Add Task"
        text-color="black"
        @click="showAddTask = true"
      />
      <q-btn v-if="!!selectedPolicy" dense flat push @click="getTasks" icon="refresh" />
      <template>
        <q-table
          style="max-height: 35vh"
          :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
          class="tabs-tbl-sticky"
          :data="tasks"
          :columns="columns"
          :rows-per-page-options="[0]"
          :pagination.sync="pagination"
          dense
          row-key="id"
          binary-state-sort
          hide-pagination
          virtual-scroll
        >
          <!-- No data Slot -->
          <template v-slot:no-data>
            <div class="full-width row flex-center q-gutter-sm">
              <span v-if="!selectedPolicy">Click on a policy to see the tasks</span>
              <span v-else>There are no tasks added to this policy</span>
            </div>
          </template>
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
          <!-- body slots -->
          <template v-slot:body="props" :props="props">
            <q-tr @dblclick="showEditTask(props.row)">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="runTask(props.row.id, props.row.enabled)">
                    <q-item-section side>
                      <q-icon name="play_arrow" />
                    </q-item-section>
                    <q-item-section>Run task now</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="showEditTask(props.row)">
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="deleteTask(props.row.name, props.row.id)">
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>
                  <q-separator />
                  <q-item clickable v-close-popup @click="showStatus(props.row)">
                    <q-item-section side>
                      <q-icon name="sync" />
                    </q-item-section>
                    <q-item-section>Policy Status</q-item-section>
                  </q-item>
                  <q-separator />
                  <q-item clickable v-close-popup>
                    <q-item-section>Close</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
              <!-- tds -->
              <q-td>
                <q-checkbox
                  dense
                  @input="taskEnableorDisable(props.row.id, props.row.enabled)"
                  v-model="props.row.enabled"
                />
              </q-td>

              <q-td>
                <q-checkbox
                  dense
                  @input="taskAlert(props.row.id, 'Text', props.row.text_alert, props.row.managed_by_policy)"
                  v-model="props.row.text_alert"
                />
              </q-td>
              <!-- email alert -->
              <q-td>
                <q-checkbox
                  dense
                  @input="taskAlert(props.row.id, 'Email', props.row.email_alert, props.row.managed_by_policy)"
                  v-model="props.row.email_alert"
                />
              </q-td>
              <!-- dashboard alert -->
              <q-td>
                <q-checkbox
                  dense
                  @input="taskAlert(props.row.id, 'Dashboard', props.row.dashboard_alert, props.row.managed_by_policy)"
                  v-model="props.row.dashboard_alert"
                />
              </q-td>
              <q-td>{{ props.row.name }}</q-td>
              <q-td>{{ props.row.schedule }}</q-td>
              <q-td>
                <span
                  style="cursor: pointer; text-decoration: underline"
                  @click="showStatus(props.row)"
                  class="status-cell text-primary"
                  >See Status</span
                >
              </q-td>
              <q-td v-if="props.row.assigned_check">{{ props.row.assigned_check.readable_desc }}</q-td>
              <q-td v-else></q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showAddTask" position="top">
      <AddAutomatedTask
        :policypk="selectedPolicy"
        @close="
          getTasks();
          showAddTask = false;
        "
      />
    </q-dialog>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import AddAutomatedTask from "@/components/modals/tasks/AddAutomatedTask";
import EditAutomatedTask from "@/components/modals/tasks/EditAutomatedTask";
import PolicyStatus from "@/components/automation/modals/PolicyStatus";

export default {
  name: "PolicyAutomatedTasksTab",
  mixins: [mixins],
  components: { AddAutomatedTask },
  props: {
    selectedPolicy: !Number,
  },
  data() {
    return {
      tasks: [],
      showAddTask: false,
      columns: [
        { name: "enabled", align: "left", field: "enabled" },
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "dashboardalert", field: "dashboard_alert", align: "left" },
        { name: "name", label: "Name", field: "name", align: "left" },
        {
          name: "schedule",
          label: "Schedule",
          field: "schedule",
          align: "left",
        },
        {
          name: "status",
          label: "More Info",
          field: "more_info",
          align: "left",
        },
        {
          name: "assignedcheck",
          label: "Assigned Check",
          field: "assigned_check",
          align: "left",
        },
      ],
      pagination: {
        rowsPerPage: 0,
        sortBy: "name",
        descending: true,
      },
    };
  },
  watch: {
    selectedPolicy: function (newValue, oldValue) {
      if (newValue !== oldValue) this.getTasks();
    },
  },
  methods: {
    getTasks() {
      this.$q.loading.show();
      this.$axios
        .get(`/automation/${this.selectedPolicy}/policyautomatedtasks/`)
        .then(r => {
          this.tasks = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("There was an issue getting tasks");
        });
    },
    taskEnableorDisable(pk, action) {
      this.$q.loading.show();
      const data = { id: pk, enableordisable: action };
      this.$axios
        .patch(`/tasks/${pk}/automatedtasks/`, data)
        .then(r => {
          this.getTasks();
          this.$q.loading.hide();
          this.notifySuccess("Task has edited successfully");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("There was an issue editing the task");
        });
    },
    taskAlert(pk, alert_type, action, managed_by_policy) {
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
          this.notifyError("There was an issue editing task");
        });
    },
    showEditTask(task) {
      this.$q
        .dialog({
          component: EditAutomatedTask,
          parent: this,
          task: task,
        })
        .onOk(() => {
          this.getTasks();
        });
    },
    showStatus(task) {
      this.$q.dialog({
        component: PolicyStatus,
        parent: this,
        type: "task",
        item: task,
      });
    },
    runTask(pk, enabled) {
      if (!enabled) {
        this.notifyError("Task cannot be run when it's disabled. Enable it first.");
        return;
      }

      this.$q.loading.show();
      this.$axios
        .put(`/automation/runwintask/${pk}/`)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess("The task was initated on all affected agents");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("There was an issue running the task");
        });
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
          this.$q.loading.show();
          this.$axios
            .delete(`/tasks/${pk}/automatedtasks/`)
            .then(r => {
              this.getTasks();
              this.$q.loading.hide();
              this.notifySuccess("Task was deleted successfully");
            })
            .catch(e => {
              this.$q.loading.hide();
              this.notifyError("There was an issue deleting the task");
            });
        });
    },
  },
  mounted() {
    this.getTasks();
  },
};
</script>

