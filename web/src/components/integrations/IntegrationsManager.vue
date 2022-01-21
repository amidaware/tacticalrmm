<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
    <q-card
      class="q-dialog-plugin"
      style="width: 90vw; max-width: 90vw; height: 40vw; max-height: 40vw"
    >
      <q-bar>
        Integrations Manager
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <q-table
          :rows="rows"
          :columns="columns"
          row-key="name"
          :filter="filter"
          grid
          hide-header
          :pagination="pagination"
        >
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
                  <div class="text-h6">{{ props.row.name }}</div>
                </q-card-section>
                <q-card-section class="q-pt-none">{{ props.row.description }}</q-card-section>
                <q-card-section>
                  <q-chip
                    dense
                    color="positive"
                    text-color="white"
                    icon="check_circle_outline"
                    v-if="props.row.enabled"
                    outline
                  >Enabled</q-chip>
                  <q-chip
                    v-if="props.row.agent_related === true"
                    dense
                    color="positive"
                    text-color="white"
                    outline
                  >Agent</q-chip>
                  <q-chip
                    v-if="props.row.client_related === true"
                    dense
                    color="positive"
                    text-color="white"
                    outline
                  >Client</q-chip>
                </q-card-section>
                <q-separator />
                <q-card-actions align="right">
                  <q-btn
                    size="md"
                    :label="props.row.enabled ? 'View Config' : 'Enable'"
                    class="q-ml-sm"
                    @click="getIntegrationModal(props.row)"
                  ></q-btn>
                  <q-btn
                    v-if="props.row.enabled"
                    size="md"
                    label="Disable"
                    class="q-ml-sm"
                    @click="getDisableIntegrationModal(props.row)"
                  ></q-btn>
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
import { ref, onMounted } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import IntegrationModal from "@/components/integrations/modals/IntegrationModal";
import DisableIntegrationModal from "@/components/integrations/modals/DisableIntegrationModal";

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

export default {
  name: "IntegrationsManager",
  emits: [...useDialogPluginComponent.emits],
  components: { IntegrationModal, DisableIntegrationModal },

  setup() {
    const { dialogRef, onDialogHide } = useDialogPluginComponent();
    const $q = useQuasar();

    const rows = ref([])

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
              configuration: integration.configuration,
              enabled: integration.enabled,
              agent_related: integration.agent_related,
              client_related: integration.client_related,
            };
            rows.value.push(integrationObj);
          }
        })
        .catch(e => {
        });
    };

    function getIntegrationModal(integration) {
      $q.dialog({
        component: IntegrationModal,
        componentProps: {
          integration: integration
        }
      }).onOk(() => {
        getIntegrations()
      })
    }

    function getDisableIntegrationModal(integration) {
      $q.dialog({
        component: DisableIntegrationModal,
        componentProps: {
          integration: integration
        }
      }).onOk(() => {
        getIntegrations()
      })
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
      getIntegrations,
      getIntegrationModal,
      getDisableIntegrationModal,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>