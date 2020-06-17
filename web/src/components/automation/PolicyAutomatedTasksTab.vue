<template>
  <div class="row">
    <div class="col-12">
      <q-btn
        size="sm"
        color="grey-5"
        icon="fas fa-plus"
        label="Add Task"
        text-color="black"
        ref="add"
        @click="showAddAutomatedTask = true"
      />
      <q-btn 
        dense 
        flat push 
        @click="refreshTasks(selectedPolicy)" 
        icon="refresh"
        ref="refresh" 
      />
      <template>
        <q-table
          dense
          class="tabs-tbl-sticky"
          :data="tasks"
          :columns="columns"
          row-key="id"
          binary-state-sort
          :pagination.sync="pagination"
          hide-pagination
        >
          <!-- header slots -->
          <template v-slot:header-cell-enabled="props">
            <q-th auto-width :props="props">
              <small>Enabled</small>
            </q-th>
          </template>
          <!-- No data Slot -->
          <template v-slot:no-data >
            <div class="full-width row flex-center q-gutter-sm">
              <span v-if="selectedPolicy === null">
                Click on a policy to see the tasks
              </span>
              <span v-else>
                There are no tasks added to this policy
              </span>
            </div>
          </template>
          <!-- body slots -->
          <template v-slot:body="props" :props="props">
            <q-tr @contextmenu="editTaskPk = props.row.id">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item 
                    clickable 
                    v-close-popup 
                    @click="runTask(props.row.id, props.row.enabled)"
                    id="context-runtask"
                  >
                    <q-item-section side>
                      <q-icon name="play_arrow" />
                    </q-item-section>
                    <q-item-section>Run task now</q-item-section>
                  </q-item>
                  <q-item 
                    clickable 
                    v-close-popup 
                    @click="showEditAutomatedTask = true"
                    id="context-edit"
                  >
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item 
                    clickable 
                    v-close-popup
                    @click="deleteTask(props.row.name, props.row.id)"
                    id="context-delete"
                  >
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>
                  <q-separator />
                  <q-item 
                    clickable 
                    v-close-popup
                    @click="showStatus(props.row)"
                    id="context-status"
                  >
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
              <q-td>{{ props.row.name }}</q-td>
              <q-td v-if="props.row.last_run">{{ props.row.last_run }}</q-td>
              <q-td v-else>Has not run yet</q-td>
              <q-td>{{ props.row.schedule }}</q-td>
              <q-td>
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="showStatus(props.row)"
                  class="status-cell"
                >
                See Status
                </span>
              </q-td>
              <q-td v-if="props.row.assigned_check">{{ props.row.assigned_check.name }}</q-td>
              <q-td v-else></q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showAddAutomatedTask" position="top">
      <AddAutomatedTask 
        :policypk="selectedPolicy"
        @close="showAddAutomatedTask = false" 
      />
    </q-dialog>

    <!-- policy task status -->
    <q-dialog v-model="showPolicyTaskStatus">
      <PolicyStatus 
        type="task" 
        :item="statusTask"
        :description="`${statusTask.name} Agent Status`"
      />
    </q-dialog>
  </div>
</template>

<script>
import { mapGetters } from "vuex";
import mixins, { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";
import AddAutomatedTask from "@/components/modals/tasks/AddAutomatedTask";
import PolicyStatus from "@/components/automation/modals/PolicyStatus";

export default {
  name: "PolicyAutomatedTasksTab",
  components: { 
    AddAutomatedTask,
    PolicyStatus
  },
  mixins: [mixins],
  data() {
    return {
      showAddAutomatedTask: false,
      showEditAutomatedTask: false,
      showPolicyTaskStatus: false,
      statusTask: {},
      editTaskPk: null,
      columns: [
        { name: "enabled", align: "left", field: "enabled" },
        { name: "name", label: "Name", field: "name", align: "left" },
        {
          name: "datetime",
          label: "Last Run Time",
          field: "last_run",
          align: "left"
        },
        {
          name: "schedule",
          label: "Schedule",
          field: "schedule",
          align: "left"
        },
        {
          name: "status",
          label: "More Info",
          field: "more_info",
          align: "left"
        },
        {
          name: "assignedcheck",
          label: "Assigned Check",
          field: "assigned_check",
          align: "left"
        }
      ],
      pagination: {
        rowsPerPage: 9999
      }
    };
  },
  methods: {
    taskEnableorDisable(pk, action) {
      const data = { id: pk, enableordisable: action };
      this.$store
        .dispatch("editAutoTask", data)
        .then(r => {
          this.$store.dispatch("automation/loadPolicyAutomatedTasks", this.selectedPolicy);
          this.$q.notify(notifySuccessConfig(r.data));
        })
        .catch(e => this.$q.notify(notifySuccessConfig("Something went wrong")));
    },
    showStatus(task) {
      this.statusTask = task;
      this.showPolicyTaskStatus = true;
    },
    refreshTasks(id) {
      this.$store.dispatch("automation/loadPolicyAutomatedTasks", id);
    },
    runTask(pk, enabled) {
      if (!enabled) {
        this.$q.notify(notifyErrorConfig("Task cannot be run when it's disabled. Enable it first."));
        return;
      }
      this.$store
        .dispatch("automation/runPolicyTask", pk)
        .then(r => this.$q.notify(notifySuccessConfig(r.data)))
        .catch(() => this.$q.notify(notifyErrorConfig("Something went wrong")));
    },
    deleteTask(name, pk) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete ${name} task`,
          cancel: true,
          persistent: true
        })
        .onOk(() => {
          this.$store 
            .dispatch("deleteAutoTask", pk)
            .then(r => {
              this.$store.dispatch("automation/loadPolicyAutomatedTasks", this.selectedPolicy);
              this.$q.notify(notifySuccessConfig(r.data));
            })
            .catch(e => this.$q.notify(notifyErrorConfig("Something went wrong")));
        });
    }
  },
  computed: {
    ...mapGetters({
      tasks: "automation/tasks",
      selectedPolicy: "automation/selectedPolicyPk"
    }),
  }
};
</script>

