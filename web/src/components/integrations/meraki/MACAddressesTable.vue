<template>
    <div class="q-pa-md">
        <q-table :rows="rows" :columns="columns" row-key="id" selection="single" v-model:selected="selected"
            :filter="filter">
            <template v-slot:top-left>
                <q-btn flat dense @click="getOrganizations()" icon="refresh" />
                <q-btn-dropdown label="Actions" flat :disable="actionBtnDisabled">
                    <q-list>
                        <q-item clickable v-close-popup @click="getDevicePolicy()">
                            <q-item-section>
                                <q-item-label>Device Policy</q-item-label>
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
    </div>
</template>

<script>
    import axios from "axios";
    // composable imports
    import { ref, computed, onMounted, watch } from "vue";
    import { useMeta, useQuasar, useDialogPluginComponent, date } from "quasar";
    import { notifySuccess, notifyError } from "@/utils/notify";
    import Policy from "@/components/integrations/meraki/modals/Policy";

    const columns = [
        {
            name: "id",
            label: "ID",
            align: "left",
            field: (row) => row.id,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "mac",
            label: "MAC",
            align: "left",
            field: (row) => row.mac,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
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
            name: "description",
            align: "left",
            label: "Description",
            field: "description",
            field: (row) => row.description,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "ip",
            align: "left",
            label: "IP",
            field: "ip",
            field: (row) => row.ip,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "status",
            align: "left",
            label: "Status",
            field: "status",
            field: (row) => row.status,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "firstSeen",
            align: "left",
            label: "First Seen",
            field: "firstSeen",
            field: (row) => row.firstSeen,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "lastSeen",
            align: "left",
            label: "Last Seen",
            field: "lastSeen",
            field: (row) => row.lastSeen,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
        {
            name: "user",
            align: "left",
            label: "User",
            field: "user",
            field: (row) => row.user,
            format: (val) => `${val}`,
            sortable: true,
            required: true,
        },
    ]

    export default {
        name: "MACAddressesTable",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent', 'rows'],

        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const tab = ref("")
            const clients = ref([])
            const rows = props.rows
            const selected = ref([])
            let actionBtnDisabled = ref(true)

            function getDevicePolicy() {
                $q.dialog({
                    component: Policy,
                    componentProps: {
                        selected: selected,
                        agent: props.agent
                    }
                })
            }

            watch(selected, (val) => {
                if (val.length > 0) {

                    actionBtnDisabled.value = false
                } else {
                    actionBtnDisabled.value = true
                }
            })

            return {
                splitterModel: ref(17),
                tab,
                columns,
                rows,
                selected,
                filter: ref(""),
                actionBtnDisabled,
                getDevicePolicy,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };
</script>