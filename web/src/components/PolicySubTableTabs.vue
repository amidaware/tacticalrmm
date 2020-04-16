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
    </q-tabs>
    <q-separator />
    <q-tab-panels v-model="subtab" :animated="false">
      <q-tab-panel name="checks">
        <PolicyChecksTab />
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script>
import PolicyChecksTab from '@/components/PolicyChecksTab';

export default {
  name: "PolicySubTableTabs",
  components: {
    PolicyChecksTab,
  },
  data() {
    return {
      subtab: 'checks'
    }
  }
};
</script>

