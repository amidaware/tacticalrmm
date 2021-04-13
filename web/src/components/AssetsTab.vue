<template>
  <div v-if="!selectedAgentPk">No agent selected</div>
  <div v-else class="q-pa-none">
    <div class="q-gutter-y-md">
      <q-card>
        <q-tabs
          v-model="tab"
          dense
          class="text-grey"
          active-color="primary"
          indicator-color="primary"
          align="justify"
          narrow-indicator
          no-caps
        >
          <q-tab name="os" label="Operating System" />
          <q-tab name="cpu" label="CPU" />
          <q-tab name="mem" label="Memory" />
          <q-tab name="usb" label="USB" />
          <q-tab name="bios" label="Bios" />
          <q-tab name="disk" label="Disks" />
          <q-tab name="comp_sys" label="Computer System" />
          <q-tab name="base_board" label="Motherboard" />
          <q-tab name="comp_sys_prod" label="Computer System Product" />
          <q-tab name="network_config" label="Network Config" />
          <q-tab name="graphics" label="Graphics" />
          <q-tab name="desktop_monitor" label="Monitors" />
          <q-tab name="network_adapter" label="Network Adapters" />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="tab">
          <q-tab-panel name="os">
            <WmiDetail :info="os" />
          </q-tab-panel>
          <q-tab-panel name="cpu">
            <WmiDetail :info="cpu" />
          </q-tab-panel>
          <q-tab-panel name="mem">
            <WmiDetail :info="mem" />
          </q-tab-panel>
          <q-tab-panel name="usb">
            <WmiDetail :info="usb" />
          </q-tab-panel>
          <q-tab-panel name="bios">
            <WmiDetail :info="bios" />
          </q-tab-panel>
          <q-tab-panel name="disk">
            <WmiDetail :info="disk" />
          </q-tab-panel>
          <q-tab-panel name="comp_sys">
            <WmiDetail :info="comp_sys" />
          </q-tab-panel>
          <q-tab-panel name="base_board">
            <WmiDetail :info="base_board" />
          </q-tab-panel>
          <q-tab-panel name="comp_sys_prod">
            <WmiDetail :info="comp_sys_prod" />
          </q-tab-panel>
          <q-tab-panel name="network_config">
            <WmiDetail :info="network_config" />
          </q-tab-panel>
          <q-tab-panel name="desktop_monitor">
            <WmiDetail :info="desktop_monitor" />
          </q-tab-panel>
          <q-tab-panel name="graphics">
            <WmiDetail :info="graphics" />
          </q-tab-panel>
          <q-tab-panel name="network_adapter">
            <WmiDetail :info="network_adapter" />
          </q-tab-panel>
        </q-tab-panels>
      </q-card>
    </div>
  </div>
</template>

<script>
import { mapGetters } from "vuex";
import WmiDetail from "@/components/WmiDetail";

export default {
  name: "AssetsTab",
  components: { WmiDetail },
  data() {
    return {
      tab: "os",
    };
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    assets() {
      return Object.freeze(this.$store.state.agentSummary.wmi_detail);
    },
    os() {
      return this.assets.os;
    },
    cpu() {
      return this.assets.cpu;
    },
    mem() {
      return this.assets.mem;
    },
    usb() {
      return this.assets.usb;
    },
    bios() {
      return this.assets.bios;
    },
    disk() {
      return this.assets.disk;
    },
    comp_sys() {
      return this.assets.comp_sys;
    },
    base_board() {
      return this.assets.base_board;
    },
    comp_sys_prod() {
      return this.assets.comp_sys_prod;
    },
    network_config() {
      return this.assets.network_config;
    },
    desktop_monitor() {
      return this.assets.desktop_monitor;
    },
    network_adapter() {
      return this.assets.network_adapter;
    },
    graphics() {
      return this.assets.graphics;
    },
  },
};
</script>

