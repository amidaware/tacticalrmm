<template>
  <div class="q-pa-xs q-ma-xs">
    <q-bar>
      <q-btn-group flat>
        <q-btn size="md" dense no-caps flat label="File">
          <q-menu>
            <q-list dense style="min-width: 100px">
              <q-item clickable>
                <q-item-section>Add</q-item-section>
                <q-item-section side>
                  <q-icon name="keyboard_arrow_right" />
                </q-item-section>
                <q-menu anchor="top right" self="top left">
                  <q-list dense style="min-width: 100px">
                    <q-item clickable v-close-popup @click="showAddClientModal">
                      <q-item-section>Client</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="showAddSiteModal">
                      <q-item-section>Site</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-close-popup @click="showUploadMesh = true">
                <q-item-section>Upload MeshAgent</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showAuditManager = true">
                <q-item-section>Audit Log</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showDebugLog = true">
                <q-item-section>Debug Log</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- view -->
        <q-btn size="md" dense no-caps flat label="View">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showPendingActions = true">
                <q-item-section>Pending Actions</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- agents -->
        <q-btn size="md" dense no-caps flat label="Agents">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showInstallAgent = true">
                <q-item-section>Install Agent</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showDeployment = true">
                <q-item-section>Manage Deployments</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showUpdateAgentsModal = true">
                <q-item-section>Update Agents</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>

        <!-- settings -->
        <q-btn size="md" dense no-caps flat label="Settings">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <!-- clients manager -->
              <q-item clickable v-close-popup @click="showClientsManager">
                <q-item-section>Clients Manager</q-item-section>
              </q-item>
              <!-- script manager -->
              <q-item clickable v-close-popup @click="showScriptManager = true">
                <q-item-section>Script Manager</q-item-section>
              </q-item>
              <!-- automation manager -->
              <q-item clickable v-close-popup @click="showAutomationManager">
                <q-item-section>Automation Manager</q-item-section>
              </q-item>
              <!-- alerts manager -->
              <q-item clickable v-close-popup @click="showAlertsManager">
                <q-item-section>Alerts Manager</q-item-section>
              </q-item>
              <!-- admin manager -->
              <q-item clickable v-close-popup @click="showAdminManager = true">
                <q-item-section>User Administration</q-item-section>
              </q-item>
              <!-- core settings -->
              <q-item clickable v-close-popup @click="showEditCoreSettingsModal = true">
                <q-item-section>Global Settings</q-item-section>
              </q-item>
              <!-- code sign -->
              <q-item v-if="!noCodeSigning" clickable v-close-popup @click="showCodeSign = true">
                <q-item-section>Code Signing</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- tools -->
        <q-btn size="md" dense no-caps flat label="Tools">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <!-- bulk command -->
              <q-item clickable v-close-popup @click="showBulkActionModal('command')">
                <q-item-section>Bulk Command</q-item-section>
              </q-item>
              <!-- bulk script -->
              <q-item clickable v-close-popup @click="showBulkActionModal('script')">
                <q-item-section>Bulk Script</q-item-section>
              </q-item>
              <!-- bulk patch management -->
              <q-item clickable v-close-popup @click="showBulkActionModal('scan')">
                <q-item-section>Bulk Patch Management</q-item-section>
              </q-item>
              <!-- server maintenance -->
              <q-item clickable v-close-popup @click="showServerMaintenance = true">
                <q-item-section>Server Maintenance</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </q-btn-group>
      <q-space />
      <!-- edit core settings modal -->
      <q-dialog v-model="showEditCoreSettingsModal">
        <EditCoreSettings @close="showEditCoreSettingsModal = false" />
      </q-dialog>
      <!-- debug log modal -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showDebugLog" maximized transition-show="slide-up" transition-hide="slide-down">
          <LogModal @close="showDebugLog = false" />
        </q-dialog>
      </div>
      <!-- pending actions modal -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showPendingActions">
          <PendingActions @close="showPendingActions = false" />
        </q-dialog>
      </div>
      <!-- audit manager -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showAuditManager" maximized transition-show="slide-up" transition-hide="slide-down">
          <AuditManager @close="showAuditManager = false" />
        </q-dialog>
      </div>
      <!-- Install Agents -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showInstallAgent">
          <InstallAgent @close="showInstallAgent = false" />
        </q-dialog>
      </div>
      <!-- Update Agents Modal -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showUpdateAgentsModal" maximized transition-show="slide-up" transition-hide="slide-down">
          <UpdateAgents @close="showUpdateAgentsModal = false" @edited="edited" />
        </q-dialog>
      </div>
      <!-- Script Manager -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showScriptManager">
          <ScriptManager @close="showScriptManager = false" />
        </q-dialog>
      </div>
      <!-- Admin Manager -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showAdminManager">
          <AdminManager @close="showAdminManager = false" />
        </q-dialog>
      </div>
      <!-- Upload new mesh agent -->
      <q-dialog v-model="showUploadMesh">
        <UploadMesh @close="showUploadMesh = false" />
      </q-dialog>
      <!-- Bulk action modal -->
      <q-dialog v-model="showBulkAction" @hide="closeBulkActionModal" position="top">
        <BulkAction :mode="bulkMode" @close="closeBulkActionModal" />
      </q-dialog>
      <!-- Agent Deployment -->
      <q-dialog v-model="showDeployment">
        <Deployment @close="showDeployment = false" />
      </q-dialog>
      <!-- Server Maintenance -->
      <q-dialog v-model="showServerMaintenance">
        <ServerMaintenance @close="showMaintenance = false" />
      </q-dialog>
      <!-- Code Sign -->
      <q-dialog v-model="showCodeSign">
        <CodeSign @close="showCodeSign = false" />
      </q-dialog>
    </q-bar>
  </div>
