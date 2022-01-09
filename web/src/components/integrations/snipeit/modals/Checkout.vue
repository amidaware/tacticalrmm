<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
        <q-layout view="hHh Lpr lff" container class="shadow-2 rounded-borders q-dialog-plugin bg-white">
            <q-header class="bg-grey-3 text-black">
                <q-bar>
                    Checkout {{agent.hostname}}
                    <q-space />
                    <q-btn dense flat icon="close" v-close-popup>
                        <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                    </q-btn>
                </q-bar>
            </q-header>
            <q-page-container class="bg-white">
                <q-page padding>
                    <q-form @submit="checkout()">
                        <div class="q-gutter-sm text-center">
                            <q-radio v-model="checkoutToType" val="user" label="User" />
                            <q-radio v-model="checkoutToType" val="asset" label="Asset" />
                            <q-radio v-model="checkoutToType" val="location" label="Location" />
                            <q-select v-if="checkoutToType === 'user'" filled dense use-chips v-model="user"
                                label="Users" :options="userOptions" :rules="[(val) => !!val || '*Required']" />
                            <q-select v-if="checkoutToType === 'asset'" filled dense v-model="asset" label="Assets"
                                :options="assetOptions" :rules="[(val) => !!val || '*Required']" />
                            <q-select v-if="checkoutToType === 'location'" filled dense v-model="location"
                                label="Locations" :options="locationOptions" :rules="[(val) => !!val || '*Required']" />
                            <div class="row q-pt-none">
                                <div class="col-6 q-mr-md">
                                    <q-input filled dense label="Checkout Date" v-model="checkoutDate" mask="date"
                                        :rules="['date']">
                                        <template v-slot:append>
                                            <q-icon name="event" class="cursor-pointer">
                                                <q-popup-proxy ref="qDateProxy" cover transition-show="scale"
                                                    transition-hide="scale">
                                                    <q-date v-model="checkoutDate">
                                                        <div class="row items-center justify-end">
                                                            <q-btn v-close-popup label="Close" color="primary" flat />
                                                        </div>
                                                    </q-date>
                                                </q-popup-proxy>
                                            </q-icon>
                                        </template>
                                    </q-input>
                                </div>

                                <div class="col-6">
                                    <q-input filled dense label="Checkin Date" v-model="checkinDate" mask="date"
                                        >
                                        <template v-slot:append>
                                            <q-icon name="event" class="cursor-pointer">
                                                <q-popup-proxy ref="qDateProxy" cover transition-show="scale"
                                                    transition-hide="scale">
                                                    <q-date v-model="checkinDate">
                                                        <div class="row items-center justify-end">
                                                            <q-btn v-close-popup label="Close" color="primary" flat />
                                                        </div>
                                                    </q-date>
                                                </q-popup-proxy>
                                            </q-icon>
                                        </template>
                                    </q-input>
                                </div>
                            </div>

                            <q-input class="q-mt-lg" v-model="notes" filled placeholder="Type notes in here" autogrow />
                        </div>
                        <div class="q-mt-xl">
                            <q-btn label="Add" type="submit" />

                            <q-btn label="Cancel" v-close-popup />
                        </div>
                    </q-form>
                </q-page>
            </q-page-container>
        </q-layout>
    </q-dialog>
</template>

<script>
    import axios from "axios";
    // composable imports
    import { ref, computed, onMounted, watch } from "vue";
    import { useQuasar, useDialogPluginComponent, date } from "quasar";
    import { notifySuccess, notifyError } from "@/utils/notify";

    export default {
        name: "Checkout",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent', 'asset'],
        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();
            const checkoutDate = ref(null)
            const checkinDate = ref(null)
            const checkoutToType = ref("user")
            const user = ref(null)
            const userOptions = ref([])
            const asset = ref("")
            const assetOptions = ref([])
            const location = ref("")
            const locationOptions = ref([])
            const snipeitAssetTag = ref([])
            const agentAssetTag = ref([])
            const notes = ref("")

            function getUsers() {
                axios
                    .get(`/snipeit/users/`)
                    .then(r => {
                        userOptions.value = []
                        for (let user of r.data.rows) {
                            let userObj = {
                                label: user.name,
                                value: user.id
                            }
                            userOptions.value.push(userObj)
                        }
                    })
                    .catch(e => {
                        console.log(e)
                    });
            }

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
                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }


            function checkout(){
                let data = {
                    id: props.asset.id,
<<<<<<< HEAD
<<<<<<< HEAD
                    assigned_user: user.value.value,
                    checkout_to_type: checkoutToType.value,
                    checkout_at: date.formatDate(checkoutDate.value, 'YYYY-MM-DD'),
                    expected_checkin: checkinDate.value ? date.formatDate(checkinDate.value, 'YYYY-MM-DD') : null,
                    note: notes.value 
=======
                    checkout_to_type: checkoutToType.value,
                    checkout_at: date.formatDate(checkoutDate.value, 'YYYY-MM-DD'),
                    expected_checkin: checkinDate.value ? date.formatDate(checkinDate.value, 'YYYY-MM-DD') : null,
                    note: notes.value
>>>>>>> checkin/checkout and delete asset
=======
                    assigned_user: user.value.value,
                    checkout_to_type: checkoutToType.value,
                    checkout_at: date.formatDate(checkoutDate.value, 'YYYY-MM-DD'),
                    expected_checkin: checkinDate.value ? date.formatDate(checkinDate.value, 'YYYY-MM-DD') : null,
                    note: notes.value 
>>>>>>> allow Meraki integration dashboard at client level as well as agent
                }
                axios
                    .post(`/snipeit/hardware/` + props.asset.id + `/checkout/`, data)
                    .then(r => {
<<<<<<< HEAD
<<<<<<< HEAD
                        console.log(r.data)
=======
>>>>>>> checkin/checkout and delete asset
=======
                        console.log(r.data)
>>>>>>> allow Meraki integration dashboard at client level as well as agent
                        if(r.data.status === 'error'){
                            notifyError(r.data.messages)
                        }else{
                            notifySuccess(r.data.messages)
                            onDialogOK()
                        }    
                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }
            watch(checkoutToType, (selection, prevSelection) => {
                if (selection === 'location') [
                    getLocations()
                ]
            })
            onMounted(() => {
                getUsers()
            });

            return {
                checkoutDate,
                checkinDate,
                checkout,
                checkoutToType,
                user,
                userOptions,
                asset,
                assetOptions,
                location,
                locationOptions,
                notes,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };

</script>