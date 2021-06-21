<template>
  <div class="q-pa-none">
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
      <q-tab name="summary" icon="fas fa-info-circle" size="xs" label="Summary" />
      <q-tab name="checks" icon="fas fa-check-double" label="Checks" />
      <q-tab name="tasks" icon="fas fa-tasks" label="Tasks" />
      <q-tab name="patches" icon="system_update" label="Patches" />
      <q-tab name="software" icon="fab fa-windows" label="Software" />
      <q-tab name="history" icon="history" label="History" />
      <q-tab name="notes" icon="far fa-sticky-note" label="Notes" />
      <q-tab name="assets" icon="fas fa-barcode" label="Assets" />
      <q-tab name="debug" icon="bug_report" label="Debug" />
      <q-tab name="audit" icon="travel_explore" label="Audit" />
    </q-tabs>
    <q-separator />
    <q-tab-panels v-model="subtab" :animated="false">
      <q-tab-panel name="summary" class="q-pb-none q-pt-xs">
        <SummaryTab />
      </q-tab-panel>
      <q-tab-panel name="checks" class="q-pb-xs q-pt-none">
        <ChecksTab @edit="$emit('edit')" />
      </q-tab-panel>
      <q-tab-panel name="tasks" class="q-pb-xs q-pt-none">
        <AutomatedTasksTab />
      </q-tab-panel>
      <q-tab-panel name="patches" class="q-pb-xs q-pt-none">
        <WindowsUpdates />
      </q-tab-panel>
      <q-tab-panel name="software" class="q-pb-xs q-pt-none">
        <SoftwareTab />
      </q-tab-panel>
      <q-tab-panel name="history" class="q-pb-xs q-pt-none">
        <HistoryTab />
      </q-tab-panel>
      <q-tab-panel name="notes" class="q-pb-xs q-pt-none">
        <NotesTab />
      </q-tab-panel>
      <q-tab-panel name="assets" class="q-pb-xs q-pt-none">
        <AssetsTab />
      </q-tab-panel>
      <q-tab-panel name="debug" class="q-pa-none">
        <DebugTab />
      </q-tab-panel>
      <q-tab-panel name="audit" class="q-pa-none">
        <AuditTab />
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script>
import SummaryTab from "@/components/SummaryTab";
import ChecksTab from "@/components/ChecksTab";
import AutomatedTasksTab from "@/components/AutomatedTasksTab";
import WindowsUpdates from "@/components/WindowsUpdates";
import SoftwareTab from "@/components/SoftwareTab";
import HistoryTab from "@/components/agents/HistoryTab";
import AuditTab from "@/components/agents/AuditTab";
import DebugTab from "@/components/agents/DebugTab";
import AssetsTab from "@/components/AssetsTab";
import NotesTab from "@/components/NotesTab";

export default {
  name: "SubTableTabs",
  emits: ["edit"],
  components: {
    SummaryTab,
    ChecksTab,
    AutomatedTasksTab,
    WindowsUpdates,
    SoftwareTab,
    HistoryTab,
    AuditTab,
    DebugTab,
    AssetsTab,
    NotesTab,
  },
  data() {
    return {
      subtab: "summary",
    };
  },
};
</script>

