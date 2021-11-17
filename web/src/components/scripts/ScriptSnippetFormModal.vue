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
        <div class="row">
          <q-input
            :rules="[val => !!val || '*Required']"
            class="q-pa-sm col-4"
            v-model="formSnippet.name"
            label="Name"
            filled
            dense
          />
          <q-select
            v-model="formSnippet.shell"
            :options="shellOptions"
            class="q-pa-sm col-2"
            label="Shell Type"
            options-dense
            filled
            dense
            emit-value
            map-options
          />
          <q-input class="q-pa-sm col-6" filled dense v-model="formSnippet.desc" label="Description" />
        </div>

        <v-ace-editor
          v-model:value="formSnippet.code"
          :lang="formSnippet.shell === 'cmd' ? 'batchfile' : formSnippet.shell"
          theme="tomorrow_night"
          :style="{ height: `${maximized ? '80vh' : '70vh'}` }"
          wrap
        />
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn :loading="loading" dense flat label="Save" color="primary" type="submit" />
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

// ace editor imports
import { VAceEditor } from "vue3-ace-editor";

import "ace-builds/src-noconflict/mode-powershell";
import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/mode-batchfile";
import "ace-builds/src-noconflict/theme-tomorrow_night";

// static data
import { shellOptions } from "@/composables/scripts";

export default {
  name: "ScriptFormModal",
  emits: [...useDialogPluginComponent.emits],
  components: {
    VAceEditor,
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
      try {
        const result = props.snippet ? await editScriptSnippet(snippet.value) : await saveScriptSnippet(snippet.value);
        onDialogOK();
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }

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