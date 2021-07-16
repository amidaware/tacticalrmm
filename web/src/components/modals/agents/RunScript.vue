<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" :maximized="maximized">
    <q-card class="dialog-plugin" style="min-width: 50vw">
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
            outlined
            v-model="scriptPK"
            :options="scriptOptions"
            label="Select script"
            mapOptions
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
            <q-radio dense v-model="output" val="email" label="Email results" />
            <q-radio dense v-model="output" val="collector" label="Save results to Custom Field" />
            <q-radio dense v-model="output" val="note" label="Save results to Agent Notes" />
          </div>
        </q-card-section>
        <q-card-section v-if="output === 'email'">
          <div class="q-gutter-sm">
            <q-radio
              dense
              v-model="emailmode"
              val="default"
              label="Use email addresses from global settings"
              @update:model-value="emails = []"
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
        <q-card-section v-if="output === 'collector'">
          <tactical-dropdown
            :rules="[val => !!val || '*Required']"
            dense
            outlined
            v-model="custom_field"
            :options="customFieldOptions"
            label="Select custom field"
            mapOptions
            options-dense
          />
          <q-checkbox v-model="save_all_output" label="Save all output" />
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
  </q-dialog>
</template>

<script>
// composition imports
import { ref, watch, computed, onMounted } from "vue";
import { useStore } from "vuex";
import { useDialogPluginComponent, useQuasar } from "quasar";
import { useScriptDropdown } from "@/composables/scripts";
import { useCustomFieldDropdown } from "@/composables/core";
import { runScript } from "@/api/agents";

//ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown";

export default {
  name: "RunScript",
  emits: [...useDialogPluginComponent.emits],
  components: { TacticalDropdown },
  props: {
    agent: !Object,
  },
  setup(props) {
    const $q = useQuasar();
    // setup vuex store
    const { state } = useStore();
    const showCommunityScripts = computed(() => state.showCommunityScripts);

    // setup quasar dialog plugin
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    // setup dropdowns
    const { scriptPK, scriptOptions, defaultTimeout, defaultArgs, getScriptOptions } = useScriptDropdown();
    const { customFieldOptions, getCustomFieldOptions } = useCustomFieldDropdown();

    // main run script functionaity
    const loading = ref(false);
    const output = ref("wait");
    const ret = ref(null);
    const emails = ref([]);
    const emailmode = ref("default");
    const custom_field = ref(null);
    const save_all_output = ref(false);
    const maximized = ref(false);

    async function sendScript() {
      ret.value = null;
      loading.value = true;

      const data = {
        pk: props.agent.id,
        timeout: defaultTimeout.value,
        scriptPK: scriptPK.value,
        output: output.value,
        args: defaultArgs.value,
        emails: emails.value,
        emailmode: emailmode.value,
        custom_field: custom_field.value,
        save_all_output: save_all_output.value,
      };

      ret.value = await runScript(data);
      loading.value = false;
      if (output.value === "forget") {
        onDialogHide();
        $q.notify({
          message: ret.value,
          color: "positive",
        });
      }
    }

    // watchers
    watch(output, () => (emails.value = []));

    // vue component hooks
    onMounted(() => {
      getScriptOptions(showCommunityScripts.value);
      getCustomFieldOptions();
    });

    return {
      // reactive data
      loading,
      scriptPK,
      scriptOptions,
      timeout: defaultTimeout,
      output,
      ret,
      args: defaultArgs,
      emails,
      emailmode,
      maximized,
      customFieldOptions,
      custom_field,
      save_all_output,

      //methods
      sendScript,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>