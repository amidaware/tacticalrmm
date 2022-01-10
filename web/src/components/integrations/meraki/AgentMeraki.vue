<template>
  <div class="q-pa-md">
    <q-card>
      <q-table :rows="rows" :columns="columns" row-key="id" />
    </q-card>
  </div>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { ref, computed, onMounted } from "vue";
  import { useMeta, useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";
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
              console.log(obj)
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
              user: resolvedMerakiClients[i].data.records[0].user
            }
            rows.value.push(clientObj)
          }
        }
        if(rows.value.length < 1){
           notifyError('Did not find any associated MAC addresses in your Cisco Meraki organization')
        }
        $q.loading.hide()
      }
      
      onMounted(() => {
        getOrganizations();
      });

      return {
        splitterModel: ref(17),
        organizations,
        tab,
        columns,
        rows,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };
</script>