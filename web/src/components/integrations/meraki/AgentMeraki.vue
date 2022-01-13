<template>
    <q-card flat>
        <q-tabs v-model="tab" dense align="left" class="text-grey" active-color="primary" indicator-color="primary"
            no-caps narrow-indicator inline-label>
            <q-tab icon="computer" name="client" label="Client" />
            <q-tab icon="settings_ethernet" name="macAddresses" label="MAC Addresses"/>
        </q-tabs>
        <q-tab-panels v-model="tab" animated>
            <q-tab-panel name="client" class="q-px-none">
                <div class="row">
                    <div class="col-5">
                        <q-list>
                            <q-item-section>
                                <q-item-label header>GENERAL </q-item-label>
                            </q-item-section>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Name</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>ID</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Policy</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Last Seen</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                </q-item-section>
                            </q-item>
                            <q-separator inset />
                            <q-item-label header>AGENT</q-item-label>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Product Version</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Engine Version</q-item-label>
                                </q-item-section>
                                <q-item-section side top>

                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Last Update</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Malware Detected</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Infected</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-separator inset />
                        </q-list>
                    </div>
                    <div class="col-7">
                        <div class="row q-mt-sm">
                            <div class="col-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-h6">Risk Score</span>
fdsa
                                    </q-card-section>
                                </q-card>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Misconfigurations</span>
                                        <div class="text-h6">
                                        safd
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">App Vulnerabilities</span>
                                        <div class="text-h6">
                                        fdsa
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Human Risks</span>
                                        <div class="text-h6">
                                        fdsa
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                        </div>
                    </div>
                </div>
            </q-tab-panel>
            <q-tab-panel name="macAddresses" class="q-px-none">
                <MACAddressesTable 
                :agent="agent"
                :rows="rows"/>
            </q-tab-panel>
        </q-tab-panels>
    </q-card>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { ref, computed, onMounted, watch } from "vue";
  import { useMeta, useQuasar, useDialogPluginComponent, date } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";
  import MACAddressesTable from "@/components/integrations/meraki/MACAddressesTable";
  
  export default {
    name: "AgentMeraki",
    emits: [...useDialogPluginComponent.emits],
    props: ['agent'],
    components: {MACAddressesTable},

    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();

      const organizations = ref([]);
      const tacticalAgentMacs = ref([])
      const tab = ref("")
      const rows = ref([])
      const clients = ref([])
      const selected = ref([])
      let actionBtnDisabled = ref(true)

      function getOrganizations() {
        $q.loading.show({ message: 'Getting organization...' })
        axios
          .get(`/meraki/organizations/`)
          .then(r => {
            organizations.value = r.data;
            $q.loading.show({
              message: 'Searching ' + organizations.value[0].name + ' for any ' + props.agent.hostname + ' associated MAC addresses... This may take a few minutes.'
            })

            if (r.data.errors) {
              notifyError(r.data.errors[0])
            }
            getClient()
          })
          .catch(e => { });
      }

      async function getClient() {
        const merakiClientsArray = []
        for (let i = 0; i < props.agent.wmi_detail.network_adapter.length; i++) {
          for (let obj of props.agent.wmi_detail.network_adapter[i]) {
            if (obj.MACAddress && obj.NetEnabled) {
              const macStr = String(obj.MACAddress)
              const rows = macStr.replaceAll(":", "").toLowerCase()
              tacticalAgentMacs.value.push(rows)
            }

          }
        }

        for (let i = 0; i < tacticalAgentMacs.value.length; i++) {
          if (tacticalAgentMacs.value[i]) {
            merakiClientsArray.push(await axios.get(`/meraki/` + organizations.value[0].id + `/client/` + tacticalAgentMacs.value[i] + `/`).catch(e => { $q.loading.hide() }))
          }
        }

        let resolvedMerakiClients = await Promise.all(merakiClientsArray)
        for (let i = 0; i < clients.value.length; i++) {
          clients.value.push(...resolvedMerakiClients[i].data.result.items)
        }

        for (let i = 0; i < resolvedMerakiClients.length; i++) {
          if (resolvedMerakiClients[i].data) {
            let clientObj = {
              id: resolvedMerakiClients[i].data.clientId,
              mac: resolvedMerakiClients[i].data.mac,
              manufacturer: resolvedMerakiClients[i].data.manufacturer,
              description: resolvedMerakiClients[i].data.records[0].description,
              ip: resolvedMerakiClients[i].data.records[0].ip,
              status: resolvedMerakiClients[i].data.records[0].status,
              firstSeen: date.formatDate(resolvedMerakiClients[i].data.records[0].firstSeen, 'ddd, MMM D, YYYY @ hh:mm A'),
              lastSeen: date.formatDate(resolvedMerakiClients[i].data.records[0].lastSeen, 'ddd, MMM D, YYYY @ hh:mm A'),
              user: resolvedMerakiClients[i].data.records[0].user,
              networkId: resolvedMerakiClients[i].data.records[0].network.id,
              networkName: resolvedMerakiClients[i].data.records[0].network.name
            }
            rows.value.push(clientObj)
          }
          tab.value = 'client'
        }

        if (rows.value.length < 1) {
          notifyError('Could not find any associated ' + props.agent.hostname + ' MAC addresses')
        }
        $q.loading.hide()
      }

      // function getMACAddresses() {
      //   $q.dialog({
      //     component: MACAddressesTable,
      //     componentProps: {
      //       agent: props.agent
      //     }
      //   })
      // }

      watch(selected, (val) => {
        if (selected.value.length > 0) {
          actionBtnDisabled.value = false
        } else {
          actionBtnDisabled.value = true
        }
      })

      onMounted(() => {
        getOrganizations();
      });

      return {
        splitterModel: ref(17),
        organizations,
        tab,
        rows,
        getOrganizations,
        // getMACAddresses,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };
</script>