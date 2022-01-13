<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else-if="!summary && loading" class="q-pa-md flex flex-center">
    <q-circular-progress indeterminate size="50px" color="primary" class="q-ma-md" />
  </div>
  <div v-else-if="summary" class="q-pa-sm">
    <q-bar dense style="background-color: transparent">
      <q-btn dense flat size="md" class="q-mr-sm" icon="refresh" @click="refreshSummary" />
      <b>{{ summary.hostname }}</b>
      <span v-if="summary.maintenance_mode"> &bull; <q-badge color="green"> Maintenance Mode </q-badge> </span>
      &bull; {{ summary.operating_system }} &bull; Agent v{{ summary.version }}
      <q-space />
      <q-btn
        dense
        flat
        label="Popout"
        icon="open_in_new"
        size="md"
        no-caps
        class="q-mr-sm"
        @click="openAgentWindow(selectedAgent)"
      />
      <q-btn
        dense
        flat
        label="Take Control"
        icon="computer"
        size="md"
        no-caps
        class="q-mr-sm"
        @click="runTakeControl(selectedAgent)"
      />
      <q-btn-dropdown dense flat size="md" no-caps label="Actions">
        <AgentActionMenu :agent="summary" />
      </q-btn-dropdown>
    </q-bar>
    <q-separator class="q-mt-sm" />
    <div class="row">
      <div class="col-4">
        <!-- left -->
        <span class="text-subtitle2 text-bold">Hardware Details</span>
        <q-list dense>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-desktop" />
            </q-item-section>
            <q-item-section>{{ summary.make_model }}</q-item-section>
          </q-item>
          <q-item v-for="(cpu, i) in summary.cpu_model" :key="cpu + i">
            <q-item-section avatar>
              <q-icon name="fas fa-microchip" />
            </q-item-section>
            <q-item-section>{{ cpu }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-memory" />
            </q-item-section>
            <q-item-section>{{ summary.total_ram }} GB RAM</q-item-section>
          </q-item>

          <!-- physical disks -->
          <q-item v-for="(disk, i) in summary.physical_disks" :key="disk + i">
            <q-item-section avatar>
              <q-icon name="far fa-hdd" />
            </q-item-section>
            <q-item-section>{{ disk }}</q-item-section>
          </q-item>
          <!-- graphics -->
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-tv" />
            </q-item-section>
            <q-item-section>{{ summary.graphics }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-globe-americas" />
            </q-item-section>
            <q-item-section>Public IP: {{ summary.public_ip }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-network-wired" />
            </q-item-section>
            <q-item-section>LAN IP: {{ summary.local_ips }}</q-item-section>
          </q-item>
        </q-list>
      </div>
      <div class="col-2">
        <span class="text-subtitle2 text-bold">Checks Status</span>
        <br />
        <div v-if="summary.checks.total !== 0">
          <q-chip v-if="summary.checks.passing" square size="lg">
            <q-avatar size="lg" square icon="done" color="green" text-color="white" />
            <small>{{ summary.checks.passing }} checks passing</small>
          </q-chip>
          <q-chip v-if="summary.checks.failing" square size="lg">
            <q-avatar size="lg" square icon="cancel" color="red" text-color="white" />
            <small>{{ summary.checks.failing }} checks failing</small>
          </q-chip>
          <q-chip v-if="summary.checks.warning" square size="lg">
            <q-avatar size="lg" square icon="warning" color="warning" text-color="white" />
            <small>{{ summary.checks.warning }} checks warning</small>
          </q-chip>
          <q-chip v-if="summary.checks.info" square size="lg">
            <q-avatar size="lg" square icon="info" color="info" text-color="white" />
            <small>{{ summary.checks.info }} checks info</small>
          </q-chip>
          <span
            v-if="
              summary.checks.total !== 0 &&
              summary.checks.passing === 0 &&
              summary.checks.failing === 0 &&
              summary.checks.warning === 0 &&
              summary.checks.info === 0
            "
            >{{ summary.checks.total }} checks awaiting first synchronization</span
          >
        </div>
        <div v-else>No checks</div>
      </div>
      <div class="col-1"></div>
      <!-- right -->
      <div class="col-3">
        <span class="text-subtitle2 text-bold">Disks</span>
        <div v-for="disk in disks" :key="disk.device">
          <span>{{ disk.device }} ({{ disk.fstype }})</span>
          <q-linear-progress
            rounded
            size="15px"
            :value="disk.percent / 100"
            :color="diskBarColor(disk.percent)"
            class="q-mt-sm"
          />
          <span>{{ disk.free }} free of {{ disk.total }}</span>
          <q-separator />
        </div>
      </div>
      <div class="col-2"></div>
    </div>
    <q-inner-loading :showing="loading" color="primary" />
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { fetchAgent, refreshAgentWMI, runTakeControl, openAgentWindow } from "@/api/agents";
import { notifySuccess } from "@/utils/notify";

// ui imports
import AgentActionMenu from "@/components/agents/AgentActionMenu";

export default {
  name: "SummaryTab",
  components: {
    AgentActionMenu,
  },
  setup(props) {
    // vuex setup
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const refreshSummaryTab = computed(() => store.state.refreshSummaryTab);

    // summary tab logic
    const summary = ref(null);
    const loading = ref(false);

    function diskBarColor(percent) {
      if (percent < 80) {
        return "positive";
      } else if (percent > 80 && percent < 95) {
        return "warning";
      } else {
        return "negative";
      }
    }

    const disks = computed(() => {
      if (!summary.value.disks) {
        return [];
      }

      const entries = Object.entries(summary.value.disks);
      const ret = [];
      for (let [k, v] of entries) {
        ret.push(v);
      }
      return ret;
    });

    async function getSummary() {
      loading.value = true;
      summary.value = await fetchAgent(selectedAgent.value);
      store.commit("setRefreshSummaryTab", false);
      loading.value = false;
    }

    async function refreshSummary() {
      loading.value = true;
      try {
        const result = await refreshAgentWMI(selectedAgent.value);
        await getSummary();
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    watch(selectedAgent, (newValue, oldValue) => {
      if (newValue) {
        getSummary();
      }
    });

    watch(refreshSummaryTab, (newValue, oldValue) => {
      if (newValue && selectedAgent.value) {
        getSummary();
      }

      store.commit("setRefreshSummaryTab", false);
    });

    onMounted(() => {
      if (selectedAgent.value) getSummary();
    });

    return {
      // reactive data
      summary,
      loading,
      selectedAgent,
      disks,

      // methods
      getSummary,
      refreshSummary,
      diskBarColor,
      runTakeControl,
      openAgentWindow,
    };
  },
};
</script>

