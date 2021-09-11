<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 40vw">
      <q-bar>
        Upload Mesh Exe
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit.prevent="submitForm">
        <q-card-section>
          <div class="q-gutter-sm">
            <q-radio v-model="form.arch" val="64" label="64 bit" />
            <q-radio v-model="form.arch" val="32" label="32 bit" />
          </div>
        </q-card-section>
        <q-card-section>
          <q-file
            v-model="form.meshagent"
            :rules="[val => !!val || '*Required']"
            label="Upload MeshAgent"
            stack-label
            filled
            counter
            class="full-width"
            accept=".exe"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
        </q-card-section>
        <q-card-actions>
          <q-space />
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn :loading="loading" dense flat label="Upload" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref } from "vue";
import { useDialogPluginComponent } from "quasar";
import { uploadMeshAgent } from "@/api/core";
import { notifySuccess } from "@/utils/notify";

export default {
  name: "UploadMesh",
  emits: [...useDialogPluginComponent.emits],
  setup(props) {
    // setup quasar plugins
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // upload mesh logic
    const form = ref({
      meshagent: null,
      arch: "64",
    });

    const loading = ref(false);

    async function submitForm() {
      loading.value = true;
      let result = "";

      let formData = new FormData();
      formData.append("arch", form.value.arch);
      formData.append("meshagent", form.value.meshagent);
      try {
        result = await uploadMeshAgent(formData);
        onDialogOK();
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }

      loading.value = false;
    }

    return {
      // reactive data
      form,
      loading,

      //methods
      submitForm,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>