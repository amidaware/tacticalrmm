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
                    <q-item clickable v-close-popup @click="showClientsFormModal('client', 'add')">
                      <q-item-section>Add Client</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="showClientsFormModal('site', 'add')">
                      <q-item-section>Add Site</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable>
                <q-item-section>Delete</q-item-section>
                <q-item-section side>
                  <q-icon name="keyboard_arrow_right" />
                </q-item-section>
                <q-menu anchor="top right" self="top left">
                  <q-list dense style="min-width: 100px">
                    <q-item clickable v-close-popup @click="showClientsFormModal('client', 'delete')">
                      <q-item-section>Delete Client</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="showClientsFormModal('site', 'delete')">
                      <q-item-section>Delete Site</q-item-section>
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
        <!-- edit -->
        <q-btn size="md" dense no-caps flat label="Edit">
          <q-menu>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showClientsFormModal('client', 'edit')">
                <q-item-section>Edit Clients</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showClientsFormModal('site', 'edit')">
                <q-item-section>Edit Sites</q-item-section>
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
              <!-- script manager -->
              <q-item clickable v-close-popup @click="showScriptManager = true">
                <q-item-section>Script Manager</q-item-section>
              </q-item>
              <!-- automation manager -->
              <q-item clickable v-close-popup @click="showAutomationManager = true">
                <q-item-section>Automation Manager</q-item-section>
              </q-item>
              <!-- admin manager -->
              <q-item clickable v-close-popup @click="showAdminManager = true">
                <q-item-section>User Administration</q-item-section>
              </q-item>
              <!-- core settings -->
              <q-item clickable v-close-popup @click="showEditCoreSettingsModal = true">
                <q-item-section>Global Settings</q-item-section>
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
      <!-- client form modal -->
      <q-dialog v-model="showClientFormModal" @hide="closeClientsFormModal">
        <ClientsForm @close="closeClientsFormModal" :op="clientOp" @edited="edited" />
      </q-dialog>
      <!-- site form modal -->
      <q-dialog v-model="showSiteFormModal" @hide="closeClientsFormModal">
        <SitesForm @close="closeClientsFormModal" :op="clientOp" @edited="edited" />
      </q-dialog>
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
      <!-- Automation Manager -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showAutomationManager">
          <AutomationManager @close="showAutomationManager = false" />
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
    </q-bar>
  </div>
</template>

<script>
import LogModal from "@/components/modals/logs/LogModal";
import PendingActions from "@/components/modals/logs/PendingActions";
import ClientsForm from "@/components/modals/clients/ClientsForm";
import SitesForm from "@/components/modals/clients/SitesForm";
import UpdateAgents from "@/components/modals/agents/UpdateAgents";
import ScriptManager from "@/components/ScriptManager";
import EditCoreSettings from "@/components/modals/coresettings/EditCoreSettings";
import AutomationManager from "@/components/automation/AutomationManager";
import AdminManager from "@/components/AdminManager";
import InstallAgent from "@/components/modals/agents/InstallAgent";
import UploadMesh from "@/components/modals/core/UploadMesh";
import AuditManager from "@/components/AuditManager";
import BulkAction from "@/components/modals/agents/BulkAction";
import Deployment from "@/components/Deployment";
import ServerMaintenance from "@/components/modals/core/ServerMaintenance";

export default {
  name: "FileBar",
  components: {
    LogModal,
    PendingActions,
    ClientsForm,
    SitesForm,
    UpdateAgents,
    ScriptManager,
    EditCoreSettings,
    AutomationManager,
    InstallAgent,
    UploadMesh,
    AdminManager,
    AuditManager,
    BulkAction,
    Deployment,
    ServerMaintenance,
  },
  props: ["clients"],
  data() {
    return {
      showServerMaintenance: false,
      showClientFormModal: false,
      showSiteFormModal: false,
      clientOp: null,
      showUpdateAgentsModal: false,
      showEditCoreSettingsModal: false,
      showAutomationManager: false,
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
    };
  },
  methods: {
    showClientsFormModal(type, op) {
      this.clientOp = op;

      if (type === "client") {
        this.showClientFormModal = true;
      } else if (type === "site") {
        this.showSiteFormModal = true;
      }
    },
    closeClientsFormModal() {
      this.clientOp = null;
      this.showClientFormModal = null;
      this.showSiteFormModal = null;
    },
    showBulkActionModal(mode) {
      this.bulkMode = mode;
      this.showBulkAction = true;
    },
    closeBulkActionModal() {
      this.bulkMode = null;
      this.showBulkAction = false;
    },
    edited() {
      this.$emit("edited");
    },
  },
};
</script>
