<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistent @keydown.esc="onDialogHide" :maximized="maximized">
    <q-card class="q-dialog-plugin" :style="maximized ? '' : 'width: 80vw; max-width: 90vw'">
      <q-bar>
        {{ title }}
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
      <q-form @submit="submitForm">
        <div class="q-pt-sm q-px-sm row">
          <q-input
            filled
            dense
            class="col-2"
            :readonly="readonly"
            v-model="formScript.name"
            label="Name"
            :rules="[val => !!val || '*Required']"
          />
          <q-select
            class="q-pl-sm col-2"
            :readonly="readonly"
            options-dense
            filled
            dense
            v-model="formScript.shell"
            :options="shellOptions"
            emit-value
            map-options
            label="Shell Type"
          />
          <q-input
            type="number"
            class="q-pl-sm col-2"
            filled
            dense
            :readonly="readonly"
            v-model.number="formScript.default_timeout"
            label="Timeout (seconds)"
            :rules="[val => val >= 5 || 'Minimum is 5']"
          />
          <tactical-dropdown
            class="q-pl-sm col-3"
            filled
            v-model="formScript.category"
            :options="categories"
            use-input
            clearable
            new-value-mode="add-unique"
            filterable
            label="Category"
            :readonly="readonly"
            hide-bottom-space
          />
          <q-input
            class="q-pl-sm col-3"
            filled
            dense
            :readonly="readonly"
            v-model="formScript.description"
            label="Description"
          />
          <tactical-dropdown
            v-model="formScript.args"
            label="Script Arguments (press Enter after typing each argument)"
            class="q-pb-sm col-12 row"
            filled
            use-input
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
            :readonly="readonly"
          />
        </div>
        <v-ace-editor
          v-model:value="code"
          :lang="formScript.shell === 'cmd' ? 'batchfile' : formScript.shell"
          :theme="$q.dark.isActive ? 'tomorrow_night_eighties' : 'tomorrow'"
          :style="{ height: `${maximized ? '72vh' : '64vh'}` }"
          wrap
        />
        <q-card-actions>
          <tactical-dropdown
            style="width: 350px"
            dense
            filled
            v-model="agent"
            :options="agentOptions"
            label="Agent to run test script on"
            mapOptions
            @filter="loadAgentOptions"
          >
            <template v-slot:after>
              <q-btn
                size="md"
                color="primary"
                dense
                flat
                label="Test Script"
                :disable="!agent || !code || !formScript.default_timeout"
                @click="openTestScriptModal"
              />
            </template>
          </tactical-dropdown>
          <q-space />
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn v-if="!readonly" :loading="loading" dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composable imports
import { ref, computed } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { saveScript, editScript, downloadScript } from "@/api/scripts";
import { useAgentDropdown } from "@/composables/agents";
import { notifySuccess } from "@/utils/notify";

// ui imports
import TestScriptModal from "@/components/scripts/TestScriptModal";
import TacticalDropdown from "@/components/ui/TacticalDropdown";
import { VAceEditor } from "vue3-ace-editor";

// static data
import { shellOptions } from "@/composables/scripts";

export default {
  name: "ScriptFormModal",
  emits: [...useDialogPluginComponent.emits],
  components: {
    TacticalDropdown,
    VAceEditor,
  },
  props: {
    script: Object,
    categories: !Array,
    readonly: {
      type: Boolean,
      default: false,
    },
    clone: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    // setup quasar plugins
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();
    const $q = useQuasar();

    // setup agent dropdown
    const { agent, agentOptions, getAgentOptions } = useAgentDropdown();

    // script form logic
    const script = props.script
      ? ref(Object.assign({}, props.script))
      : ref({ shell: "powershell", default_timeout: 90, args: [] });

    if (props.clone) script.value.name = `(Copy) ${script.value.name}`;
    const code = ref("");
    const maximized = ref(false);
    const loading = ref(false);

    const title = computed(() => {
      if (props.script) {
        return props.readonly
          ? `Viewing ${script.value.name}`
          : props.clone
          ? `Copying ${script.value.name}`
          : `Editing ${script.value.name}`;
      } else {
        return "Adding new script";
      }
    });

    // get code if editing or cloning script
    if (props.script)
      downloadScript(script.value.id, { with_snippets: props.readonly }).then(r => {
        code.value = r.code;
      });

    async function submitForm() {
      loading.value = true;
      let result = "";
      try {
        // base64 encode the script text
        script.value.code_base64 = btoa(code.value);

        // edit existing script
        if (props.script && !props.clone) {
          result = await editScript(script.value);

          // add or save cloned script
        } else {
          result = await saveScript(script.value);
        }

        onDialogOK();
        notifySuccess(result);
      } catch (e) {}

      loading.value = false;
    }

    function openTestScriptModal() {
      $q.dialog({
        component: TestScriptModal,
        componentProps: {
          script: { ...script.value, code: code.value },
          agent: agent.value,
        },
      });
    }

    function loadAgentOptions(val, update, abort) {
      if (agentOptions.value.length > 0) {
        // already loaded
        update();
        return;
      }

      update(async () => {
        await getAgentOptions();
      });
    }

    return {
      // reactive data
      formScript: script.value,
      code,
      maximized,
      loading,
      agentOptions,
      agent,

      // non-reactive data
      shellOptions,

      //computed
      getAgentOptions,
      title,

      //methods
      loadAgentOptions,
      submitForm,
      openTestScriptModal,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>