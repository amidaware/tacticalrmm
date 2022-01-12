<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{name}}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <q-form @submit="submitConfig()">
          <div class="q-gutter-y-md">
            <q-input outlined v-model="apikey" label="API Key" stack-label
              placeholder="32hk20f3kjf30hjf0kk54uifdsfaof32" hint="Check with the API provider"
              :rules="[(val) => !!val || '*Required']" dense autogrow />
            <q-input outlined v-model="apiurl" label="Base URL" stack-label
              placeholder="https://api.provider.com/api/v1/" hint="Check with the API provider"
              :rules="[(val) => !!val || '*Required']" dense />
            <q-input v-if="name === 'Bitdefender GravityZone'" outlined v-model="companyID" label="Company ID"
              stack-label placeholder="fsdja90ueji3lkjdsifj892jf3i" hint="Check with the API provider"
              :rules="[(val) => !!val || '*Required']" dense />
            <q-card-actions align="right">
              <q-btn v-if="!enabled" @click="enableChoice=true" label="Enable" type="submit"></q-btn>
              <q-btn v-if="enabled" label="Edit" type="submit" class="q-mr-md"></q-btn>
              <q-btn v-if="enabled" @click="enableChoice=false" label="Disable" type="submit"></q-btn>
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
  import { ref, computed, onMounted } from "vue";
  import { useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess } from "@/utils/notify";

  export default {
    name: "IntegrationConfigModal",
    emits: [...useDialogPluginComponent.emits],
    props: ['id', 'name'],

    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();
      let config = ref("")
      let apikey = ref("")
      let apiurl = ref("")
      let companyID = ref("")
      let enabled = ref("")
      let enableChoice = ref("")
      let id = ref("")

      const getIntegration = () => {
        axios
          .get(`/integrations/` + props.id + `/`)
          .then(r => {
            config.value = r.data
            id.value = r.data.id
            apikey.value = r.data.configuration.api_key
            apiurl.value = r.data.configuration.api_url
            companyID.value = r.data.configuration.company_id
            enabled.value = r.data.enabled
          })
          .catch(e => {
          });
      };

      function submitConfig() {
        if (enableChoice.value === true) {
          let data = {
            apikey: apikey.value,
            apiurl: apiurl.value,
            companyID: companyID.value,
            enabled: true
          };
          axios
            .post(`/integrations/` + props.id + `/`, data)
            .then(r => {
              notifySuccess(props.name + " integration enabled!");
              onDialogOK()
            })
            .catch(e => {
              console.log(e.response.data)
            });
        } else if (enableChoice.value === false) {
          let data = {
            apikey: apikey.value,
            apiurl: apiurl.value,
            companyID: companyID.value,
            enabled: false
          };
          axios
            .post(`/integrations/` + props.id + `/`, data)
            .then(r => {
              apikey.value = ""
              apiurl.value = ""
              companyID.value = ""
              notifySuccess(props.name + " integration disabled!");
              onDialogOK()
            })
            .catch(e => {
              console.log(e.response.data)
            });

        } else {
          let data = {
            apikey: apikey.value,
            apiurl: apiurl.value,
            companyID: companyID.value,
          };
          axios
            .put(`/integrations/` + props.id + `/`, data)
            .then(r => {
              notifySuccess(props.name + " integration edited!");
              onDialogOK()
            })
            .catch(e => {
            });
        }
      }

      onMounted(() => {
        getIntegration();
      });

      return {
        config,
        apikey,
        apiurl,
        companyID,
        enabled,
        enableChoice,
        submitConfig,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };
</script>