<template>
  <q-card style="min-width: 50vw">
    <q-card-section class="row items-center">
      <div class="text-h6">{{ hostname }} Agent Recovery</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-form @submit.prevent="recover">
      <q-card-section></q-card-section>
      <q-card-section>
        <div class="q-gutter-sm">
          <q-radio dense v-model="mode" val="mesh" label="Mesh Agent" />
          <q-radio dense v-model="mode" val="rpc" label="Tactical RPC" />
          <q-radio dense v-model="mode" val="tacagent" label="Tactical Agent" />
          <q-radio dense v-model="mode" val="checkrunner" label="Tactical Checkrunner" />
          <q-radio dense v-model="mode" val="command" label="Shell Command" />
        </div>
      </q-card-section>
      <q-card-section v-show="mode === 'mesh'">
        <p>Fix issues with the Mesh Agent which handles take control, live terminal and file browser.</p>
      </q-card-section>
      <q-card-section v-show="mode === 'tacagent'">
        <p>Fix issues with the TacticalAgent windows service which handles agent check-in and os info.</p>
      </q-card-section>
      <q-card-section v-show="mode === 'checkrunner'">
        <p>Fix issues with the Tactical Checkrunner windows service which handles running all checks.</p>
      </q-card-section>
      <q-card-section v-show="mode === 'rpc'">
        <p>
          Fix issues with the Tactical RPC service which handles most of the agent's realtime functions and scheduled
          tasks.
        </p>
      </q-card-section>
      <q-card-section v-show="mode === 'command'">
        <p>Run a shell command on the agent.</p>
        <p>You should use the 'Send Command' feature from the agent's context menu for sending shell commands.</p>
        <p>Only use this as a last resort if unable to recover the Tactical RPC service.</p>
        <q-input
          ref="input"
          v-model="cmd"
          outlined
          label="Command"
          bottom-slots
          stack-label
          error-message="*Required"
          :error="!isValid"
        />
      </q-card-section>
      <q-card-actions align="center">
        <q-btn label="Recover" color="primary" class="full-width" type="submit" />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "AgentRecovery",
  mixins: [mixins],
  props: {
    pk: Number,
  },
  data() {
    return {
      mode: "mesh",
      cmd: null,
    };
  },
  computed: {
    hostname() {
      return this.$store.state.agentSummary.hostname;
    },
    isValid() {
      if (this.mode === "command") {
        if (this.cmd === null || this.cmd === "") {
          return false;
        }
      }
      return true;
    },
  },
  methods: {
    recover() {
      this.$q.loading.show();
      const data = {
        pk: this.pk,
        cmd: this.cmd,
        mode: this.mode,
      };
      this.$axios
        .post("/agents/recover/", data)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.notifySuccess(r.data, 5000);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data, 5000);
        });
    },
  },
};
</script>