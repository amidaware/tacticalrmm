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
                <div class="text-h6">{{ agent.hostname }}</div>
            </q-card-section>
            <q-tab-panels
                v-model="integrationTab"
                animated
                swipeable
                vertical
                transition-prev="jump-up"
                transition-next="jump-up"
            >
                <q-tab-panel class="q-px-none" name="Bitdefender GravityZone">
                    <Bitdefender :agent="agent" />
                </q-tab-panel>
                <q-tab-panel class="q-px-none" name="Snipe-IT">
                    <SnipeIT :agent="agent" />
                </q-tab-panel>
            </q-tab-panels>
        </template>
    </q-splitter>
</template>

<script>
import axios from "axios";
import { useRoute } from 'vue-router';
import { ref, onMounted, watch } from "vue";
import { useMeta } from "quasar";
import { notifyWarning } from "@/utils/notify";
import Bitdefender from "@/components/integrations/bitdefender/Bitdefender";
import SnipeIT from "@/components/integrations/snipeit/SnipeIT";

export default {
    name: "AgentIntegrations",
    components: { Bitdefender, SnipeIT },

    setup(props) {
        const { params } = useRoute();
        const agent = ref([])
        const integrations = ref([])
        const integration = ref("")
        const integrationTab = ref("")

        function getAgent() {
            axios
                .get("agents/" + params.agent_id + "/")
                .then(r => {
                    agent.value = r.data
                    // useMeta({title: agent.value.hostname + ` Integrations Dashboard`})
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
                        if (integrationObj.enabled && integrationObj.agent_related) {
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

        watch(integrationTab, (selection) => {
            if (selection === 'Bitdefender GravityZone') {
                integrationTab.value = 'Bitdefender GravityZone'

            } else if (selection === 'Snipe-IT') {
                integrationTab.value = 'Snipe-IT'
            }
        })

        useMeta(() => {
            return {
                title: agent.value.hostname + ` | Agent Integrations Dashboard`
            }
        })

        onMounted(() => {
            getIntegrations()
            getAgent()
        });

        return {
            splitterModel: ref(15),
            integrationTab,
            agent,
            integration,
            integrations,
        };
    },
};
</script>

<style>
body {
    overflow: scroll;
}
</style>