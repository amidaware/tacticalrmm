<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 40vw">
      <q-bar>
        Add Script
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form id="scriptUploadForm" @submit="submitForm">
        <q-card-section>
          <q-input label="Name" outlined dense v-model="script.name" :rules="[val => !!val || '*Required']" />
        </q-card-section>

        <q-card-section>
          <q-input label="Description" outlined dense v-model="script.description" />
        </q-card-section>

        <q-card-section>
          <tactical-dropdown
            v-model="script.category"
            :options="categories"
            label="Category"
            hint="Press Enter or Tab when adding a new value"
            outlined
            filterable
            clearable
            new-value-mode="add-unique"
          />
        </q-card-section>

        <q-card-section>
          <q-file
            label="Script Upload"
            v-model="file"
            hint="Supported file types: .ps1, .bat, .py, .sh"
            filled
            dense
            counter
            accept=".ps1, .bat, .py, .sh"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
        </q-card-section>

        <q-card-section>
          <tactical-dropdown v-model="script.shell" :options="shellOptions" label="Type" outlined mapOptions />
        </q-card-section>

        <q-card-section>
          <tactical-dropdown
            v-model="script.args"
            label="Script Arguments"
            placeholder="(press Enter after typing each argument)"
            filled
            use-input
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>

        <q-card-section>
          <q-input
            label="Default Timeout"
            type="number"
            outlined
            dense
            v-model.number="script.default_timeout"
            :rules="[val => val >= 5 || 'Minimum is 5']"
          />
        </q-card-section>

        <q-card-actions>
          <q-space />
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn :loading="loading" dense flat label="Add" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, watch } from "vue";
import { useDialogPluginComponent } from "quasar";
import { saveScript } from "@/api/scripts";
import { notifySuccess } from "@/utils/notify";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown";

// static data
import { shellOptions } from "@/composables/scripts";
export default {
  components: { TacticalDropdown },
  name: "ScriptModal",
  emits: [...useDialogPluginComponent.emits],
  props: {
    categories: !Array,
  },
  setup(props) {
    // setup quasar plugins
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // script upload logic
    const script = ref({});
    const file = ref(null);
    const loading = ref(false);

    watch(file, (newValue, oldValue) => {
      if (newValue) {
        // base64 encode the script and delete file
        const reader = new FileReader();
        reader.onloadend = () => {
          script.value.script_body = reader.result;
        };

        reader.readAsText(file.value);
      } else {
        script.value.script_body = "";
      }
    });

    async function submitForm() {
      loading.value = true;
      let result = "";
      try {
        result = await saveScript(script.value);
        onDialogOK();
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }

      loading.value = false;
    }

    return {
      // reactive data
      script,
      file,
      loading,

      // non-reactive data
      shellOptions,

      // methods
      submitForm,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>