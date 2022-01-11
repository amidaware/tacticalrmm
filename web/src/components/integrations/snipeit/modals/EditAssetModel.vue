<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Edit {{selected.manufacturer}} - {{selected.modelNumber}}

                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <q-form @submit="saveAssetModel()">
                    <div class="q-gutter-sm text-center">
                        <q-input filled v-model="assetName" label="Name" dense
                            :rules="[(val) => !!val || '*Required']" />
                        <q-input filled v-model="assetModelNumber" label="Model Number" dense
                            :rules="[(val) => !!val || '*Required']" />
                        <q-select filled v-model="assetManufacturer" label="Manufacturer"
                            :options="assetManufacturerOptions" dense :rules="[(val) => !!val || '*Required']" />
                        <q-select filled v-model="assetCategory" label="Category" :options="assetCategoryOptions" dense
                            :rules="[(val) => !!val || '*Required']" />

                    </div>

                    <q-card-actions align="right">

                        <q-btn label="Cancel" v-close-popup />
                        <q-btn label="Save" type="submit" />
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
        name: "Checkout",
        emits: [...useDialogPluginComponent.emits],
        props: ['selected'],
        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const assetModel = ref([])
            const assetName = ref("")
            const assetModelNumber = ref("")
            const assetManufacturer = ref("")
            const assetManufacturerOptions = ref([])
            const assetCategory = ref("")
            const assetCategoryOptions = ref([])

            function getAssetModel() {
                axios
                    .get(`/snipeit/models/` + props.selected[0].id + `/`)
                    .then(r => {
                        assetModel.value = r.data
                        assetName.value = assetModel.value.name
                        assetModelNumber.value = assetModel.value.model_number
                        assetManufacturer.value = { label: assetModel.value.manufacturer.name, value: assetModel.value.manufacturer.id }
                        assetCategory.value = { label: assetModel.value.category.name, value: assetModel.value.category.id }
                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }

            function getCategories() {
                axios
                    .get(`/snipeit/categories/`)
                    .then(r => {
                        assetCategoryOptions.value = []
                        for (let category of r.data.rows) {
                            let assetCategoryObj = {
                                label: category.name,
                                value: category.id,
                            }
                            assetCategoryOptions.value.push(assetCategoryObj)
                        }
                        assetCategoryOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)
                        $q.loading.hide()
                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }
            function getManufacturers() {
                axios
                    .get(`/snipeit/manufacturers/`)
                    .then(r => {
                        assetManufacturerOptions.value = []
                        for (let manufacturer of r.data.rows) {
                            let assetManufacturerObj = {
                                label: manufacturer.name,
                                value: manufacturer.id,
                            }
                            assetManufacturerOptions.value.push(assetManufacturerObj)
                        }
                        assetManufacturerOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)

                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }

            function saveAssetModel() {
                let data = {
                    name: assetName.value,
                    model_number: assetModelNumber.value,
                    manufacturer_id: assetManufacturer.value.value,
                    category_id: assetCategory.value.value
                }
                axios
                    .put(`/snipeit/models/` + props.selected[0].id + `/`, data)
                    .then(r => {
                        console.log(r.data)
                        notifySuccess('Asset model edited successfully')
                        onDialogOK()

                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            }

            onMounted(() => {
                getAssetModel()
                getCategories()
                getManufacturers()
            });

            return {
                assetModel,
                assetName,
                assetModelNumber,
                assetManufacturer,
                assetManufacturerOptions,
                assetCategory,
                assetCategoryOptions,
                saveAssetModel,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };

</script>