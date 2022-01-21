<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Remove Meraki Association
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section class="row items-center">
                <div>
                    Are you sure you want to remove the association of the Meraki organization:
                    <span
                        class="text-weight-bold"
                    >{{ organization.name }}</span>, from
                    <span class="text-weight-bold">{{ client.name }}</span>?
                </div>
            </q-card-section>
            <q-card-actions align="right">
                <q-btn label="Cancel" v-close-popup />
                <q-btn label="Confirm" v-close-popup @click="removeOrgAssociation()" />
            </q-card-actions>
        </q-card>
    </q-dialog>
</template>

<script>
import axios from "axios";
// composable imports
import { ref } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { notifySuccess, notifyError } from "@/utils/notify";

export default {
    name: "RemoveOrgAssociation",
    emits: [...useDialogPluginComponent.emits],
    props: ['integrations', 'organization', 'client'],

    setup(props) {
        const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
        const $q = useQuasar();

        const integration = ref(null)

        function removeOrgAssociation() {
            let obj = null
            for (let i = 0; i < props.integrations.length; i++) {
                obj = props.integrations[i].configuration.backend.associations.clients.find(o => o.client_id === props.client.id);
                integration.value = props.integrations[i]
                if (obj && integration.value) {
                    break;
                }
            }

            if (obj) {
                axios
                    .delete(`/integrations/` + integration.value.id + `/associate_client/`, { data: { client: props.client } })
                    .then(r => {
                        onDialogOK()
                    })
                    .catch(e => {
                        console.log(e.response.data)
                    });
            } else {
                notifySuccess('There is no Cisco Meraki association found')
            }

        }

        return {
            removeOrgAssociation,
            // quasar dialog plugin
            dialogRef,
            onDialogHide,
        }
    }
}
</script>