<template>
    <div class="q-pa-md">
        <q-card>
            <q-table :rows="rows" :columns="columns" row-key="id" selection="single" v-model:selected="selected"
                :pagination="pagination" :filter="filter">
                <template v-slot:top-left>
                    <q-btn flat dense @click="getAssetMaintenances()" icon="refresh" />
                    <q-btn-dropdown label="Actions" flat :disable="actionBtnDisabled">
                        <q-list>
                            <q-item clickable v-close-popup @click="editMaintenance()">
                                <q-item-section>
                                    <q-item-label>Edit</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item clickable v-close-popup @click="deleteMaintenance()">
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
    import AddMaintenance from "@/components/integrations/snipeit/modals/AddMaintenance";
    import EditMaintenance from "@/components/integrations/snipeit/modals/EditMaintenance";
    import DeleteMaintenance from "@/components/integrations/snipeit/modals/DeleteMaintenance";

    const columns = [
        {
            name: "title",
            align: "left",
            label: "Title",
            field: (row) => row.title,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "name",
            label: "Asset Name",
            align: "left",
            field: (row) => row.name,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "assetTag",
            label: "Asset Tag",
            align: "left",
            field: (row) => row.assetTag,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "type",
            label: "Type",
            align: "left",
            field: (row) => row.type,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "location",
            label: "Location",
            align: "left",
            field: (row) => row.location,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "cost",
            align: "left",
            label: "Cost",
            field: (row) => row.cost,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "notes",
            align: "left",
            label: "Notes",
            field: (row) => row.notes,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "startDate",
            align: "left",
            label: "Start Date",
            field: (row) => row.startDate,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "finishDate",
            align: "left",
            label: "Finish Date",
            field: (row) => row.finishDate,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
    ]
    export default {
        name: "MaintenancesTab",
        emits: [...useDialogPluginComponent.emits],
        props: ['asset'],
        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const rows = ref([])
            const selected = ref([])
            let actionBtnDisabled = ref(true)

            function getAssetMaintenances() {
                $q.loading.show()
                rows.value = []
                axios
                    .get(`/snipeit/maintenances/`)
                    .then(r => {
                        rows.value = []
                        for (let maintenance of r.data.rows) {
                            if(maintenance.asset.asset_tag == props.asset.asset_tag){
                                let maintenanceObj = {
                                    id: maintenance.id,
                                    name: maintenance.asset.name,
                                    assetTag: maintenance.asset.asset_tag,
                                    type: maintenance.asset_maintenance_type,
                                    location: maintenance.location ? maintenance.location.name : "No location set",
                                    title: maintenance.title,
                                    cost: '$' + maintenance.cost,
                                    notes: maintenance.notes,
                                    startDate: maintenance.start_date ? maintenance.start_date.formatted : "No date set",
                                    finishDate: maintenance.completion_date ? maintenance.completion_date.formatted : "No date set",
                                }
                                rows.value.push(maintenanceObj)
                            }
                        }
                        $q.loading.hide()
                    })
                    .catch(e => { });
            }

            function editMaintenance() {
                $q.dialog({
                    component: EditMaintenance,
                    componentProps: {
                        selected: selected.value,
                        asset:props.asset
                    }
                }).onOk(() => {
                    getAssetMaintenances()
                })
            }

            function deleteMaintenance() {
                $q.dialog({
                    component: DeleteMaintenance,
                    componentProps: {
                        selected: selected.value
                    }
                }).onOk(() => {
                    getAssetMaintenances()
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
                getAssetMaintenances();
            });

            return {
                pagination: {
                    sortBy: 'name',
                    descending: false,
                    rowsPerPage: 100
                },
                columns,
                rows,
                selected,
                filter: ref(""),
                actionBtnDisabled,
                getAssetMaintenances,
                editMaintenance,
                deleteMaintenance,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };
</script>