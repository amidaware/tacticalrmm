<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Add New Model
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <q-select
                    filled
                    v-model="assetModel"
                    label="Model *"
                    :options="assetModelOptions"
                    dense
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-card-actions align="right">
                    <q-btn class="q-mb-md" label="Save" @click="onOKClick()" />
                </q-card-actions>
            </q-card-section>
        </q-card>
    </q-dialog>
</template>

<script>
import axios from "axios";
// composable imports
import { ref, onMounted, } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { notifySuccess, notifyError } from "@/utils/notify";

export default {
    name: "AddModel",
    emits: [...useDialogPluginComponent.emits],
    props: ['agent', 'manufacturer', 'category'],

    setup(props) {
        const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
        const $q = useQuasar();
        const assetModel = ref("")
        const assetModelOptions = ref([])
        const addNewModel = ref(true)

        function getTacticalAgent() {
            assetModelOptions.value.push(props.agent.wmi_detail.comp_sys_prod[0][0].IdentifyingNumber)
            assetModelOptions.value.push(props.agent.wmi_detail.comp_sys_prod[0][0].Name)
        }

        function onOKClick() {
            $q.loading.show()
            let data = {
                model_name: assetModel.value,
                model_number: assetModel.value,
                category_id: props.category.value,
                manufacturer_id: props.manufacturer.value
            }

            axios
                .post(`/snipeit/models/`, data)
                .then(r => {
                    if (r.data.status === 'error') {
                        notifyError(r.data.messages)
                    } else {
                        notifySuccess(r.data.messages)

                        $q.loading.hide()
                        onDialogOK({
                            "assetModel": assetModel.value,
                            "assetModelID": r.data.payload.id,
                            "addNewModel": addNewModel.value
                        })
                    }
                })
                .catch(e => {
                    console.log(e)
                });
        }

        onMounted(() => {
            getTacticalAgent()
        });

        return {
            assetModel,
            assetModelOptions,
            onOKClick,
            // quasar dialog plugin
            dialogRef,
            onDialogHide,
        }
    }
}
</script>