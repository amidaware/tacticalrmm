<template>
  <q-layout container view="hHh lpr lfr">
    <q-header :class="{ 'bg-dark': $q.dark.isActive, 'bg-light': !$q.dark.isActive }">
      <q-tabs
        v-model="subtab"
        dense
        inline-label
        class="text-grey"
        active-color="primary"
        indicator-color="primary"
        align="left"
        narrow-indicator
        no-caps
      >
        <q-tab content-class="min-width" name="summary" icon="fas fa-info-circle" size="xs" label="Summary" />
        <q-tab content-class="min-width" name="checks" icon="fas fa-check-double" label="Checks" />
        <q-tab content-class="min-width" name="tasks" icon="fas fa-tasks" label="Tasks" />
        <q-tab content-class="min-width" name="patches" icon="system_update" label="Patches" />
        <q-tab content-class="min-width" name="software" icon="fab fa-windows" label="Software" />
        <q-tab content-class="min-width" name="history" icon="history" label="History" />
        <q-tab content-class="min-width" name="notes" icon="far fa-sticky-note" label="Notes" />
        <q-tab content-class="min-width" name="assets" icon="fas fa-barcode" label="Assets" />
        <q-tab content-class="min-width" name="debug" icon="bug_report" label="Debug" />
        <q-tab content-class="min-width" name="audit" icon="travel_explore" label="Audit" />
      </q-tabs>
      <q-separator />
    </q-header>
    <q-page-container>
      <q-tab-panels v-model="subtab" :animated="false">
        <q-tab-panel name="summary" class="q-pa-none">
          <SummaryTab />
        </q-tab-panel>
        <q-tab-panel name="checks" class="q-pa-none">
          <ChecksTab />
        </q-tab-panel>
        <q-tab-panel name="tasks" class="q-pa-none">
          <AutomatedTasksTab />
        </q-tab-panel>
        <q-tab-panel name="patches" class="q-pa-none">
          <WinUpdateTab />
        </q-tab-panel>
        <q-tab-panel name="software" class="q-pa-none">
          <SoftwareTab />
        </q-tab-panel>
        <q-tab-panel name="history" class="q-pa-none">
          <HistoryTab />
        </q-tab-panel>
        <q-tab-panel name="notes" class="q-pa-none">
          <NotesTab />
        </q-tab-panel>
        <q-tab-panel name="assets" class="q-pa-none">
          <AssetsTab />
        </q-tab-panel>
        <q-tab-panel name="debug" class="q-pa-none">
          <DebugTab />
        </q-tab-panel>
        <q-tab-panel name="audit" class="q-pa-none">
          <AuditTab />
        </q-tab-panel>
      </q-tab-panels>
    </q-page-container>
  </q-layout>
</template>

<script>
// composition imports
import { ref } from "vue";

// ui imports
import SummaryTab from "@/components/agents/SummaryTab";
import ChecksTab from "@/components/agents/ChecksTab";
import AutomatedTasksTab from "@/components/agents/AutomatedTasksTab";
import WinUpdateTab from "@/components/agents/WinUpdateTab";
import SoftwareTab from "@/components/agents/SoftwareTab";
import HistoryTab from "@/components/agents/HistoryTab";
import AuditTab from "@/components/agents/AuditTab";
import DebugTab from "@/components/agents/DebugTab";
import AssetsTab from "@/components/agents/AssetsTab";
import NotesTab from "@/components/agents/NotesTab";

export default {
  name: "SubTableTabs",
  components: {
    SummaryTab,
    ChecksTab,
    AutomatedTasksTab,
    WinUpdateTab,
    SoftwareTab,
    HistoryTab,
    AuditTab,
    DebugTab,
    AssetsTab,
    NotesTab,
  },
  setup(props) {
    return {
      subtab: ref("summary"),
    };
  },
};
</script>