<template>
    <div class="q-pa-md">
        <q-card>
            <q-table :rows="rows" :columns="columns" row-key="id" selection="single" v-model:selected="selected"
                :pagination="pagination" :filter="filter">
                <template v-slot:top-left>
                    <q-btn flat dense @click="getAssetModels()" icon="refresh" />
                    <q-btn-dropdown label="Actions" flat :disable="actionBtnDisabled">
                        <q-list>
                            <q-item clickable v-close-popup @click="editAssetModel()">
                                <q-item-section>
                                    <q-item-label>Edit</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item clickable v-close-popup @click="deleteAssetModel()">
                                <q-item-section>
                                    <q-item-label>Delete</q-item-label>
                                </q-item-section>
                            </q-item>
                        </q-list>
                    </q-btn-dropdown>
                </template>
                <template v-slot:top-right>
                    <q-input outlined v-model="filter" label="Search" dense debounce="300" clearable>
                        <template v-slot:prepend>
                            <q-icon name="search" />
                        </template>
                    </q-input>
                </template>
            </q-table>
        </q-card>
    </div>
</template>

<script>
    import axios from "axios";
    // composable imports
    import { ref, computed, onMounted, watch } from "vue";
    import { useMeta, useQuasar, useDialogPluginComponent, date } from "quasar";
    import { notifySuccess, notifyError } from "@/utils/notify";
    import EditAssetModel from "@/components/integrations/snipeit/modals/EditAssetModel";
    import DeleteAssetModel from "@/components/integrations/snipeit/modals/DeleteAssetModel";

    const columns = [
        {
            name: "manufacturer",
            label: "Manufacturer",
            align: "left",
            field: (row) => row.manufacturer,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "name",
            label: "Model Name",
            align: "left",
            field: (row) => row.name,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "modelNumber",
            label: "Model Number",
            align: "left",
            field: (row) => row.modelNumber,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "category",
            align: "left",
            label: "Category",
            field: (row) => row.category,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "assetCount",
            align: "left",
            label: "Asset Count",
            field: (row) => row.assetCount,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
    ]
    export default {
        name: "ModelsTab",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent'],
        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const rows = ref([])
            const selected = ref([])
            let actionBtnDisabled = ref(true)

            function getAssetModels() {
                $q.loading.show()
                rows.value = []
                axios
                    .get(`/snipeit/models/`)
                    .then(r => {
                        for (let model of r.data.rows) {
                            let modelObj = {
                                id: model.id,
                                manufacturer: model.manufacturer.name,
                                name: model.name,
                                modelNumber: model.model_number,
                                category: model.category.name,
                                assetCount: model.assets_count,
                            }
                            rows.value.push(modelObj)
                        }
                        $q.loading.hide()
                    })
                    .catch(e => { });
            }

            function editAssetModel() {
                $q.dialog({
                    component: EditAssetModel,
                    componentProps: {
                        selected: selected.value
                    }
                }).onOk(() => {
                    getAssetModels()
                })
            }

            function deleteAssetModel() {
                $q.dialog({
                    component: DeleteAssetModel,
                    componentProps: {
                        selected: selected.value
                    }
                }).onOk(() => {
                    getAssetModels()
                })
            }

            watch(selected, (val) => {
                if (selected.value.length > 0) {
                    actionBtnDisabled.value = false
                } else {
                    actionBtnDisabled.value = true
                }
            })

            onMounted(() => {
                getAssetModels();
            });

            return {
                pagination: {
                    sortBy: 'manufacturer',
                    descending: false,
                    rowsPerPage: 100
                },
                columns,
                rows,
                selected,
                filter: ref(""),
                actionBtnDisabled,
                getAssetModels,
                editAssetModel,
                deleteAssetModel,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };
</script>