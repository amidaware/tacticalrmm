<template>
  <div v-if="Object.keys(checks).length === 0">No agent selected</div>
  <div class="row" v-else>
    <div class="col-12">
      <q-btn size="sm" color="grey-5" icon="fas fa-plus" label="Add Check" text-color="black">
        <q-menu>
          <q-list dense style="min-width: 200px">
            <q-item clickable v-close-popup @click="showAddDiskSpaceCheck = true">
              <q-item-section>Disk Space Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddPingCheck = true">
              <q-item-section>Ping Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddCpuLoadCheck = true">
              <q-item-section>CPU Load Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddMemCheck = true">
              <q-item-section>Memory Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddWinSvcCheck = true">
              <q-item-section>Windows Service Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddScriptCheck = true">
              <q-item-section>Script Check</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-btn>
      <q-btn dense flat push @click="onRefresh(checks.pk)" icon="refresh" />
      <template v-if="allChecks === undefined || allChecks.length === 0">
        <p>No Checks</p>
      </template>
      <template v-else>
        <q-markup-table dense>
          <thead>
            <th width="1%" class="text-left">Email</th>
            <th width="1%" class="text-left">SMS</th>
            <th width="1%" class="text-left"></th>
            <th width="20%" class="text-left">Description</th>
            <th width="10%" class="text-left">Status</th>
            <th width="33%" class="text-left">More Info</th>
            <th width="34%" class="text-left">Date / Time</th>
          </thead>

          <tbody>
            <q-tr
              v-for="check in allChecks"
              :key="check.id + check.check_type"
              @contextmenu.native="editCheckPK = check.id"
            >
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="editCheck(check.check_type)">
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="deleteCheck(check.id, check.check_type)">
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
              <td>
                <q-checkbox
                  dense
                  @input="checkAlertAction(check.id, check.check_type, 'email', check.email_alert)"
                  v-model="check.email_alert"
                />
              </td>
              <td>
                <q-checkbox
                  dense
                  @input="checkAlertAction(check.id, check.check_type, 'text', check.text_alert)"
                  v-model="check.text_alert"
                />
              </td>
              <td v-if="check.status === 'pending'"></td>
              <td v-else-if="check.status === 'passing'">
                <q-icon style="font-size: 1.3rem;" color="positive" name="check_circle" />
              </td>
              <td v-else-if="check.status === 'failing'">
                <q-icon style="font-size: 1.3rem;" color="negative" name="error" />
              </td>
              <td
                v-if="check.check_type === 'diskspace'"
              >Disk Space Drive {{ check.disk }} > {{check.threshold }}%</td>
              <td v-else-if="check.check_type === 'cpuload'">Avg CPU Load > {{ check.cpuload }}%</td>
              <td v-else-if="check.check_type === 'script'">Script check: {{ check.script.name }}</td>
              <td v-else-if="check.check_type === 'ping'">Ping {{ check.name }} ({{ check.ip }})</td>
              <td
                v-else-if="check.check_type === 'memory'"
              >Avg memory usage > {{ check.threshold }}%</td>
              <td
                v-else-if="check.check_type === 'winsvc'"
              >Service Check - {{ check.svc_display_name }}</td>
              <td v-if="check.status === 'pending'">Awaiting First Synchronization</td>
              <td v-else-if="check.status === 'passing'">
                <q-badge color="positive">Passing</q-badge>
              </td>
              <td v-else-if="check.status === 'failing'">
                <q-badge color="negative">Failing</q-badge>
              </td>
              <td v-if="check.check_type === 'ping'">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="moreInfo('Ping', check.more_info)"
                >output</span>
              </td>
              <td v-else-if="check.check_type === 'script'">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="moreInfo('Script Check', check.more_info)"
                >output</span>
              </td>
              <td v-else>{{ check.more_info }}</td>
              <td>{{ check.last_run }}</td>
            </q-tr>
          </tbody>
        </q-markup-table>
      </template>
    </div>
    <!-- modals -->
    <q-dialog v-model="showAddDiskSpaceCheck">
      <AddDiskSpaceCheck @close="showAddDiskSpaceCheck = false" :agentpk="checks.pk" />
    </q-dialog>
    <q-dialog v-model="showEditDiskSpaceCheck">
      <EditDiskSpaceCheck
        @close="showEditDiskSpaceCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="checks.pk"
      />
    </q-dialog>
    <q-dialog v-model="showAddPingCheck">
      <AddPingCheck @close="showAddPingCheck = false" :agentpk="checks.pk" />
    </q-dialog>
    <q-dialog v-model="showEditPingCheck">
      <EditPingCheck
        @close="showEditPingCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="checks.pk"
      />
    </q-dialog>
    <q-dialog v-model="showAddCpuLoadCheck">
      <AddCpuLoadCheck @close="showAddCpuLoadCheck = false" :agentpk="checks.pk" />
    </q-dialog>
    <q-dialog v-model="showEditCpuLoadCheck">
      <EditCpuLoadCheck
        @close="showEditCpuLoadCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="checks.pk"
      />
    </q-dialog>

    <q-dialog v-model="showAddMemCheck">
      <AddMemCheck @close="showAddMemCheck = false" :agentpk="checks.pk" />
    </q-dialog>
    <q-dialog v-model="showEditMemCheck">
      <EditMemCheck
        @close="showEditMemCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="checks.pk"
      />
    </q-dialog>

    <q-dialog v-model="showAddWinSvcCheck">
      <AddWinSvcCheck @close="showAddWinSvcCheck = false" :agentpk="checks.pk" />
    </q-dialog>
    <q-dialog v-model="showEditWinSvcCheck">
      <EditWinSvcCheck
        @close="showEditWinSvcCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="checks.pk"
      />
    </q-dialog>
    <!-- script check -->
    <q-dialog v-model="showAddScriptCheck">
      <AddScriptCheck @close="showAddScriptCheck = false" :agentpk="checks.pk" />
    </q-dialog>
    <q-dialog v-model="showEditScriptCheck">
      <EditScriptCheck
        @close="showEditScriptCheck = false"
        :editCheckPK="editCheckPK"
        :agentpk="checks.pk"
      />
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

export default {
  name: "ChecksTab",
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
    EditScriptCheck
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
      editCheckPK: null
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
      this.$store.dispatch("loadChecks", id);
    },
    moreInfo(name, output) {
      this.$q.dialog({
        title: `${name} output`,
        style: "width: 80vw; max-width: 90vw",
        message: `<pre>${output}</pre>`,
        html: true,
        dark: true
      });
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
              this.$store.dispatch("loadChecks", this.checks.pk);
              this.notifySuccess("Check was deleted!");
            })
            .catch(e => this.notifyError(e.response.data.error));
        });
    }
  },
  computed: {
    ...mapState({
      checks: state => state.agentChecks
    }),
    allChecks() {
      return [
        ...this.checks.diskchecks,
        ...this.checks.cpuloadchecks,
        ...this.checks.memchecks,
        ...this.checks.scriptchecks,
        ...this.checks.winservicechecks,
        ...this.checks.pingchecks
      ];
    }
  }
};
</script>

