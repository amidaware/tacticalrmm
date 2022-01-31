<template>
    <div class="q-pa-md">
        <q-card>
            <q-table
                :rows="rows"
                :columns="columns"
                row-key="id"
                :selected-rows-label="getSelectedString"
                selection="single"
                v-model:selected="selected"
                :pagination="pagination"
            >
                <template v-slot:top-left>
                    <q-btn flat dense @click="getReports()" icon="refresh" />
                    <q-btn-dropdown label="Actions" flat :disable="actionBtnDisabled">
                        <q-list>
                            <q-item clickable v-close-popup @click="checkin()">
                                <q-item-section>
                                    <q-item-label>Get Download Links</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item clickable v-close-popup @click="deleteReport()">
                                <q-item-section>
                                    <q-item-label>Delete Report</q-item-label>
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
import DeleteReport from "@/components/integrations/bitdefender/modals/DeleteReport";


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
        name: "type",
        required: true,
        label: "Type",
        align: "left",
        sortable: true,
        field: row => row.type,
        format: val => `${val}`,
    },
    {
        name: "occurrence",
        required: true,
        label: "Occurrence",
        align: "left",
        sortable: true,
        field: row => row.occurrence,
        format: val => `${val}`,
    },
]

export default {
    name: "Reports",
    props: ['endpoint', 'reportTypeOptions', 'reportOccurrenceOptions'],
    components: { DeleteReport },

    setup(props) {
        const $q = useQuasar();

        const rows = ref([])
        const selected = ref([])
        let actionBtnDisabled = ref(true)

        function getReports() {
            $q.loading.show()
            axios
                .get(`/bitdefender/reports/`)
                .then(r => {
                    console.log(r.data)
                    rows.value = []
                    for (let report of r.data.result.items) {
                        const reportTypeObj = props.reportTypeOptions.find(o => o.value === report.type);
                        const occurrenceObj = props.reportOccurrenceOptions.find(o => o.value === report.occurrence)

                        let reportObj = {
                            id: report.id,
                            name: report.name,
                            type: reportTypeObj != undefined ? reportTypeObj.label : "N/A",
                            occurrence: occurrenceObj != undefined ? occurrenceObj.label : "N/A"
                        }
                        rows.value.push(reportObj)
                    }
                    $q.loading.hide()
                })
                .catch(e => {
                    console.log(e)
                });
        }

        function deleteReport() {
            $q.dialog({
                component: DeleteReport,
                componentProps: {
                    selected: selected.value,
                    endpoint: props.endpoint
                }
            }).onOk(() => {
                getReports()
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
            deleteReport,
        };
    },
};

</script>