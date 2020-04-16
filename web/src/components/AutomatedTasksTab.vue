<template>
  <div v-if="!this.selectedAgentPk">No agent selected</div>
  <div v-else-if="Object.keys(automatedTasks).length === 0">No Tasks</div>
  <div class="row" v-else>
    <div class="col-12">
      <q-btn size="sm" color="grey-5" icon="fas fa-plus" label="Add Task" text-color="black">
        <q-menu>
          <q-list dense style="min-width: 200px">
            <q-item clickable v-close-popup @click="showAddAutomatedTask = true">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-tasks" />
              </q-item-section>
              <q-item-section>Automated Task</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-btn>
      <q-btn dense flat push @click="refreshTasks(automatedTasks.pk)" icon="refresh" />
      <template v-if="tasks === undefined || tasks.length === 0">
        <p>No Tasks</p>
      </template>
      <template v-else>
        <q-table
          dense
          class="autotasks-tbl-sticky"
          :data="tasks"
          :columns="columns"
          :row-key="row => row.id"
          binary-state-sort
          :pagination.sync="pagination"
          hide-bottom
        >
          <!-- header slots -->
          <template v-slot:header-cell-enabled="props">
            <q-th auto-width :props="props">
              <small>Enabled</small>
            </q-th>
          </template>
          <!-- body slots -->
          <template slot="body" slot-scope="props" :props="props">
            <q-tr @contextmenu="editTaskPk = props.row.id">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="runTask(props.row.id)">
                    <q-item-section side>
                      <q-icon name="play_arrow" />
                    </q-item-section>
                    <q-item-section>Run task now</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="showEditAutomatedTask = true">
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
                  @input="taskEnableorDisable(props.row.id, props.row.enabled)"
                  v-model="props.row.enabled"
                />
              </q-td>
              <q-td>{{ props.row.name }}</q-td>
              <q-td v-if="props.row.retcode || props.row.stdout || props.row.stderr">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="scriptMoreInfo(props.row)"
                >output</span>
              </q-td>
              <q-td v-else>Awaiting output</q-td>
              <q-td v-if="props.row.last_run">{{ props.row.last_run }}</q-td>
              <q-td v-else>Has not run yet</q-td>
              <q-td>{{ props.row.schedule }}</q-td>
              <q-td>{{ props.row.assigned_check }}</q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showAddAutomatedTask" position="top">
      <AddAutomatedTask @close="showAddAutomatedTask = false" />
    </q-dialog>

    <q-dialog v-model="showScriptOutput">
      <ScriptOutput @close="showScriptOutput = false; scriptInfo = {}" :scriptInfo="scriptInfo" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import AddAutomatedTask from "@/components/modals/automation/AddAutomatedTask";
import ScriptOutput from "@/components/modals/checks/ScriptOutput";

export default {
  name: "AutomatedTasksTab",
  components: { AddAutomatedTask, ScriptOutput },
  mixins: [mixins],
  data() {
    return {
      showAddAutomatedTask: false,
      showEditAutomatedTask: false,
      showScriptOutput: false,
      editTaskPk: null,
      showScriptOutput: false,
      scriptInfo: {},
      columns: [
        { name: "enabled", align: "left", field: "enabled" },
        { name: "name", label: "Name", field: "name", align: "left" },
        {
          name: "moreinfo",
          label: "More Info",
          field: "more_info",
          align: "left"
        },
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
      const data = { enableordisable: action };
      axios
        .patch(`/automation/${pk}/automatedtasks/`, data)
        .then(r => {
          this.$store.dispatch("loadAutomatedTasks", this.automatedTasks.pk);
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError("Something went wrong"));
    },
    refreshTasks(id) {
      this.$store.dispatch("loadAutomatedTasks", id);
    },
    scriptMoreInfo(props) {
      this.scriptInfo = props;
      this.showScriptOutput = true;
    },
    runTask(pk) {
      axios
        .get(`/automation/runwintask/${pk}/`)
        .then(r => this.notifySuccess(r.data))
        .catch(() => this.notifyError("Something went wrong"));
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
          axios
            .delete(`/automation/${pk}/automatedtasks/`)
            .then(r => {
              this.$store.dispatch(
                "loadAutomatedTasks",
                this.automatedTasks.pk
              );
              this.$store.dispatch("loadChecks", this.automatedTasks.pk);
              this.notifySuccess(r.data);
            })
            .catch(e => this.notifyError("Something went wrong"));
        });
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    ...mapState({
      automatedTasks: state => state.automatedTasks
    }),
    tasks() {
      return this.automatedTasks.autotasks;
    }
  }
};
</script>

<style lang="stylus">
.autotasks-tbl-sticky {
  .q-table__middle {
    max-height: 25vh;
  }

  .q-table__top, .q-table__bottom, thead tr:first-child th {
    background-color: #f5f4f2;
  }

  thead tr:first-child th {
    position: sticky;
    top: 0;
    opacity: 1;
    z-index: 1;
  }
}
</style>

