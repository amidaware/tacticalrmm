<template>
  <div v-if="Object.keys(checks).length === 0">No Policy Selected</div>
  <div class="row" v-else>
    <div class="col-12">
      <q-btn 
        size="sm" 
        color="grey-5" 
        icon="fas fa-plus" 
        label="Add Check" 
        text-color="black"
        ref="add"
      >
        <q-menu>
          <q-list dense style="min-width: 200px">
            <q-item clickable v-close-popup @click="showAddDialog('AddDiskSpaceCheck')">
              <q-item-section side>
                <q-icon size="xs" name="far fa-hdd" />
              </q-item-section>
              <q-item-section>Disk Space Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('AddPingCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-network-wired" />
              </q-item-section>
              <q-item-section>Ping Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('AddCpuLoadCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-microchip" />
              </q-item-section>
              <q-item-section>CPU Load Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('AddMemCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-memory" />
              </q-item-section>
              <q-item-section>Memory Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('AddWinSvcCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-cogs" />
              </q-item-section>
              <q-item-section>Windows Service Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('AddScriptCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-terminal" />
              </q-item-section>
              <q-item-section>Script Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('AddEventLogCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-clipboard-list" />
              </q-item-section>
              <q-item-section>Event Log Check</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-btn>
      <q-btn 
        dense 
        flat 
        push 
        @click="onRefresh(checks.id)" 
        icon="refresh"
        ref="refresh"
      />
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
          <template v-slot:body="props">
            <q-tr @contextmenu="editCheckPK = props.row.id" :props="props">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item 
                    clickable 
                    v-close-popup 
                    @click="showEditDialog(props.row.check_type)"
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
                    @click="deleteCheck(props.row.id, props.row.check_type)"
                    id="context-delete"
                  >
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item 
                    clickable 
                    v-close-popup 
                    @click="showPolicyCheckStatusModal(props.row)"
                    id="context-status"
                  >
                    <q-item-section side>
                      <q-icon name="sync" />
                    </q-item-section>
                    <q-item-section>Policy Status</q-item-section>
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
              <q-td>{{ getDescription(props.row) }}</q-td>
              <q-td>
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="showPolicyCheckStatusModal(props.row)"
                  class="status-cell"
                >
                  See Status
                </span>
              </q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>

    <!-- policy status -->
    <q-dialog v-model="showPolicyCheckStatus">
      <PolicyStatus 
        type="check" 
        :item="statusCheck"
        :description="getDescription(statusCheck)"
      />
    </q-dialog>
    
    <!-- add/edit modals -->
    <q-dialog 
      v-model="showDialog"
      @hide="hideDialog">
      <component 
        v-if="dialogComponent !== null"
        :is="dialogComponent" 
        @close="hideDialog" 
        :policypk="checks.id" 
        :editCheckPK="editCheckPK"
      />
    </q-dialog>
  </div>
</template>

<script>
import { mapState, mapGetters } from "vuex";
import mixins, { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";
import PolicyStatus from "@/components/automation/modals/PolicyStatus";
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
import AddEventLogCheck from "@/components/modals/checks/AddEventLogCheck";
import EditEventLogCheck from "@/components/modals/checks/EditEventLogCheck";

export default {
  name: "PolicyChecksTab",
  components: {
    PolicyStatus,
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
    AddEventLogCheck,
    EditEventLogCheck
  },
  mixins: [mixins],
  data() {
    return {
      dialogComponent: null,
      showDialog: false,
      showPolicyCheckStatus: false,
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
      this.$store
        .dispatch("editCheckAlertAction", data)
        .then(r => {
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
    showAddDialog(component) {
      this.dialogComponent = component;
      this.showDialog = true;
    },
    showEditDialog(category) {
      switch (category) {
        case "diskspace":
          this.dialogComponent = "EditDiskSpaceCheck";
          break;
        case "ping":
          this.dialogComponent = "EditPingCheck";
          break;
        case "cpuload":
          this.dialogComponent = "EditCpuLoadCheck";
          break;
        case "memory":
          this.dialogComponent = "EditMemCheck";
          break;
        case "winsvc":
          this.dialogComponent = "EditWinSvcCheck";
          break;
        case "script":
          this.dialogComponent = "EditScriptCheck";
          break;
        case "eventlog":
          this.dialogComponent = "EditEventLogCheck";
          break;
        default:
          return null;
      }

      this.showDialog = true;

    },
    hideDialog(component) {
      this.showDialog = false;
      this.dialogComponent = null;
    },
    deleteCheck(pk, check_type) {
      this.$q
        .dialog({
          title: `Delete ${check_type} check`,
          ok: { label: "Delete", color: "negative" },
          cancel: true,
        })
        .onOk(() => {
          const data = { pk: pk, checktype: check_type };
          this.$store
            .dispatch("deleteCheck", data)
            .then(r => {
              this.$store.dispatch("automation/loadPolicyChecks", this.checks.id);
              this.$q.notify(notifySuccessConfig);
            })
            .catch(e => this.$q.notify(notifyErrorConfig));
        });
    },
    showPolicyCheckStatusModal(check) {
      this.statusCheck = check;
      this.showPolicyCheckStatus = true;
    },
    closePolicyCheckStatusModal() {
      this.showPolicyCheckStatus = false;
      this.statusCheck = {};
    },
    getDescription(check) {
      if (check.check_type === "diskspace")
        return `Disk Space Drive ${check.disk} > ${check.threshold}%`;
      else if (check.check_type === "cpuload")
        return `Avg CPU Load > ${check.cpuload}%`;
      else if (check.check_type === "script")
        return `Script check: ${check.script.name}`;
      else if (check.check_type === "ping")
        return `Ping ${check.name} (${check.ip})`;
      else if (check.check_type === "memory")
        return `Avg memory usage > ${check.threshold}%`;
      else if (check.check_type === "winsvc")
        return `Service Check - ${check.svc_display_name}`;
      else if (check.check_type === "eventlog")
        return `Event Log Check - ${check.desc}`
    }
  },
  computed: {
    ...mapState({
      checks: state => state.automation.checks
    }),
    ...mapGetters({
      allChecks: "automation/allChecks"
    })
  }
};
</script>

