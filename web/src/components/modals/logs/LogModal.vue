<template>
  <div class="q-pa-md q-gutter-sm">
    <q-dialog
      :value="toggleLogModal"
      @hide="hideLogModal"
      @show="getLog"
      maximized
      transition-show="slide-up"
      transition-hide="slide-down"
    >
      <q-card class="bg-grey-10 text-white">
        <q-bar>
          <q-btn @click="getLog" class="q-mr-sm" dense flat push icon="refresh" label="Refresh" />Debug Log
          <q-space />
          <q-btn color="primary" text-color="white" label="Download log" @click="downloadLog" />
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-md row">
          <div class="col-2">
            <q-select
              dark
              dense
              outlined
              v-model="agent"
              :options="agents"
              label="Filter Agent"
              @input="getLog"
            />
          </div>
          <div class="col-1">
            <q-select
              dark
              dense
              outlined
              v-model="order"
              :options="orders"
              label="Order"
              @input="getLog"
            />
          </div>
        </div>
        <q-card-section>
          <q-radio dark v-model="loglevel" color="cyan" val="info" label="Info" @input="getLog" />
          <q-radio
            dark
            v-model="loglevel"
            color="red"
            val="critical"
            label="Critical"
            @input="getLog"
          />
          <q-radio dark v-model="loglevel" color="red" val="error" label="Error" @input="getLog" />
          <q-radio
            dark
            v-model="loglevel"
            color="yellow"
            val="warning"
            label="Warning"
            @input="getLog"
          />
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-scroll-area
            :thumb-style="{ right: '4px', borderRadius: '5px', background: 'red', width: '10px', opacity: 1 }"
            style="height: 60vh;"
          >
            <pre>{{ logContent }}</pre>
          </q-scroll-area>
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
export default {
  name: "LogModal",
  data() {
    return {
      logContent: "",
      loglevel: "info",
      agent: "all",
      agents: [],
      order: "latest",
      orders: ["latest", "oldest"]
    };
  },
  methods: {
    downloadLog() {
      axios
        .get("/api/v1/downloadrmmlog/", { responseType: "blob" })
        .then(({ data }) => {
          const blob = new Blob([data], { type: "text/plain" });
          let link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = "debug.log";
          link.click();
        })
        .catch(error => console.error(error));
    },
    getLog() {
      axios.get(`/api/v1/getrmmlog/${this.loglevel}/${this.agent}/${this.order}/`).then(r => {
        this.logContent = r.data.log;
        this.agents = r.data.agents.map(k => k.hostname);
        this.agents.unshift("all");
      });
    },
    hideLogModal() {
      this.$store.commit("logs/TOGGLE_LOG_MODAL", false);
    }
  },
  computed: {
    ...mapState({
      toggleLogModal: state => state.logs.toggleLogModal
    })
  }
};
</script>