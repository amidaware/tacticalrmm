<template>
  <q-card :style="{ 'min-width': width }">
    <q-card-section class="row items-center">
      <div class="text-h6">Run a script on {{ hostname }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-form @submit.prevent="send">
      <q-card-section>
        <q-select
          :rules="[val => !!val || '*Required']"
          dense
          outlined
          v-model="scriptPK"
          :options="scriptOptions"
          label="Select script"
          map-options
          emit-value
          options-dense
        />
      </q-card-section>
      <q-card-section>
        <q-select
          label="Script Arguments (press Enter after typing each argument)"
          filled
          v-model="args"
          use-input
          use-chips
          multiple
          hide-dropdown-icon
          input-debounce="0"
          new-value-mode="add"
        />
      </q-card-section>
      <q-card-section>
        <div class="q-gutter-sm">
          <q-radio dense v-model="output" val="wait" label="Wait for Output" />
          <q-radio dense v-model="output" val="forget" label="Fire and Forget" />
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
            val => val <= 25200 || 'Maximum is 25,200 seconds',
          ]"
        />
      </q-card-section>
      <q-card-actions align="center">
        <q-btn :loading="loading" label="Run" color="primary" class="full-width" type="submit" />
      </q-card-actions>
      <q-card-section v-if="ret !== null" class="q-pl-md q-pr-md q-pt-none q-ma-none scroll" style="max-height: 50vh">
        <pre>{{ ret }}</pre>
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";

export default {
  name: "RunScript",
  mixins: [mixins],
  props: {
    pk: Number,
  },
  data() {
    return {
      loading: false,
      scriptPK: null,
      timeout: 30,
      ret: null,
      output: "wait",
      args: [],
    };
  },
  computed: {
    ...mapGetters(["scripts"]),
    hostname() {
      return this.$store.state.agentSummary.hostname;
    },
    width() {
      return this.ret === null ? "40vw" : "70vw";
    },
    scriptOptions() {
      const ret = [];
      this.scripts.forEach(i => {
        ret.push({ label: i.name, value: i.id });
      });
      return ret;
    },
  },
  methods: {
    send() {
      this.ret = null;
      this.loading = true;
      const data = {
        pk: this.pk,
        timeout: this.timeout,
        scriptPK: this.scriptPK,
        output: this.output,
        args: this.args,
      };
      this.$axios
        .post("/agents/runscript/", data)
        .then(r => {
          if (this.output === "wait") {
            this.loading = false;
            this.ret = r.data;
          } else {
            this.loading = false;
            this.notifySuccess(r.data);
            this.$emit("close");
          }
        })
        .catch(e => {
          this.loading = false;
          this.notifyError(e.response.data);
        });
    },
  },
};
</script>