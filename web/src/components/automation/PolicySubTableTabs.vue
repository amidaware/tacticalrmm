<template>
  <div class="q-pa-md">
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
      <q-tab name="checks" icon="fas fa-check-double" label="Checks" />
      <q-tab name="tasks" icon="fas fa-tasks" label="Tasks" />
      <q-tab name="patches" icon="system_update" label="Patches" />
    </q-tabs>
    <q-separator />
    <q-tab-panels v-model="subtab" :animated="false">
      <q-tab-panel name="checks">
        <PolicyChecksTab />
      </q-tab-panel>
      <q-tab-panel name="tasks">
        <PolicyAutomatedTasksTab />
      </q-tab-panel>
      <q-tab-panel name="patches">
        <WindowsUpdateForm />
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script>
import PolicyChecksTab from "@/components/automation/PolicyChecksTab";
import PolicyAutomatedTasksTab from "@/components/automation/PolicyAutomatedTasksTab";
import WindowsUpdateForm from "@/components/modals/agents/WindowsUpdateForm";

export default {
  name: "PolicySubTableTabs",
  components: {
    PolicyChecksTab,
    PolicyAutomatedTasksTab,
    WindowsUpdateForm,
  },
  data() {
    return {
      subtab: "checks",
    };
  },
};
</script>

