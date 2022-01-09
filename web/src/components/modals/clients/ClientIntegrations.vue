<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
        <q-layout view="hHh Lpr lff" container class="shadow-2 rounded-borders q-dialog-plugin" style="width: 90vw; max-width: 90vw">
            <q-page-container class="bg-white">
                <q-page>
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
                            <q-card-section class="row items-center q-pb-none">
                                <div class="text-h6">{{ node.label }} Integrations</div>
                                <q-space />
                                <q-btn icon="close" flat round dense v-close-popup />
                            </q-card-section>
                            <q-tab-panels
                            v-model="integrationTab"
                            animated
                            swipeable
                            vertical
                            transition-prev="jump-up"
                            transition-next="jump-up"
                            >

                            <q-tab-panel  class="q-px-none" name="Cisco Meraki">
                                <Meraki :node="node" />
                            </q-tab-panel>

                            </q-tab-panels>
                        </template>
                    </q-splitter>
                </q-page>
            </q-page-container>
        </q-layout>
    </q-dialog>
</template>
<script>
    import axios from "axios";
    import { ref, computed, watch, onMounted } from "vue";
    import { useQuasar, useDialogPluginComponent, date } from "quasar";
    import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";
    import Meraki from "@/components/integrations/meraki/Meraki";

    export default {
        name: "ClientIntegrations",
        emits: [...useDialogPluginComponent.emits],
        components: {Meraki},
        props: ['node', 'integrations'],

        setup(props) {
            const { dialogRef, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const integrationTab = ref("")

            watch(integrationTab, (selection, prevSelection) => {
                if (selection === 'Cisco Meraki') {
                    integrationTab.value = 'Cisco Meraki'
                }
            })

            return {
                splitterModel: ref(15),
                integrationTab,
                // quasar dialog
                dialogRef,
                onDialogHide,
            };
        },
    };



</script>