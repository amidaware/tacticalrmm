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
            <q-item clickable v-close-popup @click="showCheck('add', 'ping')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-network-wired" />
              </q-item-section>
              <q-item-section>Ping Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showCheck('add', 'cpuload')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-microchip" />
              </q-item-section>
              <q-item-section>CPU Load Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showCheck('add', 'memory')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-memory" />
              </q-item-section>
              <q-item-section>Memory Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showCheck('add', 'winsvc')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-cogs" />
              </q-item-section>
              <q-item-section>Windows Service Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showCheck('add', 'script')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-terminal" />
              </q-item-section>
              <q-item-section>Script Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showCheck('add', 'eventlog')">
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
          <template v-slot:header-cell-policystatus="props">
            <q-th auto-width :props="props"></q-th>
          </template>
          <!-- body slots -->
          <template slot="body" slot-scope="props" :props="props">
            <q-tr @contextmenu="checkpk = props.row.id">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item
                    clickable
                    v-close-popup
                    @click="showCheck('edit', props.row.check_type)"
                    v-if="!props.row.managed_by_policy"
                  >
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item
                    clickable
                    v-close-popup
                    @click="deleteCheck(props.row.id, props.row.readable_desc)"
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
              <!-- text alert -->
              <q-td>
                <q-checkbox
                  dense
                  @input="checkAlert(props.row.id, 'Text', props.row.text_alert)"
                  v-model="props.row.text_alert"
                />
              </q-td>
              <!-- email alert -->
              <q-td>
                <q-checkbox
                  dense
                  @input="checkAlert(props.row.id, 'Email', props.row.email_alert)"
                  v-model="props.row.email_alert"
                />
              </q-td>
              <!-- policy check icon -->
              <q-td v-if="props.row.managed_by_policy">
                <q-icon style="font-size: 1.3rem;" name="policy">
                  <q-tooltip>This check is managed by a policy</q-tooltip>
                </q-icon>
              </q-td>
              <q-td v-else-if="props.row.overriden_by_policy">
                <q-icon style="font-size: 1.3rem;" name="remove_circle_outline">
                  <q-tooltip>This check is overriden by a policy</q-tooltip>
                </q-icon>
              </q-td>
              <q-td v-else></q-td>
              <!-- status icon -->
              <q-td v-if="props.row.status === 'pending'"></q-td>
              <q-td v-else-if="props.row.status === 'passing'">
                <q-icon style="font-size: 1.3rem;" color="positive" name="check_circle" />
              </q-td>
              <q-td v-else-if="props.row.status === 'failing'">
                <q-icon style="font-size: 1.3rem;" color="negative" name="error" />
              </q-td>
              <!-- check description -->
              <q-td>{{ props.row.readable_desc }}</q-td>
              <!-- status text -->
              <q-td v-if="props.row.status === 'pending'">Awaiting First Synchronization</q-td>
              <q-td v-else-if="props.row.status === 'passing'">
                <q-badge color="positive">Passing</q-badge>
              </q-td>
              <q-td v-else-if="props.row.status === 'failing'">
                <q-badge color="negative">Failing</q-badge>
              </q-td>
              <!-- more info -->
              <q-td v-if="props.row.check_type === 'ping'">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="pingInfo(props.row.readable_desc, props.row.more_info)"
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
              <q-td
                v-else-if="props.row.check_type === 'cpuload' || props.row.check_type === 'memory'"
              >{{ props.row.history_info }}</q-td>
              <q-td v-else>{{ props.row.more_info }}</q-td>
              <q-td>{{ props.row.last_run }}</q-td>
              <q-td v-if="props.row.assigned_task">{{ props.row.assigned_task.name }}</q-td>
              <q-td v-else></q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showDiskSpaceCheck">
      <DiskSpaceCheck
        @close="showDiskSpaceCheck = false"
        :agentpk="selectedAgentPk"
        :mode="mode"
        :checkpk="checkpk"
      />
    </q-dialog>
    <q-dialog v-model="showMemCheck">
      <MemCheck
        @close="showMemCheck = false"
        :agentpk="selectedAgentPk"
        :mode="mode"
        :checkpk="checkpk"
      />
    </q-dialog>
    <q-dialog v-model="showCpuLoadCheck">
      <CpuLoadCheck
        @close="showCpuLoadCheck = false"
        :agentpk="selectedAgentPk"
        :mode="mode"
        :checkpk="checkpk"
      />
    </q-dialog>
    <q-dialog v-model="showPingCheck">
      <PingCheck
        @close="showPingCheck = false"
        :agentpk="selectedAgentPk"
        :mode="mode"
        :checkpk="checkpk"
      />
    </q-dialog>
    <q-dialog v-model="showWinSvcCheck">
      <WinSvcCheck
        @close="showWinSvcCheck = false"
        :agentpk="selectedAgentPk"
        :mode="mode"
        :checkpk="checkpk"
      />
    </q-dialog>
    <q-dialog v-model="showEventLogCheck">
      <EventLogCheck
        @close="showEventLogCheck = false"
        :agentpk="selectedAgentPk"
        :mode="mode"
        :checkpk="checkpk"
      />
    </q-dialog>
    <q-dialog v-model="showScriptCheck">
      <ScriptCheck
        @close="showScriptCheck = false"
        :agentpk="selectedAgentPk"
        :mode="mode"
        :checkpk="checkpk"
      />
    </q-dialog>
    <q-dialog v-model="showScriptOutput">
      <ScriptOutput @close="showScriptOutput = false; scriptInfo = {}" :scriptInfo="scriptInfo" />
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
import MemCheck from "@/components/modals/checks/MemCheck";
import CpuLoadCheck from "@/components/modals/checks/CpuLoadCheck";
import PingCheck from "@/components/modals/checks/PingCheck";
import WinSvcCheck from "@/components/modals/checks/WinSvcCheck";
import EventLogCheck from "@/components/modals/checks/EventLogCheck";
import ScriptCheck from "@/components/modals/checks/ScriptCheck";
import ScriptOutput from "@/components/modals/checks/ScriptOutput";
import EventLogCheckOutput from "@/components/modals/checks/EventLogCheckOutput";

