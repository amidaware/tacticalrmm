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
        <q-card-section>
          <div class="q-gutter-sm row">
            <div class="col-5">
              <q-input :rules="[val => !!val || '*Required']" v-model="formSnippet.name" label="Name" filled dense />
            </div>
            <div class="col-2">
              <q-select
                v-model="formSnippet.shell"
                :options="shellOptions"
                label="Shell Type"
                options-dense
                filled
                dense
                emit-value
                map-options
              />
            </div>
            <div class="col-4">
              <q-input filled dense v-model="formSnippet.desc" label="Description" />
            </div>
          </div>
        </q-card-section>

        <CodeEditor
          v-model="formSnippet.code"
          :style="maximized ? '--prism-height: 80vh' : '--prism-height: 70vh'"
          :shell="formSnippet.shell"
        />
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn :loading="loading" flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composable imports
import { ref, computed } from "vue";
import { useDialogPluginComponent } from "quasar";
import { saveScriptSnippet, editScriptSnippet } from "@/api/scripts";
import { notifySuccess } from "@/utils/notify";

// ui imports
import CodeEditor from "@/components/ui/CodeEditor";

// static data
import { shellOptions } from "@/composables/scripts";

export default {
  name: "ScriptFormModal",
  emits: [...useDialogPluginComponent.emits],
  components: {
    CodeEditor,
  },
  props: {
    snippet: Object,
  },
  setup(props) {
    // setup quasar plugins
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // snippet form logic
    const snippet = props.snippet
      ? ref(Object.assign({}, props.snippet))
      : ref({ name: "", code: "", shell: "powershell" });
    const maximized = ref(false);
    const loading = ref(false);

    const title = computed(() => {
      if (props.snippet) {
        return `Editing ${snippet.value.name}`;
      } else {
        return "Adding New Script Snippet";
      }
    });

    async function submitForm() {
      loading.value = true;
      let result = "";
      try {
        // edit existing script snippet
        if (props.snippet) {
          result = await editScriptSnippet(snippet.value);

          // add script snippet
        } else {
          result = await saveScriptSnippet(snippet.value);
        }

        onDialogOK();
        notifySuccess(result);
      } catch (e) {}

      loading.value = false;
    }

    return {
      // reactive data
      formSnippet: snippet.value,
      maximized,
      loading,

      // non-reactive data
      shellOptions,

      //computed
      title,

      //methods
      submitForm,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>