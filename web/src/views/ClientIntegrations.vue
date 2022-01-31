<template>
    <q-splitter v-model="splitterModel">
        <template v-slot:before>
            <q-tabs
                v-model="integrationTab"
                vertical
                dense
                class="text-primary"
                v-for="integration in integrations"
            >
                <q-tab :name="integration.name" :label="integration.name" />
            </q-tabs>
        </template>
        <template v-slot:after>
            <q-card-section class="row items-center q-py-none">
                <div class="text-h6">{{ node.name }}</div>
            </q-card-section>
            <q-tab-panels
                v-model="integrationTab"
                animated
                swipeable
                vertical
                transition-prev="jump-up"
                transition-next="jump-up"
            >
                <q-tab-panel class="q-px-none" name="Cisco Meraki">
                    <Meraki :node="node" :integrations="integrations" />
                </q-tab-panel>
            </q-tab-panels>
        </template>
    </q-splitter>
</template>

<script>
import axios from "axios";
import { useRoute } from 'vue-router';
import { ref, watch, onMounted } from "vue";
import { useDialogPluginComponent, useMeta } from "quasar";
import { notifyWarning } from "@/utils/notify";
import Meraki from "@/components/integrations/meraki/Meraki";

export default {
    name: "ClientIntegrations",
    components: { Meraki },

    setup(props) {
        const { dialogRef, onDialogHide } = useDialogPluginComponent();
        const { params } = useRoute();

        const integrationTab = ref("")
        const node = ref([])
        const integrations = ref([])

        function getIntegrations() {
            axios
                .get("integrations/")
                .then(r => {
                    for (let integrationObj of r.data) {
                        if (integrationObj.enabled && integrationObj.client_related) {
                            integrations.value.push(integrationObj)
                        }
                    }
                    if (integrations.value.length < 1) {
                        notifyWarning('No Client Integrations configured. Go to Settings > Integrations Manager')
                    }
                })
                .catch((e) => {
                    console.log(e.response.data)
                })
        }

        function getClient() {
            axios
                .get("clients/" + params.client_id + "/")
                .then(r => {
                    node.value = r.data
                })
                .catch((e) => {
                    console.log(e)

                })
        }

        watch(integrationTab, (selection) => {
            if (selection === 'Cisco Meraki') {
                integrationTab.value = 'Cisco Meraki'
            }
        })

        useMeta(() => {
            return {
                title: node.value.name + ` | Client Integrations Dashboard`
            }
        })

        onMounted(() => {
            getIntegrations()
            getClient();
        });

        return {
            splitterModel: ref(15),
            integrationTab,
            integrations,
            node,
            // quasar dialog
            dialogRef,
            onDialogHide,
        };
    },
};
</script>

<style>
body {
    overflow: scroll;
}
</style>