<template>
    <div>
        <q-splitter v-model="splitterModel">
            <template v-slot:before>
                <q-tabs v-model="integrationTab" vertical dense class="text-primary"
                    v-for="integration in integrations">
                    <q-tab :name="integration.name" :label="integration.name" />
                </q-tabs>
            </template>
            <template v-slot:after>
                <q-card-section class="row items-center q-py-none">
                    <div class="text-h6">{{ agent.hostname }} Integrations</div>
                </q-card-section>
                <q-tab-panels v-model="integrationTab" animated swipeable vertical transition-prev="jump-up"
                    transition-next="jump-up">
                    <q-tab-panel class="q-px-none" name="Bitdefender GravityZone">
                        <Bitdefender :agent="agent" />
                    </q-tab-panel>
                    <q-tab-panel class="q-px-none" name="Cisco Meraki">
                        <AgentMeraki :agent="agent" />
                    </q-tab-panel>
                    <q-tab-panel class="q-px-none" name="Snipe-IT">
                        <SnipeIT :agent="agent" />
                    </q-tab-panel>
                </q-tab-panels>
            </template>
        </q-splitter>
    </div>
</template>

<script>
    import axios from "axios";
    import { useRoute } from 'vue-router';
    import { ref, computed, watch, onMounted } from "vue";
    import { useQuasar, useDialogPluginComponent, date, useMeta } from "quasar";
    import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";
    import Bitdefender from "@/components/integrations/bitdefender/Bitdefender";
    import SnipeIT from "@/components/integrations/snipeit/SnipeIT";
    import AgentMeraki from "@/components/integrations/meraki/AgentMeraki";

    export default {
        name: "AgentIntegrations",
        emits: [...useDialogPluginComponent.emits],
        components: { Bitdefender, SnipeIT, AgentMeraki },

        setup(props) {
            const { dialogRef, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();
            const route = useRoute()
            const agent = ref([])
            const integrations = ref([])
            const integrationTab = ref("")

            function getAgent() {
                useMeta({ title: `Agent Integrations Dashboard` });
                axios
                    .get("agents/" + route.params.agent_id + "/")
                    .then(r => {
                        agent.value = r.data
                    })
                    .catch((e) => {
                        console.log(e)
                    });
            }

            function getIntegrations() {
                axios
                    .get("/integrations/")
                    .then(r => {
                        for (let integrationObj of r.data) {
                            if (integrationObj.enabled) {
                                integrations.value.push(integrationObj)
                            }
                        }
                        if (integrations.value.length < 1) {
                            notifyWarning('No Agent Integrations configured. Go to Settings > Integrations Manager')
                        }
                    })
                    .catch((e) => {
                        console.log(e)
                    });
            }

            watch(integrationTab, (selection, prevSelection) => {
                if (selection === 'Bitdefender GravityZone') {
                    integrationTab.value = 'Bitdefender GravityZone'

                } else if (selection === 'Cisco Meraki') {
                    integrationTab.value = 'Cisco Meraki'

                } else if (selection === 'Snipe-IT') {
                    integrationTab.value = 'Snipe-IT'
                }
            })

            onMounted(() => {
                getAgent();
                getIntegrations()
            });
            
            return {
                splitterModel: ref(15),
                integrationTab,
                agent,
                integrations,
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