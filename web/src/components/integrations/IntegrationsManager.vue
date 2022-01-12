<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
    <q-card class="q-dialog-plugin" style="width: 90vw; max-width: 90vw; height: 40vw; max-height: 40vw">
      <q-bar>
        Integrations Manager
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
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
                <q-card-section>
                  <q-chip dense color="positive" text-color="white" icon="check_circle_outline" v-if="props.row.enabled"
                    outline>
                    Enabled
                  </q-chip>
                  <q-chip dense color="positive" text-color="white" outline>
                    Agent
                  </q-chip>
                  <q-chip dense color="positive" text-color="white" v-if="props.row.client_org_related" outline>
                    Client
                  </q-chip>
                </q-card-section>
                <q-separator />
                <q-card-actions align="right">
                  <q-btn size="md" label="View Config" class="q-ml-sm"
                    @click="viewIntegrationConfig(props.row.id, props.row.name, props.row.integration)"></q-btn>
                </q-card-actions>
              </q-card>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
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
          name: 'name',
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
                client_org_related: integration.client_org_related,
                integration: integration
              };
              rows.value.push(integrationObj);
            }
          })
          .catch(e => {
          });
      };

      function viewIntegrationConfig(id, name, integration) {
        if (name === "Bitdefender GravityZone") {
          $q.dialog({
            component: IntegrationConfigModal,
            componentProps: {
              id: id,
              name: name,
              integration: integration
            }
          }).onOk(() => {
            getIntegrations()
          })

        } else if (name === "Cisco Meraki") {
          $q.dialog({
            component: IntegrationConfigModal,
            componentProps: {
              id: id,
              name: name,
              integration: integration
            },
          }).onOk(() => {
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
          }).onOk(() => {
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
          sortBy: 'name',
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