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
      <p
        class="text-subtitle1"
      >Download the agent then run the following command from an elevated command prompt on the device you want to add.</p>
      <p>
        <q-field outlined color="black">
          <code>
            {{ info.exe }} /VERYSILENT /SUPPRESSMSGBOXES
            && timeout /t 20 /nobreak > NUL
            && "C:\Program Files\TacticalAgent\tacticalrmm.exe" -m install --api "{{ info.api }}"
            --client-id {{ info.data.client }} --site-id {{ info.data.site }}
            --agent-type "{{ info.agenttype }}" --power {{ info.power }} --rdp {{ info.rdp }} --ping {{ info.ping }} --auth "{{ info.data.token }}"
          </code>
        </q-field>
      </p>
      <div v-show="info.data.showextra">
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
              <a
                href="https://github.com/wh1te909/winagent/raw/master/bin/salt-minion-setup.exe"
              >here</a>
            </span>
          </div>
          <div class="q-pa-xs q-gutter-xs">
            <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
              <code>--local-mesh "C:\\&lt;some folder or path&gt;\\meshagent.exe"</code>
            </q-badge>
            <span>
              To skip downloading the Mesh Agent during the install. Download it
              <span
                style="cursor:pointer;color:blue;text-decoration:underline"
                @click="downloadMesh"
              >here</span>
            </span>
          </div>
        </q-expansion-item>
      </div>
      <br />
      <p class="text-italic">Note: the auth token above will be valid for {{ info.expires }} hours.</p>
      <q-btn type="a" :href="info.download" color="primary" label="Download Agent" />
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
      this.$axios
        .post("/api/v1/getmeshexe/", {}, { responseType: "blob" })
        .then(({ data }) => {
          const blob = new Blob([data], { type: "application/vnd.microsoft.portable-executable" });
          let link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = "meshagent.exe";
          link.click();
        })
        .catch(e => this.notifyError("Something went wrong"));
    },
  },
};
</script>