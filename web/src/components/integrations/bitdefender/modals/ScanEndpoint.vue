<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        <span v-if="scanType === 'quick'">Quick Scan</span>
        <span v-else>Full Scan</span>
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section class="row items-center">
        <div>
          <span
            v-if="scanType === 'quick'"
          >Are you sure you want to initiate a Quick Scan on {{ endpoint.name }}?</span>
          <span v-else>Are you sure you want to initiate a Full Scan on {{ endpoint.name }}?</span>
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn label="Cancel" v-close-popup />
        <q-btn
          label="Confirm"
          v-if="scanType === 'quick'"
          v-close-popup
          @click="quickScanEndpoint()"
        />
        <q-btn label="Confirm" v-else v-close-popup @click="fullScanEndpoint()" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import axios from "axios";
// composable imports
import { useQuasar, useDialogPluginComponent } from "quasar";
import { notifySuccess } from "@/utils/notify";

export default {
  name: "ScanEndpoint",
  emits: [...useDialogPluginComponent.emits],
  props: ['scanType', 'endpoint'],
  setup(props) {
    const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
    const $q = useQuasar();

    function quickScanEndpoint() {
      axios
        .post(`/bitdefender/endpoint/quickscan/` + props.endpoint.id + "/")
        .then(r => {
          notifySuccess("Quick scan initiated on " + props.endpoint.name);
        })
        .catch(e => {
          console.log(e.response.data)
        });
    }

    function fullScanEndpoint() {
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