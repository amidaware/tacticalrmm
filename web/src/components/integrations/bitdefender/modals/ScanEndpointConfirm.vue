<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card>
      <q-card-section class="row items-center">
      <div class="q-mx-sm">
        <span v-if="scanType === 'quick'">Are you sure you want to initiate a Quick Scan on {{endpoint.name}}?</span>
        <span v-else>Are you sure you want to initiate a Full Scan on {{endpoint.name}}?</span>
      </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn label="Cancel" v-close-popup />
        <q-btn label="Confirm" v-if="scanType === 'quick'" v-close-popup @click="quickScanEndpoint()" />
        <q-btn label="Confirm" v-else v-close-popup @click="fullScanEndpoint()" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { ref, computed, onMounted } from "vue";
  import { useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";

  export default {
    name: "ScanEndpointConfirm",
    emits: [...useDialogPluginComponent.emits],
    props: ['scanType', 'endpoint'],
    setup(props) {
        const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
        const $q = useQuasar();

        function quickScanEndpoint(){
          console.log("quick")
            axios
            .post(`/bitdefender/endpoint/quickscan/` + props.endpoint.id + "/")
            .then(r => {
                notifySuccess("Quick scan initiated on " + props.endpoint.name);
            })
            .catch(e => {
                console.log(e.response.data)
            });
        }

        function fullScanEndpoint(){
          console.log("full")
            axios
            .post(`/bitdefender/endpoint/fullscan/` + props.endpoint.id + "/")
            .then(r => {
                notifySuccess("Full Scan initiated on " + props.endpoint.name);
            })
            .catch(e => {
                console.log(e.response.data)
            });
        }

      return {
        quickScanEndpoint,
        fullScanEndpoint,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };

</script>