<template>
    <q-splitter v-model="splitterModel">
        <template v-slot:before>
            <q-tabs v-model="integrationTab" vertical dense class="text-primary" v-for="integration in integrations">
                <q-tab :name="integration.name" :label="integration.name" />
            </q-tabs>
        </template>
        <template v-slot:after>
            <q-card-section class="row items-center q-py-none">
                <div class="text-h6">{{node.name}} Integrations</div>
            </q-card-section>
            <q-tab-panels v-model="integrationTab" animated swipeable vertical transition-prev="jump-up"
                transition-next="jump-up">
                <q-tab-panel class="q-px-none" name="Cisco Meraki">
                   <ClientMeraki :node="node" :integrations="integrations"/>
                </q-tab-panel>
            </q-tab-panels>
        </template>
    </q-splitter>
</template>

<script>
    import axios from "axios";
    import { useRoute } from 'vue-router';
    import { ref, computed, watch, onMounted } from "vue";
    import { useQuasar, useDialogPluginComponent, date, useMeta } from "quasar";
    import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";
    import ClientMeraki from "@/components/integrations/meraki/ClientMeraki";

    export default {
        name: "ClientIntegrations",
        emits: [...useDialogPluginComponent.emits],
        components: { ClientMeraki },

        setup(props) {
            const { dialogRef, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();
            const route = useRoute()

            const integrationTab = ref("")
            const node = ref([])
            const integrations = ref([])
            const organization = ref("")
            const orgChoice = ref(false)

            function getIntegrations() {
                useMeta({ title: `Client Integrations Dashboard` });
                axios
                    .get("integrations/")
                    .then(r => {
                        for (let integrationObj of r.data) {
                            if (integrationObj.enabled && integrationObj.client_org_related) {
                                integrations.value.push(integrationObj)
                            }
                        }
                        if (integrations.value.length < 1) {
                            notifyWarning('No Client Integrations configured. Go to Settings > Integrations Manager')
                        }
                    })
                    .catch((e) => {
                        console.log(e)
                    })
            }

            function getClient() {
                axios
                    .get("clients/" + route.params.client_id + "/")
                    .then(r => {
                        node.value = r.data
                    })
                    .catch((e) => {
                        console.log(e)

                    })
            }

            watch(integrationTab, (selection, prevSelection) => {
                if (selection === 'Cisco Meraki') {
                    integrationTab.value = 'Cisco Meraki'
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
                orgChoice,
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