</template>

<script>
import LogModal from "@/components/modals/logs/LogModal";
import PendingActions from "@/components/modals/logs/PendingActions";
import ClientsManager from "@/components/ClientsManager";
import ClientsForm from "@/components/modals/clients/ClientsForm";
import SitesForm from "@/components/modals/clients/SitesForm";
import UpdateAgents from "@/components/modals/agents/UpdateAgents";
import ScriptManager from "@/components/ScriptManager";
import EditCoreSettings from "@/components/modals/coresettings/EditCoreSettings";
import AlertsManager from "@/components/AlertsManager";
import AutomationManager from "@/components/automation/AutomationManager";
import AdminManager from "@/components/AdminManager";
import InstallAgent from "@/components/modals/agents/InstallAgent";
import UploadMesh from "@/components/modals/core/UploadMesh";
import AuditManager from "@/components/AuditManager";
import BulkAction from "@/components/modals/agents/BulkAction";
import Deployment from "@/components/Deployment";
import ServerMaintenance from "@/components/modals/core/ServerMaintenance";
import CodeSign from "@/components/modals/coresettings/CodeSign";

export default {
  name: "FileBar",
  components: {
    LogModal,
    PendingActions,
    UpdateAgents,
    ScriptManager,
    EditCoreSettings,
    InstallAgent,
    UploadMesh,
    AdminManager,
    AuditManager,
    BulkAction,
    Deployment,
    ServerMaintenance,
    CodeSign,
  },
  data() {
    return {
      showServerMaintenance: false,
      showUpdateAgentsModal: false,
      showEditCoreSettingsModal: false,
      showAdminManager: false,
      showInstallAgent: false,
      showUploadMesh: false,
      showAuditManager: false,
      showBulkAction: false,
      showPendingActions: false,
      bulkMode: null,
      showDeployment: false,
      showDebugLog: false,
      showScriptManager: false,
      showCodeSign: false,
    };
  },
  computed: {
    noCodeSigning() {
      return this.$store.state.noCodeSign;
    },
  },
  methods: {
    showBulkActionModal(mode) {
      this.bulkMode = mode;
      this.showBulkAction = true;
    },
    closeBulkActionModal() {
      this.bulkMode = null;
      this.showBulkAction = false;
    },
    showAutomationManager() {
      this.$q.dialog({
        component: AutomationManager,
        parent: this,
      });
    },
    showAlertsManager() {
      this.$q.dialog({
        component: AlertsManager,
        parent: this,
      });
    },
    showClientsManager() {
      this.$q.dialog({
        component: ClientsManager,
        parent: this,
      });
    },
    showAddClientModal() {
      this.$q.dialog({
        component: ClientsForm,
        parent: this,
      });
    },
    showAddSiteModal() {
      this.$q.dialog({
        component: SitesForm,
        parent: this,
      });
    },
    edited() {
      this.$emit("edited");
    },
  },
};
</script>
