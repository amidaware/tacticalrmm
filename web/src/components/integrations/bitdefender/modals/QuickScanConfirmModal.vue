<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card>
      <q-card-section class="row items-center">
        <span class="q-ml-sm">Are you sure you want to initiate a Quick Scan for {{selected.name}}?</span>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn label="Cancel" v-close-popup />
        <q-btn label="Confirm" v-close-popup @click="quickScan()" />
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
    name: "QuickScanConfirm",
    emits: [...useDialogPluginComponent.emits],
    props: ['selected'],
    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();

    function quickScan(){

      let data = {endpoint: props.selected.id}
       axios
          .post(`/bitdefender/endpoint/quickscan/` + props.selected.id + "/")
          .then(r => {
            notifySuccess("Quick scan initiated on " + props.selected.name);
          })
          .catch(e => {
            console.log(e)
          });
    }

      return {
        quickScan,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };

</script>