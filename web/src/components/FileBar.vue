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
            <q-item clickable v-close-popup @click="getLog">
              <q-item-section>Debug Log</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </div>
      <q-space />
      <!-- add client modal -->
      <q-dialog v-model="showAddClientModal">
        <AddClient @close="showAddClientModal = false" />
      </q-dialog>
      <!-- add site modal -->
      <q-dialog v-model="showAddSiteModal">
        <AddSite @close="showAddSiteModal = false" :clients=clients />
      </q-dialog>
      <!-- debug log modal -->
      <LogModal />
    </q-bar>
  </div>
</template>

<script>
import LogModal from "@/components/modals/logs/LogModal";
import AddClient from "@/components/modals/clients/AddClient";
import AddSite from "@/components/modals/clients/AddSite";
export default {
  name: "FileBar",
  components: { LogModal, AddClient, AddSite },
  props: ["clients"],
  data() {
    return {
      showAddClientModal: false,
      showAddSiteModal: false
    };
  },
  methods: {
    getLog() {
      this.$store.commit("logs/TOGGLE_LOG_MODAL", true);
    }
  }
};
</script>
