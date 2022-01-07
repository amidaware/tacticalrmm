<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-layout view="hHh Lpr lff" container class="shadow-2 rounded-borders q-dialog-plugin"
      style="width: 90vw; max-width: 90vw">
      <q-header class="bg-grey-3 text-black">
        <q-bar>
          <q-btn ref="refresh" @click="getIntegrations()" class="q-mr-sm" dense flat push icon="refresh" />Integrations
          Manager
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
      </q-header>
      <q-page-container class="bg-white">
        <q-page>
          <div class="q-pa-md">
            <q-table :rows="rows" :columns="columns" row-key="name" :filter="filter" grid hide-header
              :pagination="pagination">
              <template v-slot:top-right>
                <q-input outlined v-model="filter" label="Search" dense debounce="300" clearable>
                  <template v-slot:prepend>
                    <q-icon name="search" />
                  </template>
                </q-input>
              </template>
              <template v-slot:item="props">
                <div class="q-pa-xs col-xs-12 col-sm-6 col-md-4 col-lg-3 grid-style-transition">
                  <q-card class="bg-grey-1">
                    <q-card-section>
                      <div class="text-h6">{{props.row.name}}</div>
                    </q-card-section>
                    <q-card-section class="q-pt-none">
                      {{props.row.description}}
                    </q-card-section>
                    <div class="vertical-bottom">
                      <q-card-actions align="left">
                        <q-btn label="View Config" class="q-ml-sm"
                          @click="viewIntegrationConfig(props.row.id, props.row.name, props.row.integration)"></q-btn>
                      </q-card-actions>
                    </div>
                    <q-separator v-if="props.row.enabled" />
                    <q-card-section>
                      <q-chip color="positive" text-color="white" icon="check_circle_outline" v-if="props.row.enabled"
                        outline>
                        Enabled
                      </q-chip>
                    </q-card-section>
                  </q-card>
                </div>
              </template>
            </q-table>
          </div>
        </q-page>
      </q-page-container>
    </q-layout>
  </q-dialog>
</template>

<script>
  import axios from "axios";
  import { ref, computed, watch, onMounted } from "vue";
  import { useQuasar, useDialogPluginComponent, exportFile } from "quasar";
  import IntegrationConfigModal from "@/components/integrations/modals/IntegrationConfigModal";
  import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";
  import { useRouter } from 'vue-router';

  export default {
    name: "IntegrationsManager",
    emits: [...useDialogPluginComponent.emits],
    setup() {
      const { dialogRef, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();
      const router = useRouter()
      let enabled = ref("")
      let rows = ref([])

      const columns = [
        {
          name: 'desc',
          required: true,
          label: 'Name',
          align: 'left',
          field: row => row.name,
          format: val => `${val}`,
          sortable: true
        },
      ]

      function getIntegrations() {
        axios
          .get(`/integrations/`)
          .then(r => {
            rows.value = []
            for (let integration of r.data) {
              let integrationObj = {
                id: integration.id,
                name: integration.name,
                description: integration.description,
                api_key: integration.configuration.api_key,
                enabled: integration.enabled,
                integration: integration
              };

              rows.value.push(integrationObj);

            }
          })
          .catch(e => {

          });
      };

      function viewIntegrationConfig(id, name, integration) {
        if (name === "Bitdefender GravityZone"){
          $q.dialog({
            component: IntegrationConfigModal,
            componentProps: {
              id: id,
              name: name,
            }
          }) 
            .onOk(() => {
              getIntegrations()
            })
            
        }else if (name === "Cisco Meraki") {
          $q.dialog({
            component: IntegrationConfigModal,
            componentProps: {
              id: id,
              name: name,
            },
          })
            .onOk(() => {
              getIntegrations()
            })

        } else if (name === "Snipe-IT") {
          $q.dialog({
            component: IntegrationConfigModal,
            componentProps: {
              id: id,
              name: name,
              integration: integration
            },
          })
            .onOk(() => {
              getIntegrations()
            })

        } else {
          notifyError(name + " integration not yet implemented")
        }
      }
      onMounted(() => {
        getIntegrations();
      });

      return {
        pagination: {
          sortBy: 'desc',
          descending: false,
          rowsPerPage: 8
        },
        filter: ref(""),
        columns,
        rows,
        enabled,
        getIntegrations,
        // quasar dialog
        dialogRef,
        onDialogHide,
        viewIntegrationConfig,
      };
    },
  };



</script>