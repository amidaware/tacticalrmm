<template>
  <div class="q-pa-xs q-ma-xs">
    <q-bar>
      <div class="cursor-pointer non-selectable">
        File
        <q-menu>
          <q-list dense style="min-width: 100px">
            <q-item clickable v-close-popup @click="showAddClientModal = true">
              <q-item-section>Add Client</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showAddSiteModal = true">
              <q-item-section>Add Site</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showEditClientsModal = true">
              <q-item-section>Edit Clients</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showEditSitesModal = true">
              <q-item-section>Edit Sites</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="getLog">
              <q-item-section>Debug Log</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </div>
      <!-- agents -->
      <div class="q-ml-md cursor-pointer non-selectable">
        Agents
        <q-menu auto-close>
          <q-list dense style="min-width: 100px">
            <q-item clickable v-close-popup @click="showUpdateAgentsModal = true">
              <q-item-section>Update Agents</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </div>
      <!-- settings -->
      <div class="q-ml-md cursor-pointer non-selectable">
        Settings
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
            <!-- core settings -->
            <q-item clickable v-close-popup @click="showEditCoreSettingsModal = true">
              <q-item-section>Global Settings</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </div>
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
          <AutomationManager @close="showAutomationManager = false"/>
        </q-dialog>
      </div>
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
    AutomationManager
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
    };
  },
  methods: {
    getLog() {
      this.$store.commit("logs/TOGGLE_LOG_MODAL", true);
    },
    showScriptManager() {
      this.$store.commit("TOGGLE_SCRIPT_MANAGER", true);
    },
    edited() {
      this.$emit("edited");
    }
  }
};
</script>
