<template>
  <div class="q-pa-xs q-ma-xs">
    <q-bar>
      <q-btn-group flat>
        <q-btn size="md" dense no-caps flat label="File">
          <q-menu>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showAddClientModal = true">
                <q-item-section>Add Client</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showAddSiteModal = true">
                <q-item-section>Add Site</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showUploadMesh = true">
                <q-item-section>Upload MeshAgent</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="getLog">
                <q-item-section>Debug Log</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- edit -->
        <q-btn size="md" dense no-caps flat label="Edit">
          <q-menu>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showEditClientsModal = true">
                <q-item-section>Edit Clients</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showEditSitesModal = true">
                <q-item-section>Edit Sites</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- view -->
        <q-btn size="md" dense no-caps flat label="View">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showPendingActions">
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
              <q-item clickable v-close-popup @click="showScriptManager">
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
      </q-btn-group>
      <q-space />
      <!-- add client modal -->
      <q-dialog v-model="showAddClientModal">
        <AddClient @close="showAddClientModal = false" />
      </q-dialog>
      <q-dialog v-model="showEditClientsModal">
        <EditClients @close="showEditClientsModal = false" @edited="edited" />
      </q-dialog>
      <!-- add site modal -->
      <q-dialog v-model="showAddSiteModal">
        <AddSite @close="showAddSiteModal = false" :clients="clients" />
      </q-dialog>
      <q-dialog v-model="showEditSitesModal">
        <EditSites @close="showEditSitesModal = false" @edited="edited" />
      </q-dialog>
      <!-- edit core settings modal -->
      <q-dialog v-model="showEditCoreSettingsModal">
        <EditCoreSettings @close="showEditCoreSettingsModal = false" />
      </q-dialog>
      <!-- debug log modal -->
      <LogModal />
      <!-- Install Agents -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showInstallAgent">
          <InstallAgent @close="showInstallAgent = false" />
        </q-dialog>
      </div>
      <!-- Update Agents Modal -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog
          v-model="showUpdateAgentsModal"
          maximized
          transition-show="slide-up"
          transition-hide="slide-down"
        >
          <UpdateAgents @close="showUpdateAgentsModal = false" />
        </q-dialog>
      </div>
      <!-- Script Manager -->
      <ScriptManager />

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
    </q-bar>
  </div>
</template>

<script>
import LogModal from "@/components/modals/logs/LogModal";
import AddClient from "@/components/modals/clients/AddClient";
import EditClients from "@/components/modals/clients/EditClients";
import AddSite from "@/components/modals/clients/AddSite";
import EditSites from "@/components/modals/clients/EditSites";
import UpdateAgents from "@/components/modals/agents/UpdateAgents";
import ScriptManager from "@/components/ScriptManager";
import EditCoreSettings from "@/components/modals/coresettings/EditCoreSettings";
import AutomationManager from "@/components/automation/AutomationManager";
import AdminManager from "@/components/AdminManager";
import InstallAgent from "@/components/modals/agents/InstallAgent";
import UploadMesh from "@/components/modals/core/UploadMesh";

export default {
  name: "FileBar",
  components: {
    LogModal,
    AddClient,
    EditClients,
    AddSite,
    EditSites,
    UpdateAgents,
    ScriptManager,
    EditCoreSettings,
    AutomationManager,
    InstallAgent,
    UploadMesh,
    AdminManager,
  },
  props: ["clients"],
  data() {
    return {
      showAddClientModal: false,
      showEditClientsModal: false,
      showAddSiteModal: false,
      showEditSitesModal: false,
      showUpdateAgentsModal: false,
      showEditCoreSettingsModal: false,
      showAutomationManager: false,
      showAdminManager: false,
      showInstallAgent: false,
      showUploadMesh: false,
    };
  },
  methods: {
    getLog() {
      this.$store.commit("logs/TOGGLE_LOG_MODAL", true);
    },
    showPendingActions() {
      const data = { action: true, agentpk: null, hostname: null };
      this.$store.commit("logs/TOGGLE_PENDING_ACTIONS", data);
    },
    showScriptManager() {
      this.$store.commit("TOGGLE_SCRIPT_MANAGER", true);
    },
    edited() {
      this.$emit("edited");
    },
  },
};
</script>
