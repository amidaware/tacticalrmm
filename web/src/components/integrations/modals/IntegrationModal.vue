<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ integration.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <q-form @submit="submitConfig()">
          <div class="q-gutter-y-md">
            <q-input
              outlined
              v-model="apiKey"
              label="API Key"
              stack-label
              placeholder="32hk20f3kjf30hjf0kk54uifdsfaof32"
              hint="Check with the API provider"
              :rules="[(val) => !!val || '*Required']"
              dense
              autogrow
            />
            <q-input
              outlined
              v-model="apiUrl"
              label="Base URL"
              stack-label
              placeholder="https://api.provider.com/api/v1/"
              hint="Check with the API provider"
              :rules="[(val) => !!val || '*Required']"
              dense
            />
            <q-input
              v-if="integration.name === 'Bitdefender GravityZone'"
              outlined
              v-model="companyId"
              label="Company ID"
              stack-label
              placeholder="fsdja90ueji3lkjdsifj892jf3i"
              hint="Check with the API provider"
              :rules="[(val) => !!val || '*Required']"
              dense
            />
            <q-card-actions align="right">
              <q-btn label="Save" type="submit"></q-btn>
            </q-card-actions>
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import axios from "axios";
// composable imports
import { ref, onMounted } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { notifySuccess } from "@/utils/notify";

export default {
  name: "IntegrationConfigModal",
  emits: [...useDialogPluginComponent.emits],
  props: ['integration'],

  setup(props) {
    const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
    const $q = useQuasar();

    let apiKey = ref("")
    let apiUrl = ref("")
    let companyId = ref("")
    let enabled = ref("")

    function getIntegration() {
      apiKey.value = props.integration.configuration.api_key
      apiUrl.value = props.integration.configuration.api_url
      companyId.value = props.integration.configuration.company_id
      enabled.value = props.integration.enabled
    };

    function submitConfig() {
      let data = {
        apiKey: apiKey.value,
        apiUrl: apiUrl.value,
        companyId: companyId.value
      }

      axios
        .post(`/integrations/` + props.integration.id + `/`, data)
        .then(r => {
          if (props.integration.enabled) {
            notifySuccess(props.integration.name + " integration edited!");
            onDialogOK()
          } else {
            notifySuccess(props.integration.name + " integration enabled!");
            onDialogOK()
          }

        })
        .catch(e => {
          console.log(e.response.data)
        })
    }

    onMounted(() => {
      getIntegration();
    });

    return {
      apiKey,
      apiUrl,
      companyId,
      submitConfig,
      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>