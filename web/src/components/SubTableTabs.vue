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
            <q-tab name="summary" icon="fas fa-server" size="xs" label="Summary" />
            <q-tab name="checks" icon="computer" label="Checks" />
            <q-tab name="patches" label="Patches" />
        </q-tabs>
        <q-separator />
        <q-tab-panels v-model="subtab" :animated="false">
            <q-tab-panel name="summary">
                <SummaryTab />
            </q-tab-panel>
            <q-tab-panel name="checks">
                <ChecksTab />
            </q-tab-panel>
            <q-tab-panel name="patches">
                patches
            </q-tab-panel>
        </q-tab-panels>
    </div>
</template>

<script>
import SummaryTab from '@/components/SummaryTab';
import ChecksTab from '@/components/ChecksTab';
export default {
  name: "SubTableTabs",
  components: {
      SummaryTab,
      ChecksTab
  },
  data() {
      return {
          subtab: 'summary'
      }
  }
};
</script>

