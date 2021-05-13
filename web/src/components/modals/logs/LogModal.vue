<template>
  <q-card class="bg-grey-10 text-white">
    <q-bar>
      <q-btn @click="getLog" class="q-mr-sm" dense flat push icon="refresh" label="Refresh" />Debug Log
      <q-space />
      <q-btn color="primary" text-color="white" label="Download log" @click="downloadLog" />
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <div class="q-pa-md row">
      <div class="col-2">
        <q-select
          dark
          dense
          options-dense
          outlined
          v-model="agent"
          :options="agents"
          label="Filter Agent"
          @input="getLog"
        />
      </div>
      <div class="col-1">
        <q-select dark dense options-dense outlined v-model="order" :options="orders" label="Order" @input="getLog" />
      </div>
    </div>
    <q-card-section>
      <q-radio dark v-model="loglevel" color="cyan" val="info" label="Info" @input="getLog" />
      <q-radio dark v-model="loglevel" color="red" val="critical" label="Critical" @input="getLog" />
      <q-radio dark v-model="loglevel" color="red" val="error" label="Error" @input="getLog" />
      <q-radio dark v-model="loglevel" color="yellow" val="warning" label="Warning" @input="getLog" />
    </q-card-section>
    <q-separator />
    <q-card-section class="scroll" style="max-height: 80vh">
      <pre>{{ logContent }}</pre>
    </q-card-section>
  </q-card>
</template>

<script>
export default {
  name: "LogModal",
  data() {
    return {
      logContent: "",
      loglevel: "info",
      agent: "all",
      agents: [],
      order: "latest",
      orders: ["latest", "oldest"],
    };
  },
  methods: {
    downloadLog() {
      this.$axios
        .get("/logs/downloadlog/", { responseType: "blob" })
        .then(({ data }) => {
          const blob = new Blob([data], { type: "text/plain" });
          let link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = "debug.log";
          link.click();
        })
        .catch(e => {});
    },
    getLog() {
      this.$axios
        .get(`/logs/debuglog/${this.loglevel}/${this.agent}/${this.order}/`)
        .then(r => {
          this.logContent = r.data.log;
          this.agents = r.data.agents.map(k => k.hostname).sort();
          this.agents.unshift("all");
        })
        .catch(e => {});
    },
  },
  created() {
    this.getLog();
  },
};
</script>