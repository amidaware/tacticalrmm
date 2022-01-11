<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Checkin {{agent.hostname}}
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <q-form @submit="checkin()" class="q-pa-md">
                    <div class="q-gutter-sm text-center">
                        <q-select filled dense v-model="location" label="Locations" :options="locationOptions"
                            :rules="[(val) => !!val || '*Required']" />

                        <q-input v-model="notes" filled placeholder="Type notes in here" autogrow />
                    </div>
                    <q-card-actions align="right">
                        <q-btn label="Add" type="submit" />

                        <q-btn label="Cancel" v-close-popup />
                    </q-card-actions>
                </q-form>
            </q-card-section>
        </q-card>
    </q-dialog>
</template>

<script>
    import axios from "axios";
    // composable imports
    import { ref, computed, onMounted, watch } from "vue";
    import { useQuasar, useDialogPluginComponent, date } from "quasar";
    import { notifySuccess, notifyError } from "@/utils/notify";

    export default {
        name: "Checkin",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent', 'asset'],
        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();
            const assetOptions = ref([])
            const asset = ref([])
            const location = ref("")
            const locationOptions = ref([])
            const snipeitAssetTag = ref([])
            const agentAssetTag = ref([])
            const notes = ref("")

            function getLocations() {
                axios
                    .get(`/snipeit/locations/`)
                    .then(r => {
                        locationOptions.value = []
                        for (let location of r.data.rows) {
                            let locationObj = {
                                label: location.name,
                                value: location.id
                            }
                            locationOptions.value.push(locationObj)
                        }

                        locationOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)

                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }

            function checkin() {
                let data = {
                    id: props.asset.id,
                    location_id: location.value.value,
                    note: notes.value
                }
                axios
                    .post(`/snipeit/hardware/` + props.asset.id + `/checkin/`, data)
                    .then(r => {
                        if (r.data.status === 'error') {
                            notifyError(r.data.messages)
                        } else {
                            notifySuccess(r.data.messages)
                            onDialogOK()
                        }
                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }
            onMounted(() => {
                getLocations()
            });

            return {
                assetOptions,
                asset,
                location,
                locationOptions,
                notes,
                checkin,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };

</script>