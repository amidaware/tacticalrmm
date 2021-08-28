<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistent @keydown.esc="onDialogHide" :maximized="maximized">
    <q-card class="q-dialog-plugin" :style="maximized ? '' : 'width: 70vw; max-width: 90vw'">
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
        <q-card-section class="row">
          <div class="q-pa-sm col-1" style="width: auto">
            <q-icon
              class="cursor-pointer"
              :name="formScript.favorite ? 'star' : 'star_outline'"
              size="md"
              color="yellow-8"
              @[clickEvent]="formScript.favorite = !formScript.favorite"
            />
          </div>
          <div class="q-pa-sm col-2">
            <q-input
              filled
              dense
              :readonly="readonly"
              v-model="formScript.name"
              label="Name"
              :rules="[val => !!val || '*Required']"
            />
          </div>
          <div class="q-pa-sm col-2">
            <q-select
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
          </div>
          <div class="q-pa-sm col-2">
            <q-input
              type="number"
              filled
              dense
              :readonly="readonly"
              v-model.number="formScript.default_timeout"
              label="Timeout (seconds)"
              :rules="[val => val >= 5 || 'Minimum is 5']"
            />
          </div>
          <div class="q-pa-sm col-3">
            <tactical-dropdown
              hint="Press Enter or Tab when adding a new value"
              filled
              v-model="formScript.category"
              :options="categories"
              use-input
              clearable
              new-value-mode="add-unique"
              filterable
              label="Category"
              :readonly="readonly"
            />
          </div>
          <div class="q-pa-sm col-2">
            <q-input filled dense :readonly="readonly" v-model="formScript.description" label="Description" />
          </div>
        </q-card-section>
        <div class="q-px-sm q-pt-none q-pb-sm q-mt-none row">
          <tactical-dropdown
            v-model="formScript.args"
            label="Script Arguments (press Enter after typing each argument)"
            class="col-12"
            filled
            use-input
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
            :readonly="readonly"
          />
        </div>

        <CodeEditor
          v-model="code"
          :style="maximized ? '--prism-height: 76vh' : '--prism-height: 70vh'"
          :readonly="readonly"
          :shell="formScript.shell"
        />
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn dense flat color="primary" label="Test Script" @click="openTestScriptModal" />
          <q-btn v-if="!readonly" :loading="loading" dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composable imports
import { ref, computed, watch } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { saveScript, editScript, downloadScript } from "@/api/scripts";
import { notifySuccess } from "@/utils/notify";

// ui imports
import CodeEditor from "@/components/ui/CodeEditor";
import TestScriptModal from "@/components/scripts/TestScriptModal";
import TacticalDropdown from "@/components/ui/TacticalDropdown";

// static data
import { shellOptions } from "@/composables/scripts";

export default {
  name: "ScriptFormModal",
  emits: [...useDialogPluginComponent.emits],
  components: {
    CodeEditor,
    TacticalDropdown,
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

    // script form logic
    const script = props.script ? ref(Object.assign({}, props.script)) : ref({ shell: "powershell", timeout: 90 });

    if (props.clone) script.value.name = `(Copy) ${script.value.name}`;
    const code = ref("");
    const maximized = ref(false);
    const loading = ref(false);

    const clickEvent = computed(() => (!props.readonly ? "click" : null));
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
        script.value.code = r.code;
      });

    watch(code, (newValue, oldValue) => {
      if (newValue) {
        script.value.code = code.value;
      }
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
          script: script.value,
        },
      });
    }

    return {
      // reactive data
      formScript: script.value,
      code,
      maximized,
      loading,

      // non-reactive data
      shellOptions,

      //computed
      clickEvent,
      title,

      //methods
      submitForm,
      openTestScriptModal,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>