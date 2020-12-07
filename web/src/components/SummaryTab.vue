<template>
  <div v-if="Object.keys(summary).length === 0">No agent selected</div>
  <div v-else>
    <q-btn class="q-mr-sm" dense flat push icon="refresh" @click="refreshSummary" />
    <span>
      <b>{{ summary.hostname }}</b>
      <span v-if="summary.maintenance_mode"> &bull; <q-badge color="warning"> Maintenance Mode </q-badge> </span>
      &bull; {{ summary.operating_system }} &bull; Agent v{{ summary.version }}
    </span>
    <hr />
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
        <template v-if="summary.checks.total !== 0">
          <q-chip v-if="summary.checks.passing" square size="lg">
            <q-avatar size="lg" square icon="done" color="green" text-color="white" />
            <small>{{ summary.checks.passing }} checks passing</small>
          </q-chip>
          <q-chip v-if="summary.checks.failing" square size="lg">
            <q-avatar size="lg" square icon="cancel" color="red" text-color="white" />
            <small>{{ summary.checks.failing }} checks failing</small>
          </q-chip>
          <span v-if="awaitingSync(summary.checks.total, summary.checks.passing, summary.checks.failing)"
            >{{ summary.checks.total }} checks awaiting first synchronization</span
          >
        </template>
        <template v-else>No checks</template>
      </div>
      <div class="col-1"></div>
      <!-- right -->
      <div class="col-3">
        <span class="text-subtitle2 text-bold">Disks</span>
        <div v-for="disk in disks" :key="disk.device">
          <span>{{ disk.device }} ({{ disk.fstype }})</span>
          <q-linear-progress rounded size="15px" :value="disk.percent / 100" color="green" class="q-mt-sm" />
          <span>{{ disk.free }} free of {{ disk.total }}</span>
          <hr />
        </div>
      </div>
      <div class="col-2"></div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "SummaryTab",
  mixins: [mixins],
  data() {
    return {};
  },
  methods: {
    awaitingSync(total, passing, failing) {
      return total !== 0 && passing === 0 && failing === 0 ? true : false;
    },
    refreshSummary() {
      this.$q.loading.show();
      this.$axios
        .get(`/agents/${this.selectedAgentPk}/wmi/`)
        .then(r => {
          this.$store.dispatch("loadSummary", this.selectedAgentPk);
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    summary() {
      return this.$store.state.agentSummary;
    },
    disks() {
      if (this.summary.disks === undefined) {
        return [];
      }

      const entries = Object.entries(this.summary.disks);
      const ret = [];
      for (let [k, v] of entries) {
        ret.push(v);
      }
      return ret;
    },
  },
};
</script>

