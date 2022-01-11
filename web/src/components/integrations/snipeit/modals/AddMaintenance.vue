<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Add Maintenance
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <q-form @submit="addMaintenance()">
                    <q-input filled v-model="maintenanceTitle" label="Title" dense
                        :rules="[(val) => !!val || '*Required']" />
                    <q-select filled dense v-model="assetHardware" label="Asset" :options="assetOptions"
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
                    <q-select filled dense v-model="assetSupplier" label="Supplier" :options="assetSupplierOptions"
                        :rules="[(val) => !!val || '*Required']" />

                    <q-select filled dense v-model="assetMaintenanceType" label="Maintenance Type"
                        :options="assetMaintenanceTypeOptions" :rules="[(val) => !!val || '*Required']" />
                    <div class="row q-pt-none">
                        <div class="col-6 q-mr-md">
                            <q-input filled dense label="Start Date" v-model="startDate" mask="date" :rules="['date']">
                                <template v-slot:append>
                                    <q-icon name="event" class="cursor-pointer">
                                        <q-popup-proxy ref="qDateProxy" cover transition-show="scale"
                                            transition-hide="scale">
                                            <q-date v-model="startDate">
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
                            <q-input filled dense label="Estimated Completion Date" v-model="completionDate" mask="date"
                                :rules="['date']">
                                <template v-slot:append>
                                    <q-icon name="event" class="cursor-pointer">
                                        <q-popup-proxy ref="qDateProxy" cover transition-show="scale"
                                            transition-hide="scale">
                                            <q-date v-model="completionDate">
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
                    <q-input filled dense v-model="cost" label="Cost" prefix="$"
                        :rules="[(val) => !!val || '*Required']" style="width:150px" mask="#.##" fill-mask="0"
                        reverse-fill-mask />
                    <q-input v-model="notes" filled placeholder="Type notes in here" autogrow />

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
        name: "AddMaintenance",
        emits: [...useDialogPluginComponent.emits],
        props: ['asset'],

        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();
            const assetHardware = ref([])
            const assetOptions = ref([])
            const assetSupplier = ref("")
            const assetSupplierOptions = ref([])
            const assetMaintenanceType = ref(null)
            const assetMaintenanceTypeOptions = [{ label: 'Calibration', value: 'Calibration' }, { label: 'Hardware Support', value: 'Hardware Support' }, { label: 'Maintenance', value: 'Maintenance' }, { label: 'PTA', value: 'PTA' }, { label: 'Repair', value: 'Repair' }, { label: 'Software Support', value: 'Software Support' }, { label: 'Upgrade', value: 'Upgrade' }]
            const maintenanceTitle = ref("")
            const startDate = ref(null)
            const completionDate = ref(null)
            const cost = ref("")
            const notes = ref("")

            function getHardware() {
                console.log(props.asset)
                let assetObj = {
                    label: props.asset.name,
                    value: props.asset.id,
                    description: props.asset.assigned_to ? props.asset.model.name + ' ' + props.asset.model_number + ' -> ' + props.asset.assigned_to.name : props.asset.model.name + ' ' + props.asset.model_number
                }
                assetHardware.value = assetObj
                assetOptions.value.push(assetObj)
                getSuppliers()
                // $q.loading.show()
                // asset
                //     axios
                //     .get(`/snipeit/hardware/`, { params: { status: 'All' } })
                //     .then(r => {
                //         console.log(r.data)
                //         for(let asset of r.data.rows){
                //             let assetObj = {
                //                 label: asset.name,
                //                 value: asset.id,
                //                 description: asset.assigned_to ? asset.model.name + ' ' + asset.model_number + ' -> ' + asset.assigned_to.name : asset.model.name + ' ' + asset.model_number
                //             }
                //             assetOptions.value.push(assetObj)
                //             assetOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)

                //         }
                //         getSuppliers()
                //     })
                //     .catch(e => {
                //         console.log(e)
                //     });
            }

            function getSuppliers() {
                $q.loading.show()
                axios
                    .get(`/snipeit/suppliers/`)
                    .then(r => {

                        for (let supplier of r.data.rows) {
                            let supplierObj = {
                                label: supplier.name,
                                value: supplier.id,
                            }
                            assetSupplierOptions.value.push(supplierObj)
                            assetSupplierOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)

                        }
                        $q.loading.hide()
                    })
                    .catch(e => {
                        console.log(e)
                    });
            }

            function addMaintenance() {
                let data = {
                    title: maintenanceTitle.value,
                    asset_maintenance_type: assetMaintenanceType.value.label,
                    asset_id: props.asset.id,
                    supplier_id: assetSupplier.value.value,
                    start_date: date.formatDate(startDate.value, 'YYYY-MM-DD'),
                    completion_date: date.formatDate(completionDate.value, 'YYYY-MM-DD'),
                    cost: cost.value,
                }
                axios
                    .post(`/snipeit/maintenances/`, data)
                    .then(r => {
                        if (r.data.status === 'error') {
                            notifyError("Please try again")
                        } else {
                            notifySuccess("A maintenance entry has been added for " + props.asset.name)
                            onDialogOK()
                        }

                    })
                    .catch(e => {
                        console.log(e)
                    });
            }

            onMounted(() => {
                getHardware()
            });

            return {
                assetHardware,
                assetOptions,
                assetSupplier,
                assetSupplierOptions,
                maintenanceTitle,
                assetMaintenanceType,
                assetMaintenanceTypeOptions,
                startDate,
                completionDate,
                cost,
                notes,
                addMaintenance,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            }
        }
    }
</script>