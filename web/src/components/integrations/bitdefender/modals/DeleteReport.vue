<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Delete Report
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section class="row items-center">
                <div>
                    Are you sure you want to delete the
                    <span
                        class="text-weight-bold"
                    >{{ selected[0].name }}</span> report from Bitdfender GravityZone?
                </div>
            </q-card-section>
            <q-card-actions align="right">
                <q-btn label="Cancel" v-close-popup />
                <q-btn label="Confirm" v-close-popup @click="deleteReport()" />
            </q-card-actions>
        </q-card>
    </q-dialog>
</template>

<script>
import axios from "axios";
// composable imports
import { useQuasar, useDialogPluginComponent } from "quasar";
import { notifySuccess, notifyError } from "@/utils/notify";

export default {
    name: "DeleteReport",
    emits: [...useDialogPluginComponent.emits],
    props: ['selected'],

    setup(props) {
        const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
        const $q = useQuasar();

        function deleteReport() {
            axios
                .delete(`/bitdefender/reports/delete/` + props.selected[0].id + `/`)
                .then(r => {
                    notifySuccess('The ' + props.selected[0].name + ' report has been deleted from Bitdefender GravityZone')
                    onDialogOK()
                })
                .catch(e => {
                    console.log(e)
                });
        }

        return {
            deleteReport,
            // quasar dialog plugin
            dialogRef,
            onDialogHide,
        }
    }
}
</script>