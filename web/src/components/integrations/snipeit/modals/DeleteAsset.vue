<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Delete Asset
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section class="row items-center">
                <div>
                    Are you sure you want to delete the <span class="text-weight-bold">{{asset.name}}</span> asset from Snipe-IT?
                </div>
            </q-card-section>
            <q-card-actions align="right">
                <q-btn label="Cancel" v-close-popup />
                <q-btn label="Confirm" v-close-popup @click="deleteAsset()" />
            </q-card-actions>
        </q-card>
    </q-dialog>
</template>

<script>
    import axios from "axios";
    // composable imports
    import { ref, computed, onMounted, watch } from "vue";
    import { useQuasar, useDialogPluginComponent } from "quasar";
    import { notifySuccess, notifyError } from "@/utils/notify";

    export default {
        name: "DeleteAsset",
        emits: [...useDialogPluginComponent.emits],
        props: ['asset', 'agent'],

        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            function deleteAsset() {
                axios
                    .delete(`/snipeit/hardware/` + props.asset.id + `/`)
                    .then(r => {
                        if (r.data.status === 'error') {
                            notifyError(r.data.messages)
                        } else {
                            notifySuccess(props.agent.hostname + " has been deleted from Snipe-IT")
                        }
                        onDialogOK()
                    })
                    .catch(e => {
                        console.log(e)
                    });
            }

            return {
                deleteAsset,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            }
        }
    }
</script>