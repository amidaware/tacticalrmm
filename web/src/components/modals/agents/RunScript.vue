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
          @input="setScriptDefaults"
        >
          <template v-slot:option="scope">
            <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
              <q-item-section>
                <q-item-label v-html="scope.opt.label"></q-item-label>
              </q-item-section>
            </q-item>
            <q-item-label v-if="scope.opt.category" v-bind="scope.itemProps" header class="q-pa-sm">{{
              scope.opt.category
            }}</q-item-label>
          </template>
        </q-select>
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
          <q-radio dense v-model="output" val="wait" label="Wait for Output" @input="emails = []" />
          <q-radio dense v-model="output" val="forget" label="Fire and Forget" @input="emails = []" />
          <q-radio dense v-model="output" val="email" label="Email results" />
        </div>
      </q-card-section>
      <q-card-section v-if="output === 'email'">
        <div class="q-gutter-sm">
          <q-radio
            dense
            v-model="emailmode"
            val="default"
            label="Use email addresses from global settings"
            @input="emails = []"
          />
          <q-radio dense v-model="emailmode" val="custom" label="Custom emails" />
        </div>
      </q-card-section>
      <q-card-section v-if="emailmode === 'custom' && output === 'email'">
        <q-select
          label="Email recipients (press Enter after typing each email)"
          filled
          v-model="emails"
          use-input
          use-chips
          multiple
          hide-dropdown-icon
          input-debounce="0"
          new-value-mode="add"
        />
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
          :rules="[val => !!val || '*Required', val => val >= 5 || 'Minimum is 5 seconds']"
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
import { mapState } from "vuex";

export default {
  name: "RunScript",
  emits: ["close"],
  mixins: [mixins],
  props: {
    pk: Number,
  },
  data() {
    return {
      scriptOptions: [],
      loading: false,
      scriptPK: null,
      timeout: 30,
      ret: null,
      output: "wait",
      args: [],
      emails: [],
      emailmode: "default",
    };
  },
  computed: {
    ...mapState(["showCommunityScripts"]),
    hostname() {
      return this.$store.state.agentSummary.hostname;
    },
    width() {
      return this.ret === null ? "40vw" : "70vw";
    },
  },
  methods: {
    setScriptDefaults() {
      const script = this.scriptOptions.find(i => i.value === this.scriptPK);

      this.timeout = script.timeout;
      this.args = script.args;
    },
    send() {
      this.ret = null;
      this.loading = true;
      const data = {
        pk: this.pk,
        timeout: this.timeout,
        scriptPK: this.scriptPK,
        output: this.output,
        args: this.args,
        emails: this.emails,
        emailmode: this.emailmode,
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
        });
    },
  },
  mounted() {
    this.getScriptOptions(this.showCommunityScripts).then(options => (this.scriptOptions = Object.freeze(options)));
  },
};
</script>