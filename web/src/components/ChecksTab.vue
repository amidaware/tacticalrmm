<template>
  <div v-if="checks === null">No agent selected</div>
  <div class="row" v-else>
    <div class="col-12">
      <q-btn size="sm" color="grey-5" icon="fas fa-plus" label="Add Check" text-color="black">
        <q-menu>
          <q-list dense style="min-width: 200px">
            <q-item clickable v-close-popup @click="showCheck('add', 'diskspace')">
              <q-item-section side>
                <q-icon size="xs" name="far fa-hdd" />
              </q-item-section>
              <q-item-section>Disk Space Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddPingCheck = true">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-network-wired" />
              </q-item-section>
              <q-item-section>Ping Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddCpuLoadCheck = true">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-microchip" />
              </q-item-section>
              <q-item-section>CPU Load Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddMemCheck = true">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-memory" />
              </q-item-section>
              <q-item-section>Memory Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddWinSvcCheck = true">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-cogs" />
              </q-item-section>
              <q-item-section>Windows Service Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddScriptCheck = true">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-terminal" />
              </q-item-section>
              <q-item-section>Script Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddEventLogCheck = true">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-clipboard-list" />
              </q-item-section>
              <q-item-section>Event Log Check</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-btn>
      <q-btn dense flat push @click="onRefresh(selectedAgentPk)" icon="refresh" />
      <template v-if="checks === undefined || checks.length === 0">
        <p>No Checks</p>
      </template>
      <template v-else>
        <q-table
          dense
          class="tabs-tbl-sticky"
          :data="checks"
          :columns="columns"
          :row-key="row => row.id + row.check_type"
          binary-state-sort
          :pagination.sync="pagination"
          hide-bottom
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
          <template v-slot:header-cell-statusicon="props">
            <q-th auto-width :props="props"></q-th>
          </template>
          <!-- body slots -->
          <template slot="body" slot-scope="props" :props="props">
            <q-tr @contextmenu="editCheckPK = props.row.id">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="editCheck(props.row.check_type)">
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item
                    clickable
                    v-close-popup
                    @click="deleteCheck(props.row.id, props.row.check_type)"
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
                  @input="checkAlertAction(props.row.id, props.row.check_type, 'text', props.row.text_alert)"
                  v-model="props.row.text_alert"
                />
              </q-td>
              <q-td>
                <q-checkbox
                  dense
                  @input="checkAlertAction(props.row.id, props.row.check_type, 'email', props.row.email_alert)"
                  v-model="props.row.email_alert"
                />
              </q-td>
              <q-td v-if="props.row.status === 'pending'"></q-td>
              <q-td v-else-if="props.row.status === 'passing'">
                <q-icon style="font-size: 1.3rem;" color="positive" name="check_circle" />
              </q-td>
              <q-td v-else-if="props.row.status === 'failing'">
                <q-icon style="font-size: 1.3rem;" color="negative" name="error" />
              </q-td>
              <q-td v-if="props.row.check_type === 'diskspace'">{{ props.row.readable_desc }}</q-td>
              <q-td
                v-else-if="props.row.check_type === 'cpuload'"
              >Avg CPU Load > {{ props.row.cpuload }}%</q-td>
              <q-td
                v-else-if="props.row.check_type === 'script'"
              >Script check: {{ props.row.script.name }}</q-td>
              <q-td
                v-else-if="props.row.check_type === 'ping'"
              >Ping {{ props.row.name }} ({{ props.row.ip }})</q-td>
              <q-td
                v-else-if="props.row.check_type === 'memory'"
              >Avg memory usage > {{ props.row.threshold }}%</q-td>
              <q-td
                v-else-if="props.row.check_type === 'winsvc'"
              >Service Check - {{ props.row.svc_display_name }}</q-td>
              <q-td
                v-else-if="props.row.check_type === 'eventlog'"
              >Event Log Check - {{ props.row.desc }}</q-td>
              <q-td v-if="props.row.status === 'pending'">Awaiting First Synchronization</q-td>
              <q-td v-else-if="props.row.status === 'passing'">
                <q-badge color="positive">Passing</q-badge>
              </q-td>
              <q-td v-else-if="props.row.status === 'failing'">
                <q-badge color="negative">Failing</q-badge>
              </q-td>
              <q-td v-if="props.row.check_type === 'ping'">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="moreInfo('Ping', props.row.more_info)"
                >output</span>
              </q-td>
              <q-td v-else-if="props.row.check_type === 'script'">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="scriptMoreInfo(props.row)"
                >output</span>
              </q-td>
              <q-td v-else-if="props.row.check_type === 'eventlog'">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="eventLogMoreInfo(props.row)"
                >output</span>
              </q-td>
              <q-td v-else>{{ props.row.more_info }}</q-td>
              <q-td>{{ props.row.last_run }}</q-td>
              <q-td>{{ props.row.assigned_task }}</q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showDiskSpaceCheck">
      <DiskSpaceCheck @close="showDiskSpaceCheck = false" :agentpk="selectedAgentPk" :mode="mode" />
    </q-dialog>
    <q-dialog v-model="showAddPingCheck">
      <AddPingCheck @close="showAddPingCheck = false" :agentpk="selectedAgentPk" />
    </q-dialog>
    <q-dialog v-model="showEditPingCheck">
      <EditPingCheck
        @close="showEditPingCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="selectedAgentPk"
      />
    </q-dialog>
    <q-dialog v-model="showAddCpuLoadCheck">
      <AddCpuLoadCheck @close="showAddCpuLoadCheck = false" :agentpk="selectedAgentPk" />
    </q-dialog>
    <q-dialog v-model="showEditCpuLoadCheck">
      <EditCpuLoadCheck
        @close="showEditCpuLoadCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="selectedAgentPk"
      />
    </q-dialog>

    <q-dialog v-model="showAddMemCheck">
      <AddMemCheck @close="showAddMemCheck = false" :agentpk="selectedAgentPk" />
    </q-dialog>
    <q-dialog v-model="showEditMemCheck">
      <EditMemCheck
        @close="showEditMemCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="selectedAgentPk"
      />
    </q-dialog>

    <q-dialog v-model="showAddWinSvcCheck">
      <AddWinSvcCheck @close="showAddWinSvcCheck = false" :agentpk="selectedAgentPk" />
    </q-dialog>
    <q-dialog v-model="showEditWinSvcCheck">
      <EditWinSvcCheck
        @close="showEditWinSvcCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="selectedAgentPk"
      />
    </q-dialog>
    <!-- script check -->
    <q-dialog v-model="showAddScriptCheck">
      <AddScriptCheck @close="showAddScriptCheck = false" :agentpk="selectedAgentPk" />
    </q-dialog>
    <q-dialog v-model="showEditScriptCheck">
      <EditScriptCheck
        @close="showEditScriptCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="selectedAgentPk"
      />
    </q-dialog>
    <q-dialog v-model="showScriptOutput">
      <ScriptOutput @close="showScriptOutput = false; scriptInfo = {}" :scriptInfo="scriptInfo" />
    </q-dialog>
    <!-- event log check -->
    <q-dialog v-model="showAddEventLogCheck">
      <AddEventLogCheck @close="showAddEventLogCheck = false" :agentpk="selectedAgentPk" />
    </q-dialog>
    <q-dialog v-model="showEditEventLogCheck">
      <EditEventLogCheck
        @close="showEditEventLogCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="selectedAgentPk"
      />
    </q-dialog>
    <q-dialog v-model="showEventLogOutput">
      <EventLogCheckOutput
        @close="showEventLogOutput = false; evtlogdata = {}"
        :evtlogdata="evtlogdata"
      />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import { mapState, mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import DiskSpaceCheck from "@/components/modals/checks/DiskSpaceCheck";
// refactor below
import AddPingCheck from "@/components/modals/checks/AddPingCheck";
import EditPingCheck from "@/components/modals/checks/EditPingCheck";
import AddCpuLoadCheck from "@/components/modals/checks/AddCpuLoadCheck";
import EditCpuLoadCheck from "@/components/modals/checks/EditCpuLoadCheck";
import AddMemCheck from "@/components/modals/checks/AddMemCheck";
import EditMemCheck from "@/components/modals/checks/EditMemCheck";
import AddWinSvcCheck from "@/components/modals/checks/AddWinSvcCheck";
import EditWinSvcCheck from "@/components/modals/checks/EditWinSvcCheck";
import AddScriptCheck from "@/components/modals/checks/AddScriptCheck";
import EditScriptCheck from "@/components/modals/checks/EditScriptCheck";
import ScriptOutput from "@/components/modals/checks/ScriptOutput";
import AddEventLogCheck from "@/components/modals/checks/AddEventLogCheck";
import EditEventLogCheck from "@/components/modals/checks/EditEventLogCheck";
import EventLogCheckOutput from "@/components/modals/checks/EventLogCheckOutput";

export default {
  name: "ChecksTab",
  components: {
    DiskSpaceCheck,
    AddPingCheck,
    EditPingCheck,
    AddCpuLoadCheck,
    EditCpuLoadCheck,
    AddMemCheck,
    EditMemCheck,
    AddWinSvcCheck,
    EditWinSvcCheck,
    AddScriptCheck,
    EditScriptCheck,
    ScriptOutput,
    AddEventLogCheck,
    EditEventLogCheck,
    EventLogCheckOutput
  },
  mixins: [mixins],
  data() {
    return {
      mode: "add",
      showDiskSpaceCheck: false,
      // refactor below
      showAddPingCheck: false,
      showEditPingCheck: false,
      showAddCpuLoadCheck: false,
      showEditCpuLoadCheck: false,
      showAddMemCheck: false,
      showEditMemCheck: false,
      showAddWinSvcCheck: false,
      showEditWinSvcCheck: false,
      showAddScriptCheck: false,
      showEditScriptCheck: false,
      showScriptOutput: false,
      showAddEventLogCheck: false,
      showEditEventLogCheck: false,
      showEventLogOutput: false,
      editCheckPK: null,
      scriptInfo: {},
      evtlogdata: {},
      columns: [
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "statusicon", align: "left" },
        { name: "desc", label: "Description", align: "left" },
        { name: "status", label: "Status", field: "status", align: "left" },
        {
          name: "moreinfo",
          label: "More Info",
          field: "more_info",
          align: "left"
        },
        {
          name: "datetime",
          label: "Date / Time",
          field: "last_run",
          align: "left"
        },
        { name: "assignedtasks", label: "Assigned Tasks", field: "assigned_task", align: "left" }
      ],
      pagination: {
        rowsPerPage: 9999
      }
    };
  },
  methods: {
    showCheck(mode, type) {
      if (mode === "add") {
        this.mode = "add";
        switch (type) {
          case "diskspace":
            this.showDiskSpaceCheck = true;
            break;
        }
      } else if (mode === "edit") {
        this.mode = "edit";
        switch (type) {
          case "diskspace":
            this.showDiskSpaceCheck = true;
            break;
        }
      }
    },
    checkAlertAction(pk, category, alert_type, alert_action) {
      const action = alert_action ? "enabled" : "disabled";
      const data = {
        alertType: alert_type,
        checkid: pk,
        category: category,
        action: action
      };
      const alertColor = alert_action ? "positive" : "warning";
      axios.patch("/checks/checkalert/", data).then(r => {
        this.$q.notify({
          color: alertColor,
          icon: "fas fa-check-circle",
          message: `${alert_type} alerts ${action}`
        });
      });
    },
    onRefresh(id) {
      this.$store.dispatch("loadChecks", id);
      this.$store.dispatch("loadAutomatedTasks", id);
    },
    moreInfo(name, output) {
      this.$q.dialog({
        title: `${name} output`,
        style: "width: 35vw; max-width: 50vw",
        message: `<pre>${output}</pre>`,
        html: true,
        dark: true
      });
    },
    scriptMoreInfo(props) {
      this.scriptInfo = props;
      this.showScriptOutput = true;
    },
    eventLogMoreInfo(props) {
      this.evtlogdata = props;
      this.showEventLogOutput = true;
    },
    editCheck(category) {
      switch (category) {
        case "ping":
          this.showEditPingCheck = true;
          break;
        case "cpuload":
          this.showEditCpuLoadCheck = true;
          break;
        case "memory":
          this.showEditMemCheck = true;
          break;
        case "winsvc":
          this.showEditWinSvcCheck = true;
          break;
        case "script":
          this.showEditScriptCheck = true;
          break;
        case "eventlog":
          this.showEditEventLogCheck = true;
          break;
        default:
          return false;
      }
    },
    deleteCheck(pk, check_type) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete ${check_type} check`,
          cancel: true,
          persistent: true
        })
        .onOk(() => {
          const data = { pk: pk, checktype: check_type };
          axios
            .delete("checks/deletestandardcheck/", { data: data })
            .then(r => {
              this.$store.dispatch("loadChecks", this.selectedAgentPk);
              this.$store.dispatch("loadAutomatedTasks", this.selectedAgentPk);
              this.notifySuccess("Check was deleted!");
            })
            .catch(e => this.notifyError(e.response.data.error));
        });
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk", "checks"])
  }
};
</script>