export default {
  name: "ChecksTab",
  components: {
    DiskSpaceCheck,
    MemCheck,
    CpuLoadCheck,
    PingCheck,
    WinSvcCheck,
    EventLogCheck,
    ScriptCheck,
    ScriptOutput,
    EventLogCheckOutput
  },
  mixins: [mixins],
  data() {
    return {
      mode: "add",
      checkpk: null,
      showDiskSpaceCheck: false,
      showMemCheck: false,
      showCpuLoadCheck: false,
      showPingCheck: false,
      showWinSvcCheck: false,
      showEventLogCheck: false,
      showScriptCheck: false,
      showScriptOutput: false,
      showEventLogOutput: false,
      scriptInfo: {},
      evtlogdata: {},
      columns: [
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "policystatus", align: "left" },
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
      switch (mode) {
        case "add":
          this.mode = "add";
          break;
        case "edit":
          this.mode = "edit";
          break;
      }

      switch (type) {
        case "diskspace":
          this.showDiskSpaceCheck = true;
          break;
        case "memory":
          this.showMemCheck = true;
          break;
        case "cpuload":
          this.showCpuLoadCheck = true;
          break;
        case "ping":
          this.showPingCheck = true;
          break;
        case "winsvc":
          this.showWinSvcCheck = true;
          break;
        case "eventlog":
          this.showEventLogCheck = true;
          break;
        case "script":
          this.showScriptCheck = true;
          break;
      }
    },
    checkAlert(id, alert_type, action) {
      const data = {};
      if (alert_type === "Email") {
        data.email_alert = action;
      } else {
        data.text_alert = action;
      }
      data.check_alert = true;
      const act = action ? "enabled" : "disabled";
      const color = action ? "positive" : "warning";
      axios.patch(`/checks/${id}/check/`, data).then(r => {
        this.$q.notify({
          color: color,
          icon: "fas fa-check-circle",
          message: `${alert_type} alerts ${act}`
        });
      });
    },
    onRefresh(id) {
      this.$store.dispatch("loadChecks", id);
      this.$store.dispatch("loadAutomatedTasks", id);
    },
    pingInfo(desc, output) {
      this.$q.dialog({
        title: desc,
        style: "width: 50vw; max-width: 60vw",
        message: `<pre>${output}</pre>`,
        html: true
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
    deleteCheck(pk, desc) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete ${desc}`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
          persistent: true
        })
        .onOk(() => {
          axios
            .delete(`/checks/${pk}/check/`)
            .then(r => {
              this.$store.dispatch("loadChecks", this.selectedAgentPk);
              this.$store.dispatch("loadAutomatedTasks", this.selectedAgentPk);
              this.notifySuccess(r.data);
            })
            .catch(e => this.notifyError(e.response.data));
        });
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk", "checks"])
  }
};
</script>

