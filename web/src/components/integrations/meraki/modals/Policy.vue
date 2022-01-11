<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                {{agent.hostname}} Device Policy
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <q-select filled v-model="policy" label="Device Policy" :options="policyOptions" dense
                    :rules="[(val) => !!val || '*Required']">
                    <template v-slot:option="scope">
                        <q-item v-bind="scope.itemProps">
                            <q-item-section>
                                <q-item-label>{{ scope.opt.label }}</q-item-label>
                                <q-item-label caption>{{ scope.opt.description }}</q-item-label>
                            </q-item-section>
                        </q-item>
                    </template>
                </q-select>
            </q-card-section>
            <q-card-actions align="right">
                <q-btn label="Cancel" v-close-popup />
                <q-btn label="Save" @click="savePolicy()" />
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
        name: "AddModel",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent', 'selected'],

        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();
            const policy = ref("")
            const policyOptions = ref([{ label: 'Whitelisted', value: 'Whitelisted', description: 'No bandwidth limits or splash page' }, { label: 'Blocked', value: 'Blocked', description: 'No access allowed' }, { label: 'Normal', value: 'Normal', description: '' }])

            function getDevicePolicy() {
                $q.loading.show({
                    message: 'Getting device policy for ' + props.agent.hostname
                })
                axios
                    .get(`/meraki/` + props.selected.value[0].networkId + `/clients/` + props.selected.value[0].mac + `/policy/`)
                    .then(r => {
                        policy.value = r.data.devicePolicy
                        if (r.data.errors) {
                            notifyError(r.data.errors[0])
                        }
                        $q.loading.hide()
                    })
                    .catch(e => { });
            }

            function savePolicy() {
                $q.loading.show({
                    message: 'Applying new device policy for ' + props.agent.hostname
                })
                let data = {
                    devicePolicy: policy.value.value
                }
                axios
                    .put(`/meraki/` + props.selected.value[0].networkId + `/clients/` + props.selected.value[0].mac + `/policy/`, data)
                    .then(r => {
                        policy.value = r.data.devicePolicy

                        if (r.data.errors) {
                            notifyError(r.data.errors[0])
                        }
                        $q.loading.hide()
                        notifySuccess('Device policy successfully applied to ' + props.agent.hostname)
                        onDialogOK()
                    })
                    .catch(e => { });
            }

            onMounted(() => {
                getDevicePolicy()
            });

            return {
                getDevicePolicy,
                savePolicy,
                policy,
                policyOptions,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            }
        }
    }
</script>