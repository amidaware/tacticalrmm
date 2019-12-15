<template>
  <div class="q-pa-md">
    <q-tabs
      v-model="tab"
      dense
      inline-label
      class="text-grey"
      active-color="primary"
      indicator-color="primary"
      align="left"
      narrow-indicator
    >
      <q-tab name="terminal" icon="fas fa-terminal" label="Terminal" />
      <q-tab name="filebrowser" icon="far fa-folder-open" label="File Browser" />
      <q-tab name="services" icon="fas fa-cogs" label="Services" />
      <q-tab name="eventlog" icon="fas fa-cogs" label="Event Log" />
    </q-tabs>
    <q-separator />
    <q-tab-panels v-model="tab">
      <q-tab-panel name="terminal">
        <iframe
          style="overflow:hidden;height:715px;"
          :src="terminalurl" width="100%" height="100%" scrolling="no"
        >
        </iframe>
      </q-tab-panel>
      <q-tab-panel name="services">
        <Services :pk="pk" />
      </q-tab-panel>
      <q-tab-panel name="eventlog">
        <EventLog :pk="pk" />
      </q-tab-panel>
      <q-tab-panel name="filebrowser">
        <iframe
          style="overflow:hidden;height:715px;"
          :src="fileurl" width="100%" height="100%" scrolling="no"
        >
        </iframe>
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script>
import axios from "axios";
import Services from "@/components/Services";
import EventLog from "@/components/EventLog";

export default {
  name: "RemoteBackground",
  components: {
    Services,
    EventLog
  },
  data() {
    return {
      terminalurl: "",
      fileurl: "",
      tab: "terminal",
      title: ''
    };
  },
  methods: {
    genURLS() {
      axios.get(`/agents/${this.pk}/meshtabs/`).then(r => {
        this.terminalurl = r.data.terminalurl;
        this.fileurl = r.data.fileurl;
        this.title = `${r.data.hostname} | Remote Background`;
      });
    }
  },
  meta() {
    return {
      title: this.title
    }
  },
  computed: {
    pk() {
      return this.$route.params.pk;
    }
  },
  created() {
    this.genURLS();
  }
};
</script>