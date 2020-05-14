<template>
  <div v-if="Object.keys(summary).length === 0">No agent selected</div>
  <div v-else>
    <span>
      <b>{{ summary.hostname }}</b>
      &bull; {{ summary.operating_system }} &bull; Agent v{{ summary.version }}
    </span>
    <hr />
    <div class="row">
      <div class="col-4">
        <!-- left -->
        <q-list dense>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-desktop" />
            </q-item-section>
            <q-item-section>{{ summary.make_model }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-microchip" />
            </q-item-section>
            <q-item-section>{{ summary.cpu_model }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-memory" />
            </q-item-section>
            <q-item-section>{{ summary.total_ram}} GB RAM</q-item-section>
          </q-item>

          <!-- physical disks -->
          <q-item v-for="disk in summary.physical_disks" :key="disk.model">
            <q-item-section avatar>
              <q-icon name="far fa-hdd" />
            </q-item-section>
            <q-item-section>{{ disk.model }} {{ disk.size }}GB {{ disk.interfaceType }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-globe-americas" />
            </q-item-section>
            <q-item-section>Public IP: {{ summary.public_ip}}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-network-wired" />
            </q-item-section>
            <q-item-section>LAN IP: {{ summary.local_ips }}</q-item-section>
          </q-item>
        </q-list>
      </div>
      <div class="col-5"></div>
      <!-- right -->
      <div class="col-3">
        <span class="text-subtitle2 text-bold">Disks</span>
        <div v-for="disk in disks" :key="disk.device">
          <span>{{ disk.device }} ({{ disk.fstype }})</span>
          <q-linear-progress
            rounded
            size="15px"
            :value="disk.percent / 100"
            color="green"
            class="q-mt-sm"
          />
          <span>{{ disk.free }} free of {{ disk.total }}</span>
          <hr />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "SummaryTab",
  data() {
    return {};
  },
  methods: {},
  computed: {
    summary() {
      return this.$store.state.agentSummary;
    },
    disks() {
      const entries = Object.entries(this.summary.disks);
      const ret = [];
      for (let [k, v] of entries) {
        ret.push(v);
      }
      return ret;
    }
  }
};
</script>

