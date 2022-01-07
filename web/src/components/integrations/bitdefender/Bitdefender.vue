<template>
      <q-card flat>
        <q-tabs
          v-model="tab"
          dense
          align="left"
          class="text-grey"
          active-color="primary"
          indicator-color="primary"
          no-caps
          narrow-indicator
          inline-label
        >
          <q-tab icon="computer" name="endpoint" label="Endpoint" />
          <q-tab icon="summarize" name="reports" label="Reports" />
          <q-tab icon="local_police" name="quarantine" label="Quarantine" />
        </q-tabs>
        <q-tab-panels v-model="tab" animated>
          <q-tab-panel name="endpoint">
            <div class="text-h6">Mails</div>
            Lorem ipsum dolor sit amet consectetur adipisicing elit.
          </q-tab-panel>

          <q-tab-panel name="reports">
            <div class="text-h6">Alarms</div>
            Lorem ipsum dolor sit amet consectetur adipisicing elit.
          </q-tab-panel>

          <q-tab-panel name="quarantine">
            <div class="text-h6">Movies</div>
            Lorem ipsum dolor sit amet consectetur adipisicing elit.
          </q-tab-panel>
        </q-tab-panels>
      </q-card>
</template>

<script>
    import axios from "axios";
    import { ref, computed, watch, onMounted } from "vue";
    import { useQuasar, useDialogPluginComponent, date } from "quasar";
    import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";
    import ScanEndpoint from "@/components/integrations/bitdefender/ScanEndpointConfirm";

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
            name: "ip",
            required: true,
            label: "IP",
            align: "left",
            sortable: true,

        },
        {
            name: "threatName",
            required: true,
            label: "Threat",
            align: "left",
            sortable: true,

        },

        {
            name: "quarantinedOn",
            required: true,
            label: "Quarantined On",
            align: "left",
            sortable: true,

        },
        {
            name: "canBeRemoved",
            required: true,
            label: "Can Be Removed",
            align: "left",
            sortable: true,

        },
        {
            name: "canBeRestored",
            required: true,
            label: "Can Be Restored",
            align: "left",
            sortable: true,

        },
        {
            name: "details",
            required: true,
            label: "Details",
            align: "left",
            sortable: true,

        }
    ]

    export default {
        name: "Bitdefender",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent'],
        
        setup(props) {
            const { dialogRef, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const tab = ref("")
            const tacticalAgentMacs = ref([])
            const bitdefenderEndpoints = ref([])

            function getTacticalAgentMacs(){
                axios
                    .get("agents/" + props.agent.agent_id + "/")
                    .then(r => {
                        for (let adapters of r.data.wmi_detail.network_adapter) {
                            for (let adapter of adapters) {
                                let macStr = String(adapter.MACAddress)
                                let macs = macStr.replaceAll(":", "").toLowerCase()
                                tacticalAgentMacs.value.push(macs)
                            }
                        }
                        getBitdefenderEndpoints()
                    })
                    .catch((e) => {
                        console.log(e)
                    });
            }

            async function getBitdefenderEndpoints(){
                const r = await axios.get(`/bitdefender/endpoints/`, { params: { pageNumber: 1 } });
                const bitdefenderEndpointsArray = [];
                
                for (let i = 0; i < r.data.result.pagesCount; i++) {
                    let nextPage = i + 1
                    bitdefenderEndpointsArray.push(axios.get(`/bitdefender/endpoints/`, { params: { pageNumber: nextPage } }));
                };

                let resolvedbitdefenderEndpoints = await Promise.all(bitdefenderEndpointsArray)
                for (let i = 0; i < resolvedbitdefenderEndpoints.length; i++) {
                    bitdefenderEndpoints.value.push(...resolvedbitdefenderEndpoints[i].data.result.items)
                }
                console.log(bitdefenderEndpoints.value)
            }

            onMounted(() => {
                getTacticalAgentMacs()
            });

            return {
                tab,
                quarantinePagination: {
                    sortBy: 'quarantinedOn',
                    descending: false,
                    page: 1,
                    rowsPerPage: 100
                },
                // rows,
                // columns,
                filter: ref(""),
                // quasar dialog
                dialogRef,
                onDialogHide,
            };
        },
    };

</script>