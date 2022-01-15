<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistent>
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Associate Meraki Organization
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <q-select filled v-model="organization" label="Organization *" :options="organizationOptions" dense
                    :rules="[(val) => !!val || '*Required']" />
            </q-card-section>

            <q-card-actions align="right">
                <q-btn class="q-mb-md" label="Save" @click="onOKClick()" />
            </q-card-actions>

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
        name: "AssociateOrg",
        emits: [...useDialogPluginComponent.emits],
        props: [],
        setup(props) {
            const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const organization = ref("")
            const organizationOptions = ref([])


            function getOrganizations() {
                $q.loading.show({ message: 'Getting Cisco Meraki organizations...' })
                axios
                    .get(`/meraki/organizations/`)
                    .then(r => {
                        for (let org of r.data) {
                            let orgObj = {
                                label: org.name,
                                value: org.id,
                            }
                            organizationOptions.value.push(orgObj)
                        }
                        $q.loading.hide()

                    })
                    .catch(e => { });
            }
            function onOKClick() {
                onDialogOK({
                    "organization": organization.value
                })
            }

            onMounted(() => {

                getOrganizations()
            });

            return {
                organization,
                organizationOptions,
                onOKClick,
                // quasar dialog plugin
                dialogRef,
                onDialogHide,
            };
        },
    };

</script>