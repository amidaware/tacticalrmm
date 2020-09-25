<template>
  <q-card :style="{'min-width': width}">
    <q-card-section class="row items-center">
      <div class="text-h6">Send command on {{ hostname }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-form @submit.prevent="send">
      <q-card-section>
        <div class="q-gutter-sm">
          <q-radio dense v-model="shell" val="cmd" label="CMD" />
          <q-radio dense v-model="shell" val="powershell" label="Powershell" />
        </div>
      </q-card-section>
      <q-card-section>
        <q-input
          v-model.number="timeout"
          dense
          outlined
          type="number"
          style="max-width: 150px"
          label="Timeout (seconds)"
          stack-label
          :rules="[ 
              val => !!val || '*Required',
              val => val >= 10 || 'Minimum is 10 seconds',
              val => val <= 3600 || 'Maximum is 3600 seconds'
          ]"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          v-model="cmd"
          outlined
          label="Command"
          stack-label
          :placeholder="shell === 'cmd' ? 'rmdir /S /Q C:\\Windows\\System32' : 'Remove-Item -Recurse -Force C:\\Windows\\System32'"
          :rules="[ val => !!val || '*Required']"
        />
      </q-card-section>
      <q-card-actions align="center">
        <q-btn :loading="loading" label="Send" color="primary" class="full-width" type="submit" />
      </q-card-actions>
      <q-card-section
        v-if="ret !== null"
        class="q-pl-md q-pr-md q-pt-none q-ma-none scroll"
        style="max-height: 50vh"
      >
        <pre>{{ ret }}</pre>
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "SendCommand",
  mixins: [mixins],
  props: {
    pk: Number,
  },
  data() {
    return {
      loading: false,
      shell: "cmd",
      cmd: null,
      timeout: 30,
      ret: null,
    };
  },
  computed: {
    hostname() {
      return this.$store.state.agentSummary.hostname;
    },
    width() {
      return this.ret === null ? "40vw" : "70vw";
    },
  },
  methods: {
    send() {
      this.ret = null;
      this.loading = true;
      const data = {
        pk: this.pk,
        cmd: this.cmd,
        shell: this.shell,
        timeout: this.timeout,
      };
      this.$axios
        .post("/agents/sendrawcmd/", data)
        .then(r => {
          this.loading = false;
          this.ret = r.data;
        })
        .catch(e => {
          this.loading = false;
          this.notifyError(e.response.data);
        });
    },
  },
};
</script>