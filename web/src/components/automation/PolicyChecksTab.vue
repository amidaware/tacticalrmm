<template>
  <div class="row">
    <div class="col-12">
      <q-btn v-if="!!selectedPolicy" size="sm" color="grey-5" icon="fas fa-plus" label="Add Check" text-color="black">
        <q-menu>
          <q-list dense style="min-width: 200px">
            <q-item clickable v-close-popup @click="showAddDialog('DiskSpaceCheck')">
              <q-item-section side>
                <q-icon size="xs" name="far fa-hdd" />
              </q-item-section>
              <q-item-section>Disk Space Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('PingCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-network-wired" />
              </q-item-section>
              <q-item-section>Ping Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('CpuLoadCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-microchip" />
              </q-item-section>
              <q-item-section>CPU Load Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('MemCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-memory" />
              </q-item-section>
              <q-item-section>Memory Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('WinSvcCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-cogs" />
              </q-item-section>
              <q-item-section>Windows Service Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('ScriptCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-terminal" />
              </q-item-section>
              <q-item-section>Script Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddDialog('EventLogCheck')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-clipboard-list" />
              </q-item-section>
              <q-item-section>Event Log Check</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-btn>
      <q-btn v-if="!!selectedPolicy" dense flat push @click="getChecks" icon="refresh" />
      <q-table
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="tabs-tbl-sticky"
        :rows="checks"
        :columns="columns"
        v-model:pagination="pagination"
        :rows-per-page-options="[0]"
        row-key="id"
        binary-state-sort
        dense
        hide-pagination
        virtual-scroll
      >
        <!-- No data Slot -->
        <template v-slot:no-data>
          <div class="full-width row flex-center q-gutter-sm">
            <span v-if="!selectedPolicy">Click on a policy to see the checks</span>
            <span v-else>There are no checks added to this policy</span>
          </div>
        </template>
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
        <template v-slot:header-cell-statusicon="props">
          <q-th auto-width :props="props"></q-th>
        </template>
        <!-- body slots -->
        <template v-slot:body="props">
          <q-tr :props="props" class="cursor-pointer" @dblclick="showEditDialog(props.row)">
            <!-- context menu -->
            <q-menu context-menu>
              <q-list dense style="min-width: 200px">
                <q-item clickable v-close-popup @click="showEditDialog(props.row)">
                  <q-item-section side>
                    <q-icon name="edit" />
                  </q-item-section>
                  <q-item-section>Edit</q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="deleteCheck(props.row)">
                  <q-item-section side>
                    <q-icon name="delete" />
                  </q-item-section>
                  <q-item-section>Delete</q-item-section>
                </q-item>

                <q-separator></q-separator>

                <q-item clickable v-close-popup @click="showPolicyStatus(props.row)">
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
                @update:model-value="checkAlert(props.row.id, 'Text', props.row.text_alert)"
                v-model="props.row.text_alert"
              />
            </q-td>
            <q-td>
              <q-checkbox
                dense
                @update:model-value="checkAlert(props.row.id, 'Email', props.row.email_alert)"
                v-model="props.row.email_alert"
              />
            </q-td>
            <q-td>
              <q-checkbox
                dense
                @update:model-value="checkAlert(props.row.id, 'Dashboard', props.row.dashboard_alert)"
                v-model="props.row.dashboard_alert"
              />
            </q-td>
            <q-td>{{ props.row.readable_desc }}</q-td>
            <q-td>
              <span
                style="cursor: pointer; text-decoration: underline"
                @click="showPolicyStatus(props.row)"
                class="status-cell text-primary"
                >See Status</span
              >
            </q-td>
            <q-td v-if="props.row.assignedtask !== null && props.row.assignedtask.length === 1">{{
              props.row.assignedtask[0].name
            }}</q-td>
            <q-td v-else-if="props.row.assignedtask">{{ props.row.assignedtask.length }} Tasks</q-td>
            <q-td v-else></q-td>
          </q-tr>
        </template>
      </q-table>
    </div>

    <!-- add/edit modals -->
    <q-dialog v-model="showDialog" @hide="hideDialog">
      <component
        v-if="dialogComponent !== null"
        :is="dialogComponent"
        @close="hideDialog"
        :policypk="selectedPolicy"
        :checkpk="editCheckPK"
        :mode="!!editCheckPK ? 'edit' : 'add'"
      />
    </q-dialog>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import PolicyStatus from "@/components/automation/modals/PolicyStatus";
import DiskSpaceCheck from "@/components/modals/checks/DiskSpaceCheck";
import PingCheck from "@/components/modals/checks/PingCheck";
import CpuLoadCheck from "@/components/modals/checks/CpuLoadCheck";
import MemCheck from "@/components/modals/checks/MemCheck";
import WinSvcCheck from "@/components/modals/checks/WinSvcCheck";
import ScriptCheck from "@/components/modals/checks/ScriptCheck";
import EventLogCheck from "@/components/modals/checks/EventLogCheck";

export default {
  name: "PolicyChecksTab",
  components: {
    DiskSpaceCheck,
    PingCheck,
    CpuLoadCheck,
    MemCheck,
    WinSvcCheck,
    ScriptCheck,
    EventLogCheck,
  },
  mixins: [mixins],
  props: {
    selectedPolicy: !Number,
  },
  data() {
    return {
      checks: [],
      dialogComponent: null,
      showDialog: false,
      editCheckPK: null,
      columns: [
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "dashboardalert", field: "dashboard_alert", align: "left" },
        { name: "desc", field: "readable_desc", label: "Description", align: "left", sortable: true },
        { name: "status", label: "Status", field: "status", align: "left" },
        { name: "assigned_task", label: "Assigned Tasks", field: "assigned_task", align: "left", sortable: true },
      ],
      pagination: {
        rowsPerPage: 0,
        sortBy: "status",
        descending: true,
      },
    };
  },
  watch: {
    selectedPolicy: function (newValue, oldValue) {
      if (newValue !== oldValue) this.getChecks();
    },
  },
  methods: {
    getChecks() {
      this.$q.loading.show();
      this.$axios
        .get(`/automation/${this.selectedPolicy}/policychecks/`)
        .then(r => {
          this.checks = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    checkAlert(id, alert_type, action) {
      this.$q.loading.show();
      const data = {};

      if (alert_type === "Email") {
        data.email_alert = !action;
      } else if (alert_type === "Text") {
        data.text_alert = !action;
      } else {
        data.dashboard_alert = !action;
      }

      data.check_alert = true;
      const act = !action ? "enabled" : "disabled";
      const color = !action ? "positive" : "warning";
      this.$axios
        .patch(`/checks/${id}/check/`, data)
        .then(r => {
          this.$q.loading.hide();
          this.$q.notify({
            color: color,
            icon: "fas fa-check-circle",
            message: `${alert_type} alerts ${act}`,
          });
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    showAddDialog(component) {
      this.dialogComponent = component;
      this.showDialog = true;
    },
    showEditDialog(check) {
      switch (check.check_type) {
        case "diskspace":
          this.dialogComponent = "DiskSpaceCheck";
          break;
        case "ping":
          this.dialogComponent = "PingCheck";
          break;
        case "cpuload":
          this.dialogComponent = "CpuLoadCheck";
          break;
        case "memory":
          this.dialogComponent = "MemCheck";
          break;
        case "winsvc":
          this.dialogComponent = "WinSvcCheck";
          break;
        case "script":
          this.dialogComponent = "ScriptCheck";
          break;
        case "eventlog":
          this.dialogComponent = "EventLogCheck";
          break;
        default:
          return null;
      }
      this.editCheckPK = check.id;
      this.showDialog = true;
    },
    hideDialog() {
      this.getChecks();
      this.showDialog = false;
      this.dialogComponent = null;
      this.editCheckPK = null;
    },
    deleteCheck(check) {
      this.$q
        .dialog({
          title: `Delete ${check.check_type} check?`,
          ok: { label: "Delete", color: "negative" },
          cancel: true,
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/checks/${check.id}/check/`)
            .then(r => {
              this.getChecks();
              this.$q.loading.hide();
              this.notifySuccess("Check Deleted!");
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
    showPolicyStatus(check) {
      this.$q.dialog({
        component: PolicyStatus,
        componentProps: {
          type: "check",
          item: check,
        },
      });
    },
  },
  created() {
    this.getChecks();
  },
};
</script>

