<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit.prevent="submitForm">
        <q-card-section>
          <span v-if="!APIKey">API Key will be generated on save</span>
        </q-card-section>
        <!-- name -->
        <q-card-section>
          <q-input label="Name" outlined dense v-model="localKey.name" :rules="[val => !!val || '*Required']" />
        </q-card-section>

        <!-- user -->
        <q-card-section>
          <tactical-dropdown outlined v-model="localKey.user" label="User" :options="userOptions" mapOptions />
        </q-card-section>

        <!-- key -->
        <q-card-section v-if="APIKey">
          <q-input readonly label="Key" outlined dense v-model="localKey.key" />
        </q-card-section>

        <!-- expiration -->
        <q-card-section>
          <q-input
            type="datetime-local"
            dense
            label="Key Expiration (Not required)"
            stack-label
            filled
            v-model="localKey.expiration"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn flat label="Submit" color="primary" type="submit" :loading="loading" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, computed } from "vue";
import { useDialogPluginComponent } from "quasar";
import { saveAPIKey, editAPIKey } from "@/api/accounts";
import { useUserDropdown } from "@/composables/accounts";
import { notifySuccess } from "@/utils/notify";
import { formatDateInputField, formatDateStringwithTimezone } from "@/utils/format";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";

export default {
  components: { TacticalDropdown },
  name: "APIKeysForm",
  emits: [...useDialogPluginComponent.emits],
  props: { APIKey: Object },
  setup(props) {
    // setup quasar plugins
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // setup dropdowns
    const { userOptions } = useUserDropdown(true);

    // setup api key form logic
    const key = props.APIKey ? ref(Object.assign({}, props.APIKey)) : ref({ name: "", expiration: null });
    const loading = ref(false);

    // remove Z from date string
    if (props.APIKey) {
      key.value.expiration = formatDateInputField(key.value.expiration);
    }

    const title = computed(() => (props.APIKey ? "Edit API Key" : "Add API Key"));

    async function submitForm() {
      loading.value = true;

      const data = {
        ...key.value,
      };

      // convert date to local timezone if exists
      if (data.expiration) data.expiration = formatDateStringwithTimezone(data.expiration);

      try {
        const result = props.APIKey ? await editAPIKey(data) : await saveAPIKey(data);
        onDialogOK();
        notifySuccess(result);
        loading.value = false;
      } catch (e) {
        loading.value = false;
      }
    }
    return {
      // reactive data
      localKey: key,
      loading,
      userOptions,

      // computed
      title,

      // methods
      submitForm,

      // quasar dialog
      dialogRef,
      onDialogHide,
      onDialogOK,
    };
  },
};
</script>