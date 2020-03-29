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
            <q-item-section>{{ makeModel }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-microchip" />
            </q-item-section>
            <q-item-section>{{ cpuModel }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-memory" />
            </q-item-section>
            <q-item-section>{{ summary.total_ram}} GB RAM</q-item-section>
          </q-item>

          <!-- physical disks -->
          <q-item v-for="disk in physicalDisks" :key="disk.model">
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
            <q-item-section>LAN IP: {{ localIPs }}</q-item-section>
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
  methods: {
    bytesToGB(bytes) {
      return Math.round(parseInt(bytes) / 1073741824);
    },
    validateIPv4(ip) {
      const rx = /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/;
      if (rx.test(ip)) {
        return true;
      }
      return false;
    }
  },
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
    },
    makeModel() {
      const comp_sys = this.summary.wmi_detail.comp_sys[0];
      const comp_sys_prod = this.summary.wmi_detail.comp_sys_prod[0];
      let make = comp_sys_prod.filter(k => k.Vendor).map(k => k.Vendor)[0];
      let model = comp_sys.filter(k => k.SystemFamily).map(k => k.SystemFamily)[0];

      if (!model || !make) {
        return comp_sys_prod.filter(k => k.Version).map(k => k.Version)[0];
      } else {
        return `${make} ${model}`;
      }
    },
    physicalDisks() {
      const ret = this.summary.wmi_detail.disk;
      const phys = [];
      ret.forEach(disk => {
        const model = disk.filter(k => k.Caption).map(k => k.Caption)[0];
        const size = disk.filter(k => k.Size).map(k => k.Size)[0];
        const interfaceType = disk
          .filter(k => k.InterfaceType)
          .map(k => k.InterfaceType)[0];

        phys.push({
          model: model,
          size: this.bytesToGB(size),
          interfaceType: interfaceType
        });
      });

      return phys;
    },
    localIPs() {
      const ret = this.summary.wmi_detail.network_config;
      const ips = [];
      ret.forEach(ip => {
        const x = ip.filter(k => k.IPAddress).map(k => k.IPAddress)[0];
        if (x !== undefined) {
          x.forEach(i => {
            if (this.validateIPv4(i)) {
              ips.push(i);
            }
          });
        }
      });
      return (ips.length === 1 ? ips[0] : ips.join(", "))
    },
    cpuModel() {
      const cpu = this.summary.wmi_detail.cpu[0];
      return cpu.filter(k => k.Name).map(k => k.Name)[0];
    }
  }
};
</script>

