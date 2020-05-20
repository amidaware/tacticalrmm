<template>
  <div v-if="Object.keys(checks).length === 0">No Policy Selected</div>
  <div class="row" v-else>
    <div class="col-12">
      <q-btn size="sm" color="grey-5" icon="fas fa-plus" label="Add Check" text-color="black">
        <q-menu>
          <q-list dense style="min-width: 200px">
            <q-item clickable v-close-popup @click="showAddDiskSpaceCheck = true">
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
      <q-btn dense flat push @click="onRefresh(checks.id)" icon="refresh" />
      <template v-if="allChecks === undefined || allChecks.length === 0">
        <p>No Checks</p>
      </template>
      <template v-else>
        <q-table
          dense
          class="tabs-tbl-sticky"
          :data="allChecks"
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

                  <q-item clickable v-close-popup @click="showPolicyCheckStatusModal(props.row)">
                    <q-item-section side>
                      <q-icon name="remove_red_eye" />
                    </q-item-section>
                    <q-item-section>Status</q-item-section>
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
              <q-td
                v-if="props.row.check_type === 'diskspace'"
              >Disk Space Drive {{ props.row.disk }} > {{props.row.threshold }}%</q-td>
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
              <q-td>
                <q-btn
                  label="See Status"
                  color="primary"
                  dense
                  flat
                  unelevated
                  no-caps
                  @click="showPolicyCheckStatusModal(props.row)"
                  size="sm"
                />
              </q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showAddDiskSpaceCheck">
      <AddDiskSpaceCheck @close="showAddDiskSpaceCheck = false" :policypk="checks.id" />
    </q-dialog>
    <q-dialog v-model="showEditDiskSpaceCheck">
      <EditDiskSpaceCheck
        @close="showEditDiskSpaceCheck = false"
        :editCheckPK="editCheckPK"
        :policypk="checks.id"
      />
    </q-dialog>
    <q-dialog v-model="showAddPingCheck">
      <AddPingCheck @close="showAddPingCheck = false" :policypk="checks.id" />
    </q-dialog>
    <q-dialog v-model="showEditPingCheck">
      <EditPingCheck
        @close="showEditPingCheck = false"
        :editCheckPK="editCheckPK"
        :policypk="checks.id"
      />
    </q-dialog>
    <q-dialog v-model="showAddCpuLoadCheck">
      <AddCpuLoadCheck @close="showAddCpuLoadCheck = false" :policypk="checks.id" />
    </q-dialog>
    <q-dialog v-model="showEditCpuLoadCheck">
      <EditCpuLoadCheck
        @close="showEditCpuLoadCheck = false"
        :editCheckPK="editCheckPK"
        :policypk="checks.id"
      />
    </q-dialog>
    <q-dialog v-model="showAddMemCheck">
      <AddMemCheck @close="showAddMemCheck = false" :policypk="checks.id" />
    </q-dialog>
    <q-dialog v-model="showEditMemCheck">
      <EditMemCheck
        @close="showEditMemCheck = false"
        :editCheckPK="editCheckPK"
        :policypk="checks.id"
      />
    </q-dialog>
    <q-dialog v-model="showAddWinSvcCheck">
      <AddWinSvcCheck @close="showAddWinSvcCheck = false" :policypk="checks.id" />
    </q-dialog>
    <q-dialog v-model="showEditWinSvcCheck">
      <EditWinSvcCheck
        @close="showEditWinSvcCheck = false"
        :editCheckPK="editCheckPK"
        :policypk="checks.id"
      />
    </q-dialog>
    <!-- script check -->
    <q-dialog v-model="showAddScriptCheck">
      <AddScriptCheck @close="showAddScriptCheck = false" :policypk="checks.id" />
    </q-dialog>
    <q-dialog v-model="showEditScriptCheck">
      <EditScriptCheck
        @close="showEditScriptCheck = false"
        :editCheckPK="editCheckPK"
        :policypk="checks.id"
      />
    </q-dialog>
    <!-- event log check -->
    <q-dialog v-model="showAddEventLogCheck">
      <AddEventLogCheck @close="showAddEventLogCheck = false" :policypk="checks.id" />
    </q-dialog>
    <q-dialog v-model="showEditEventLogCheck">
      <EditEventLogCheck
        @close="showEditEventLogCheck = false"
        :editCheckPK="editCheckPK"
        :policypk="checks.id"
      />
    </q-dialog>

    <q-dialog v-model="showPolicyCheckStatus">
      <PolicyCheckStatus :check="statusCheck" @close="closePolicyCheckStatusModal" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";
import AddDiskSpaceCheck from "@/components/modals/checks/AddDiskSpaceCheck";
import EditDiskSpaceCheck from "@/components/modals/checks/EditDiskSpaceCheck";
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
import PolicyCheckStatus from "@/components/automation/modals/PolicyCheckStatus";
import AddEventLogCheck from "@/components/modals/checks/AddEventLogCheck";
import EditEventLogCheck from "@/components/modals/checks/EditEventLogCheck";

export default {
  name: "PolicyChecksTab",
  props: ["policypk"],
  components: {
    AddDiskSpaceCheck,
    EditDiskSpaceCheck,
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
    PolicyCheckStatus,
    AddEventLogCheck,
    EditEventLogCheck
  },
  mixins: [mixins],
  data() {
    return {
      showAddDiskSpaceCheck: false,
      showEditDiskSpaceCheck: false,
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
      showPolicyCheckStatus: false,
      showAddEventLogCheck: false,
      showEditEventLogCheck: false,
      editCheckPK: null,
      statusCheck: {},
      columns: [
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "desc", label: "Description", align: "left" },
        { name: "status", label: "Status", field: "status", align: "left" }
      ],
      pagination: {
        rowsPerPage: 9999
      }
    };
  },
  methods: {
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
      this.$store.dispatch("automation/loadPolicyChecks", id);
    },
    editCheck(category) {
      switch (category) {
        case "diskspace":
          this.showEditDiskSpaceCheck = true;
          break;
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
              this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
              this.notifySuccess("Check was deleted!");
            })
            .catch(e => this.notifyError(e.response.data.error));
        });
    },
    showPolicyCheckStatusModal(check) {
      this.statusCheck = check;
      this.showPolicyCheckStatus = true;
    },
    closePolicyCheckStatusModal() {
      this.showPolicyCheckStatus = false;
      this.statusCheck = {};
    }
  },
  computed: {
    ...mapState({
      checks: state => state.automation.checks
    }),
    allChecks() {
      return [
        ...this.checks.diskchecks,
        ...this.checks.cpuloadchecks,
        ...this.checks.memchecks,
        ...this.checks.scriptchecks,
        ...this.checks.winservicechecks,
        ...this.checks.pingchecks,
        ...this.checks.eventlogchecks
      ];
    }
  }
};
</script>

