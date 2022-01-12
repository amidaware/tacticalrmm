<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
        <q-card class="q-dialog-plugin" style="min-width: 60vw">
            <q-bar>
                <span>
                    Packages
                </span>
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <div class="q-pa-sm">
                    <q-table :rows="rows" :columns="columns" row-key="installLinkWindows" :pagination="pagination"
                        :filter="filter" flat>
                        <template v-slot:top-left>
                            <q-btn flat dense @click="getInstallLinks()" icon="refresh" />
                        </template>
                        <template v-slot:top-right>
                            <q-input outlined v-model="filter" label="Search" dense debounce="300" clearable>
                                <template v-slot:prepend>
                                    <q-icon name="search" />
                                </template>
                            </q-input>
                        </template>
                        <template v-slot:body="props">
                            <q-tr :props="props">
                                <q-td key="companyName" :props="props">
                                    {{ props.row.companyName }}
                                </q-td>
                                <q-td key="packageName" :props="props">
                                    {{ props.row.packageName }}
                                </q-td>
                                <q-td key="installLinkWindows" :props="props">
                                    <q-btn flat icon="content_copy"
                                        @click="copyInstallLink(props.row.installLinkWindows)" />
                                </q-td>
                                <q-td key="installLinkLinux" :props="props">
                                    <q-btn flat icon="content_copy"
                                        @click="copyInstallLink(props.row.installLinkLinux)" />
                                </q-td>
                                <q-td key="installLinkMacDownloader" :props="props">
                                    <q-btn flat icon="content_copy"
                                        @click="copyInstallLink(props.row.installLinkMacDownloader)" />
                                </q-td>
                            </q-tr>
                        </template>
                    </q-table>
                </div>
            </q-card-section>
        </q-card>
    </q-dialog>
</template>

<script>
    import axios from "axios";
    // composable imports
    import { ref, computed, onMounted } from "vue";
    import { useQuasar, useDialogPluginComponent, copyToClipboard } from "quasar";
    import { notifySuccess, notifyError } from "@/utils/notify";
    const columns = [
        {
            name: "companyName",
            required: true,
            label: "Company",
            align: "left",
            sortable: true,
            field: row => row.companyName,
            format: val => `${val}`,
        },
        {
            name: "packageName",
            required: true,
            label: "Name",
            align: "left",
            sortable: true,
            field: row => row.packageName,
            format: val => `${val}`,
        },
        {
            name: "installLinkWindows",
            required: true,
            label: "Windows",
            align: "left",
            sortable: true,
            field: row => row.installLinkWindows,
            format: val => `${val}`,
        },
        {
            name: "installLinkLinux",
            required: true,
            label: "Linux",
            align: "left",
            sortable: true,
            field: row => row.installLinkLinux,
            format: val => `${val}`,
        },
        {
            name: "installLinkMacDownloader",
            required: true,
            label: "MAC Downloader",
            align: "left",
            sortable: true,
            field: row => row.installLinkMacDownloader,
            format: val => `${val}`,
        },
    ]
    export default {
        name: "Packages",
        emits: [...useDialogPluginComponent.emits],
        props: ['endpoint'],
        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const packages = ref([])
            const rows = ref([])

            function getInstallLinks() {
                rows.value = []
                $q.loading.show()
                axios
                    .get(`/bitdefender/packages/`)
                    .then(r => {
                        for (let obj of r.data.result) {
                            let packageObj = {
                                companyName: obj.companyName,
                                packageName: obj.packageName,
                                installLinkLinux: obj.installLinkLinux,
                                installLinkMacDownloader: obj.installLinkMacDownloader,
                                installLinkWindows: obj.installLinkWindows
                            }
                            rows.value.push(packageObj)
                        }
                        packages.value = r.data
                        $q.loading.hide()
                    })
                    .catch(e => {
                        console.log(e)
                    });
            }

            function copyInstallLink(downloadLink) {
                copyToClipboard(downloadLink)
                    .then(() => {
                        notifySuccess("Download link copied to clipboard!");
                    })
                    .catch(() => {
                        notifyError("Unable to copy to clipboard!");
                    });
            }

            onMounted(() => {
                getInstallLinks()
            });

            return {
                pagination: {
                    sortBy: 'name',
                    descending: false,
                    page: 1,
                    rowsPerPage: 50
                },
                packages,
                rows,
                columns,
                filter: ref(""),
                getInstallLinks,
                copyInstallLink,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };

</script>