<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistent @keydown.esc="onDialogHide" :maximized="maximized">
    <q-card class="dialog-plugin" style="min-width: 60vw">
      <q-bar>
        Run a script on {{ agent.hostname }}
        <q-space />
        <q-btn dense flat icon="minimize" @click="maximized = false" :disable="!maximized">
          <q-tooltip v-if="maximized" class="bg-white text-primary">Minimize</q-tooltip>
        </q-btn>
        <q-btn dense flat icon="crop_square" @click="maximized = true" :disable="maximized">
          <q-tooltip v-if="!maximized" class="bg-white text-primary">Maximize</q-tooltip>
        </q-btn>
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit.prevent="sendScript">
        <q-card-section>
          <tactical-dropdown
            :rules="[val => !!val || '*Required']"
            v-model="state.script"
            :options="filteredScriptOptions"
            label="Select script"
            outlined
            mapOptions
            filterable
          >
            <template v-slot:after>
              <q-btn size="sm" round dense flat icon="info" @click="openScriptURL">
                <q-tooltip v-if="syntax" class="bg-white text-primary text-body1" v-html="formatScriptSyntax(syntax)" />
              </q-btn>
            </template>
          </tactical-dropdown>
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            v-model="state.args"
            label="Script Arguments (press Enter after typing each argument)"
            filled
            use-input
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>
        <q-card-section>
          <q-option-group v-model="state.output" :options="outputOptions" color="primary" inline dense />
        </q-card-section>
        <q-card-section v-if="state.output === 'email'">
          <div class="q-gutter-sm">
            <q-radio dense v-model="state.emailMode" val="default" label="Use email addresses from global settings" />
            <q-radio dense v-model="state.emailMode" val="custom" label="Custom emails" />
          </div>
        </q-card-section>
        <q-card-section v-if="state.emailMode === 'custom' && state.output === 'email'">
          <tactical-dropdown
            v-model="state.emails"
            label="Email recipients (press Enter after typing each email)"
            filled
            use-input
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>
        <q-card-section v-if="state.output === 'collector'">
          <tactical-dropdown
            :rules="[val => !!val || '*Required']"
            outlined
            v-model="state.custom_field"
            :options="customFieldOptions"
            label="Select custom field"
            mapOptions
          />
          <q-checkbox v-model="state.save_all_output" label="Save all output" />
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.number="state.timeout"
            dense
            outlined
            type="number"
            style="max-width: 150px"
            label="Timeout (seconds)"
            stack-label
            :rules="[val => !!val || '*Required', val => val >= 5 || 'Minimum is 5 seconds']"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Cancel" v-close-popup />
          <q-btn :loading="loading" :disabled="loading" label="Run" color="primary" type="submit" />
        </q-card-actions>
        <q-card-section v-if="ret !== null" class="q-pl-md q-pr-md q-pt-none q-ma-none scroll" style="max-height: 50vh">
          <pre>{{ ret }}</pre>
        </q-card-section>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, watch, computed } from "vue";
import { useDialogPluginComponent, openURL } from "quasar";
import { useScriptDropdown } from "@/composables/scripts";
import { useCustomFieldDropdown } from "@/composables/core";
import { runScript } from "@/api/agents";
import { notifySuccess } from "@/utils/notify";
import { formatScriptSyntax, removeExtraOptionCategories } from "@/utils/format";

//ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown";

// static data
const outputOptions = [
  { label: "Wait for Output", value: "wait" },
  { label: "Fire and Forget", value: "forget" },
  { label: "Email results", value: "email" },
  { label: "Save results to Custom Field", value: "collector" },
  { label: "Save results to Agent Notes", value: "note" },
];

export default {
  name: "RunScript",
  emits: [...useDialogPluginComponent.emits],
  components: { TacticalDropdown },
  props: {
    agent: !Object,
    script: Number,
  },
  setup(props) {
    // setup quasar dialog plugin
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    // setup dropdowns
    const { script, scriptOptions, defaultTimeout, defaultArgs, syntax, link } = useScriptDropdown(props.script, {
      onMount: true,
      filterByPlatform: props.agent.plat,
    });
    const { customFieldOptions } = useCustomFieldDropdown({ onMount: true });

    // main run script functionaity
    const state = ref({
      output: "wait",
      emails: [],
      emailMode: "default",
      custom_field: null,
      save_all_output: false,
      script,
      args: defaultArgs,
      timeout: defaultTimeout,
    });

    const ret = ref(null);
    const loading = ref(false);
    const maximized = ref(false);

    async function sendScript() {
      ret.value = null;
      loading.value = true;

      ret.value = await runScript(props.agent.agent_id, state.value);
      loading.value = false;
      if (state.value.output === "forget") {
        onDialogHide();
        notifySuccess(ret.value);
      }
    }

    function openScriptURL() {
      link.value ? openURL(link.value) : null;
    }

    const filteredScriptOptions = computed(() => {
      return removeExtraOptionCategories(
        scriptOptions.value.filter(
          script =>
            script.category || !script.supported_platforms || script.supported_platforms.includes(props.agent.plat)
        )
      );
    });

    // watchers
    watch([() => state.value.output, () => state.value.emailMode], () => (state.value.emails = []));

    return {
      // reactive data
      state,
      loading,
      filteredScriptOptions,
      link,
      syntax,
      ret,
      maximized,
      customFieldOptions,

      // non-reactive data
      outputOptions,

      //methods
      formatScriptSyntax,
      sendScript,
      openScriptURL,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>