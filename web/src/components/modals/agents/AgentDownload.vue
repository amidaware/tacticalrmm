<template>
  <q-card style="min-width: 70vw">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Manual Installation Instructions</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <p class="text-subtitle1">
        Download the agent then run the following command from an elevated command prompt on the device you want to add.
      </p>
      <p>
        <q-field outlined :color="$q.dark.isActive ? 'white' : 'black'">
          <code>{{ info.data.cmd }}</code>
        </q-field>
      </p>
      <q-expansion-item
        switch-toggle-side
        header-class="text-primary"
        expand-separator
        label="View optional command line args"
      >
        <div class="q-pa-xs q-gutter-xs">
          <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
            <code>--log DEBUG</code>
          </q-badge>
          <span>To enable verbose output during the install</span>
        </div>
        <div class="q-pa-xs q-gutter-xs">
          <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
            <code>--local-salt "C:\\&lt;some folder or path&gt;\\salt-minion-setup.exe"</code>
          </q-badge>
          <span>
            To skip downloading the salt-minion during the install. Download it
            <a v-if="info.arch === '64'" :href="info.data.salt64">here</a>
            <a v-else :href="info.data.salt32">here</a>
          </span>
        </div>
        <div class="q-pa-xs q-gutter-xs">
          <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
            <code>--local-mesh "C:\\&lt;some folder or path&gt;\\meshagent.exe"</code>
          </q-badge>
          <span>
            To skip downloading the Mesh Agent during the install. Download it
            <span style="cursor: pointer; text-decoration: underline" class="text-primary" @click="downloadMesh"
              >here</span
            >
          </span>
        </div>
        <div class="q-pa-xs q-gutter-xs">
          <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
            <code>--cert "C:\\&lt;some folder or path&gt;\\ca.pem"</code>
          </q-badge>
          <span> To use a domain CA </span>
        </div>
        <div class="q-pa-xs q-gutter-xs">
          <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
            <code>--timeout NUMBER_IN_SECONDS</code>
          </q-badge>
          <span> To increase the default timeout of 900 seconds for the installer. Use on slow computers.</span>
        </div>
      </q-expansion-item>
      <br />
      <p class="text-italic">Note: the auth token above will be valid for {{ info.expires }} hours.</p>
      <q-btn type="a" :href="info.data.url" color="primary" label="Download Agent" />
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "AgentDownload",
  mixins: [mixins],
  props: ["info"],
  methods: {
    downloadMesh() {
      const fileName = this.info.arch === "64" ? "meshagent.exe" : "meshagent-x86.exe";
      this.$axios
        .post(`/agents/${this.info.arch}/getmeshexe/`, {}, { responseType: "blob" })
        .then(({ data }) => {
          const blob = new Blob([data], { type: "application/vnd.microsoft.portable-executable" });
          let link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = fileName;
          link.click();
        })
        .catch(e => this.notifyError(e.response.data));
    },
  },
};
</script>