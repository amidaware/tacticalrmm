<template>
  <div>
    <div class="row">
      <div class="text-subtitle2">API Keys</div>
      <q-space />
      <q-btn size="sm" color="grey-5" icon="fas fa-plus" text-color="black" label="Add key" @click="addAPIKey" />
    </div>
    <q-separator />
    <q-table
      dense
      :rows="keys"
      :columns="columns"
      v-model:pagination="pagination"
      row-key="id"
      binary-state-sort
      hide-pagination
      virtual-scroll
      :rows-per-page-options="[0]"
      no-data-label="No API tokens added yet"
    >
      <!-- header slots -->
      <template v-slot:header-cell-actions="props">
        <q-th :props="props" auto-width> </q-th>
      </template>

      <!-- body slots -->
      <template v-slot:body="props">
        <q-tr :props="props" class="cursor-pointer" @dblclick="editAPIKey(props.row)">
          <!-- context menu -->
          <q-menu context-menu>
            <q-list dense style="min-width: 200px">
              <q-item clickable v-close-popup @click="editAPIKey(props.row)">
                <q-item-section side>
                  <q-icon name="edit" />
                </q-item-section>
                <q-item-section>Edit</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="deleteAPIKey(props.row)">
                <q-item-section side>
                  <q-icon name="delete" />
                </q-item-section>
                <q-item-section>Delete</q-item-section>
              </q-item>

              <q-separator></q-separator>

              <q-item clickable v-close-popup>
                <q-item-section>Close</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <!-- name -->
          <q-td>
            {{ props.row.name }}
          </q-td>
          <q-td>
            {{ props.row.username }}
          </q-td>
          <!-- expiration -->
          <q-td>
            {{ formatDate(props.row.expiration) }}
          </q-td>
          <!-- created time -->
          <q-td>
            {{ formatDate(props.row.created_time) }}
          </q-td>
          <q-td>
            <q-icon size="sm" name="content_copy" @click="copyKeyToClipboard(props.row.key)">
              <q-tooltip>Copy API Key to clipboard</q-tooltip>
            </q-icon>
          </q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { ref, computed, onMounted } from "vue";
import { useStore } from "vuex";
import { fetchAPIKeys, removeAPIKey } from "@/api/accounts";
import { useQuasar, copyToClipboard } from "quasar";
import { notifySuccess, notifyError } from "@/utils/notify";
import APIKeysForm from "@/components/core/APIKeysForm";

const columns = [
  {
    name: "name",
    label: "Name",
    field: "name",
    align: "left",
    sortable: true,
  },
  {
    name: "username",
    label: "User",
    field: "username",
    align: "left",
    sortable: true,
  },
  {
    name: "expiration",
    label: "Expiration",
    field: "expiration",
    align: "left",
    sortable: true,
  },
  {
    name: "created_time",
    label: "Created",
    field: "created_time",
    align: "left",
    sortable: true,
  },
  {
    name: "actions",
    label: "",
    field: "actions",
  },
];
export default {
  name: "APIKeysTable",
  setup() {
    // setup quasar
    const $q = useQuasar();

    // setup vuex
    const store = useStore();
    const formatDate = computed(() => store.getters.formatDate);

    // setup api keys logic
    const keys = ref([]);
    const loading = ref(false);

    // setup table
    const pagination = ref({
      rowsPerPage: 0,
      sortBy: "name",
      descending: true,
    });

    function copyKeyToClipboard(apikey) {
      copyToClipboard(apikey)
        .then(() => {
          notifySuccess("Key was copied to clipboard!");
        })
        .catch(() => {
          notifyError("Unable to copy to clipboard!");
        });
    }

    // api functions
    async function getAPIKeys() {
      loading.value = true;
      keys.value = await fetchAPIKeys();
      loading.value = false;
    }

    async function deleteAPIKey(key) {
      $q.dialog({
        title: `Delete API key: ${key.name}?`,
        cancel: true,
        ok: { label: "Delete", color: "negative" },
      }).onOk(async () => {
        loading.value = true;
        try {
          const result = await removeAPIKey(key.id);
          notifySuccess(result);
          getAPIKeys();
          loading.value = false;
        } catch (e) {
          console.error(e);
          loading.value = false;
        }
      });
    }

    // quasar dialog functions
    function editAPIKey(key) {
      $q.dialog({
        component: APIKeysForm,
        componentProps: {
          APIKey: key,
        },
      }).onOk(() => getAPIKeys());
    }

    function addAPIKey() {
      $q.dialog({
        component: APIKeysForm,
      }).onOk(() => getAPIKeys());
    }

    // component lifecycle hooks
    onMounted(getAPIKeys());
    return {
      // reactive data
      keys,
      loading,
      pagination,

      // non-reactive data
      columns,

      //methods
      getAPIKeys,
      deleteAPIKey,
      copyKeyToClipboard,
      formatDate,

      //dialogs
      editAPIKey,
      addAPIKey,
    };
  },
};
</script>