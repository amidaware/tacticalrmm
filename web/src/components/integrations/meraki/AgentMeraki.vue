<template>

  <div class="q-pa-md">
  <q-btn-dropdown label="Actions" flat :disable="actionBtnDisabled">
      <q-list>
          <q-item clickable v-close-popup @click="getDevicePolicy()">
              <q-item-section>
                  <q-item-label>Device Policy</q-item-label>
              </q-item-section>
          </q-item>

      </q-list>
  </q-btn-dropdown>
    <q-card>
      <q-table :rows="rows" :columns="columns" row-key="id"
      :selected-rows-label="getSelectedString"
      selection="single"
      v-model:selected="selected" />
    </q-card>
  </div>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { ref, computed, onMounted, watch } from "vue";
  import { useMeta, useQuasar, useDialogPluginComponent, date } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";
  
  import Policy from "@/components/integrations/meraki/modals/Policy";


  const columns = [
    {
      name: "id",
      label: "ID",
      align: "left",
      field: (row) => row.id,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "mac",
      label: "MAC",
      align: "left",
      field: (row) => row.mac,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "manufacturer",
      label: "Manufacturer",
      align: "left",
      field: (row) => row.manufacturer,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "description",
      align: "left",
      label: "Description",
      field: "description",
      field: (row) => row.description,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "ip",
      align: "left",
      label: "IP",
      field: "ip",
      field: (row) => row.ip,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "status",
      align: "left",
      label: "Status",
      field: "status",
      field: (row) => row.status,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "firstSeen",
      align: "left",
      label: "First Seen",
      field: "firstSeen",
      field: (row) => row.firstSeen,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "lastSeen",
      align: "left",
      label: "Last Seen",
      field: "lastSeen",
      field: (row) => row.lastSeen,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "user",
      align: "left",
      label: "User",
      field: "user",
      field: (row) => row.user,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
  ]
  export default {
    name: "AgentMeraki",
    emits: [...useDialogPluginComponent.emits],
    props: ['agent'],
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
        $q.loading.show({message: 'Getting organization...'})
        axios
          .get(`/meraki/organizations/`)
          .then(r => {
            organizations.value = r.data;
            $q.loading.show({
              message: 'Searching ' + organizations.value[0].name + ' for any ' + props.agent.hostname +' associated MAC addresses... This may take a few minutes.'
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
            if(obj.MACAddress && obj.NetEnabled){
              const macStr = String(obj.MACAddress)
              const macs = macStr.replaceAll(":", "").toLowerCase()
              tacticalAgentMacs.value.push(macs)
            }

          }
        }

        for (let i = 0; i < tacticalAgentMacs.value.length; i++) {
          if (tacticalAgentMacs.value[i]) {
            merakiClientsArray.push(await axios.get(`/meraki/` + organizations.value[0].id + `/client/` + tacticalAgentMacs.value[i] + `/`).catch(e => { $q.loading.hide()}))
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
        }

        if(rows.value.length < 1){
           notifyError('Could not find any associated ' + props.agent.hostname + ' MAC addresses')
        }
        $q.loading.hide()
      }

      function getDevicePolicy(){
            $q.dialog({
              component: Policy,
              componentProps: {
                  selected: selected,
                  agent: props.agent
              }
          })
      }

      watch(selected, (val) =>{
        if (selected.value.length > 0){
          actionBtnDisabled.value = false
        }else{
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
        columns,
        rows,
        selected,
        getSelectedString () {
            return selected.value.length === 0 ? '' : `${selected.value.length} record${selected.value.length > 1 ? 's' : ''} selected of ${rows.value.length}`
        },
        actionBtnDisabled,
        getDevicePolicy,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };
</script>