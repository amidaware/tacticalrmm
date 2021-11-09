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
        @click="showAddTask"
      />
      <q-btn v-if="!!selectedPolicy" dense flat push @click="getTasks" icon="refresh" />
      <q-table
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="tabs-tbl-sticky"
        :rows="tasks"
        :columns="columns"
        :rows-per-page-options="[0]"
        v-model:pagination="pagination"
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

        <template v-slot:header-cell-collector="props">
          <q-th auto-width :props="props">
            <q-icon name="mdi-database-arrow-up" size="1.5em">
              <q-tooltip>Collector Task</q-tooltip>
            </q-icon>
          </q-th>
        </template>

        <!-- body slots -->
        <template v-slot:body="props" :props="props">
          <q-tr class="cursor-pointer" @dblclick="showEditTask(props.row)">
            <!-- context menu -->
            <q-menu context-menu>
              <q-list dense style="min-width: 200px">
                <q-item clickable v-close-popup @click="runTask(props.row)">
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
                <q-item clickable v-close-popup @click="deleteTask(props.row)">
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
                @update:model-value="editTask(props.row, { enabled: !props.row.enabled })"
                v-model="props.row.enabled"
              />
            </q-td>

            <q-td>
              <q-checkbox
                dense
                @update:model-value="editTask(props.row, { text_alert: !props.row.text_alert })"
                v-model="props.row.text_alert"
              />
            </q-td>
            <!-- email alert -->
            <q-td>
              <q-checkbox
                dense
                @update:model-value="editTask(props.row, { email_alert: !props.row.email_alert })"
                v-model="props.row.email_alert"
              />
            </q-td>
            <!-- dashboard alert -->
            <q-td>
              <q-checkbox
                dense
                @update:model-value="editTask(props.row, { dashboard_alert: !props.row.dashboard_alert })"
                v-model="props.row.dashboard_alert"
              />
            </q-td>
            <!-- is collector task -->
            <q-td>
              <q-icon v-if="!!props.row.custom_field" style="font-size: 1.3rem" name="check">
                <q-tooltip>The task updates a custom field on the agent</q-tooltip>
              </q-icon>
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
            <q-td>{{ props.row.check_name }}</q-td>
          </q-tr>
        </template>
      </q-table>
    </div>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import AddAutomatedTask from "@/components/tasks/AddAutomatedTask";
import EditAutomatedTask from "@/components/tasks/EditAutomatedTask";
import PolicyStatus from "@/components/automation/modals/PolicyStatus";

export default {
  name: "PolicyAutomatedTasksTab",
  mixins: [mixins],
  props: {
    selectedPolicy: !Number,
  },
  data() {
    return {
      tasks: [],
      columns: [
        { name: "enabled", align: "left", field: "enabled" },
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "dashboardalert", field: "dashboard_alert", align: "left" },
        { name: "collector", label: "Collector", field: "custom_field", align: "left", sortable: true },
        { name: "name", label: "Name", field: "name", align: "left", sortable: true },
        {
          name: "schedule",
          label: "Schedule",
          field: "schedule",
          align: "left",
          sortable: true,
        },
        {
          name: "status",
          label: "More Info",
          field: "more_info",
          align: "left",
          sortable: true,
        },
        {
          name: "check_name",
          label: "Assigned Check",
          field: "check_name",
          align: "left",
          sortable: true,
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
        .get(`/automation/policies/${this.selectedPolicy}/tasks/`)
        .then(r => {
          this.tasks = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    editTask(task, data) {
      this.$axios
        .put(`/tasks/${task.id}/`, data)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
          this.getTasks();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    showAddTask() {
      this.$q
        .dialog({
          component: AddAutomatedTask,
          componentProps: {
            parent: { policy: this.selectedPolicy },
          },
        })
        .onOk(this.getTasks);
    },
    showEditTask(task) {
      this.$q
        .dialog({
          component: EditAutomatedTask,
          componentProps: {
            task: task,
          },
        })
        .onOk(this.getTasks);
    },
    showStatus(task) {
      this.$q.dialog({
        component: PolicyStatus,
        componentProps: {
          type: "task",
          item: task,
        },
      });
    },
    runTask(task) {
      if (!task.enabled) {
        this.notifyError("Task cannot be run when it's disabled. Enable it first.");
        return;
      }

      this.$q.loading.show();
      this.$axios
        .post(`/automation/tasks/${task.id}/run/`)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess("The task was initated on all affected agents");
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    deleteTask(task) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete ${task.name} task`,
          cancel: true,
          persistent: true,
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/tasks/${task.id}/`)
            .then(r => {
              this.getTasks();
              this.$q.loading.hide();
              this.notifySuccess("Task was deleted successfully");
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
  },
  created() {
    this.getTasks();
  },
};
</script>

