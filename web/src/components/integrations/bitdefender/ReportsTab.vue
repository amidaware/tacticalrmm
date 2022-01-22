<template>
    <div class="q-pa-md">
        <q-card>
            <q-table
                :rows="rows"
                :columns="columns"
                row-key="id"
                :selected-rows-label="getSelectedString"
                selection="multiple"
                v-model:selected="selected"
                :pagination="pagination"
            >
                <template v-slot:top-left>
                    <q-btn flat dense @click="getReports()" icon="refresh" />
                    <q-btn-dropdown label="Actions" flat :disable="actionBtnDisabled">
                        <q-list>
                            <q-item clickable v-close-popup @click="checkout()">
                                <q-item-section>
                                    <q-item-label>Restore</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item clickable v-close-popup @click="checkin()">
                                <q-item-section>
                                    <q-item-label>Remove</q-item-label>
                                </q-item-section>
                            </q-item>
                        </q-list>
                    </q-btn-dropdown>
                </template>
                <template v-slot:top-right>
                    <q-input
                        outlined
                        v-model="filter"
                        label="Search"
                        dense
                        debounce="300"
                        clearable
                    >
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
import { ref, onMounted, watch } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";

const columns = [
    {
        name: "name",
        required: true,
        label: "Name",
        align: "left",
        sortable: true,
        field: row => row.name,
        format: val => `${val}`,
    },
    {
        name: "ip",
        required: true,
        label: "IP",
        align: "left",
        sortable: true,
        field: row => row.ip,
        format: val => `${val}`,
    },
    {
        name: "threatName",
        required: true,
        label: "Threat",
        align: "left",
        sortable: true,
        field: row => row.threatName,
        format: val => `${val}`,
    },

    {
        name: "quarantinedOn",
        required: true,
        label: "Quarantined On",
        align: "left",
        sortable: true,
        field: row => row.quarantinedOn,
        format: val => `${val}`,
    },
    {
        name: "canBeRemoved",
        required: true,
        label: "Can Be Removed",
        align: "left",
        sortable: true,
        field: row => row.canBeRemoved,
        format: val => `${val}`,
    },
    {
        name: "canBeRestored",
        required: true,
        label: "Can Be Restored",
        align: "left",
        sortable: true,
        field: row => row.canBeRestored,
        format: val => `${val}`,
    },
    {
        name: "details",
        required: true,
        label: "Details",
        align: "left",
        sortable: true,
        field: row => row.details,
        format: val => `${val}`,
    }
]

export default {
    name: "Reports",
    emits: [...useDialogPluginComponent.emits],
    props: ['endpoint'],

    setup(props) {
        const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
        const $q = useQuasar();

        const rows = ref([])
        const selected = ref([])
        let actionBtnDisabled = ref(true)

        function getReports() {
            $q.loading.show()
            axios
                .get(`/bitdefender/reports/` + props.endpoint.id + `/`)
                .then(r => {
                    console.log(r.data)
                    rows.value = []
                    for (let item of r.data.result.items) {
                        let quarantineObj = {
                            name: item.endpointName,
                            ip: item.endpointIP,
                            threatName: item.threatName,
                            quarantinedOn: item.quarantinedOn,
                            canBeRemoved: item.canBeRemoved,
                            canBeRestored: item.canBeRestored,
                            details: item.details.filePath
                        }
                        rows.value.push(quarantineObj)
                    }

                    $q.loading.hide()
                })
                .catch(e => {
                    console.log(e)
                });
        }
        watch(selected, (val) => {

            if (selected.value.length > 0) {
                actionBtnDisabled.value = false
            } else {
                actionBtnDisabled.value = true
            }
        })

        onMounted(() => {
            getReports()
        });

        return {
            pagination: {
                sortBy: 'desc',
                descending: false,
                page: 1,
                rowsPerPage: 100
            },
            rows,
            columns,
            filter: ref(""),
            selected,
            actionBtnDisabled,
            getSelectedString() {
                return selected.value.length === 0 ? '' : `${selected.value.length} record${selected.value.length > 1 ? 's' : ''} selected of ${rows.value.length}`
            },
            getReports,
            // quasar dialog plugin
            dialogRef,
            onDialogHide,
        };
    },
};

</script>