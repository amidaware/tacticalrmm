<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card
      class="q-dialog-plugin"
      :style="{
        width: `${$q.screen.width - 300}px`,
        'max-width': `${$q.screen.width - 300}px`,
        height: `${$q.screen.height - 300}px`,
        'max-height': `${$q.screen.height - 300}px`,
      }"
    >
      <q-bar>
        <q-btn @click="getSnippets" class="q-mr-sm" dense flat push icon="refresh" />Script Snippets
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-table
        dense
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        :style="{ 'max-height': `${$q.screen.height - 300 - 32}px` }"
        class="tbl-sticky"
        :rows="snippets"
        :columns="columns"
        :loading="loading"
        :pagination="{ rowsPerPage: 0, sortBy: 'name', descending: true }"
        row-key="id"
        binary-state-sort
        virtual-scroll
        :rows-per-page-options="[0]"
      >
        <template v-slot:top>
          <q-btn dense flat no-caps icon="add" label="New" @click="newSnippetModal" />
        </template>
        <template v-slot:header-cell-shell="props">
          <q-th :props="props" auto-width> Shell </q-th>
        </template>

        <template v-slot:body="props">
          <!-- Table View -->
          <q-tr :props="props" @dblclick="editSnippetModal(props.row)" class="cursor-pointer">
            <!-- Context Menu -->
            <q-menu context-menu>
              <q-list dense style="min-width: 200px">
                <q-item clickable v-close-popup @click="editSnippetModal(props.row)">
                  <q-item-section side>
                    <q-icon name="edit" />
                  </q-item-section>
                  <q-item-section>Edit</q-item-section>
                </q-item>

                <q-item clickable v-close-popup @click="deleteSnippet(props.row)">
                  <q-item-section side>
                    <q-icon name="delete" />
                  </q-item-section>
                  <q-item-section>Delete</q-item-section>
                </q-item>

                <q-item clickable v-close-popup>
                  <q-item-section>Close</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
            <q-td>
              <q-icon v-if="props.row.shell === 'powershell'" name="mdi-powershell" color="primary" size="sm">
                <q-tooltip> Powershell </q-tooltip>
              </q-icon>
              <q-icon v-else-if="props.row.shell === 'python'" name="mdi-language-python" color="primary" size="sm">
                <q-tooltip> Python </q-tooltip>
              </q-icon>
              <q-icon v-else-if="props.row.shell === 'cmd'" name="mdi-microsoft-windows" color="primary" size="sm">
                <q-tooltip> Batch </q-tooltip>
              </q-icon>
              <q-icon v-else-if="props.row.shell === 'shell'" name="mdi-bash" color="primary" size="sm">
                <q-tooltip> Shell </q-tooltip>
              </q-icon>
            </q-td>
            <!-- name -->
            <q-td>{{ props.row.name }}</q-td>
            <q-td>{{ props.row.desc }}</q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, onMounted } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { fetchScriptSnippets, removeScriptSnippet } from "@/api/scripts";
import { notifySuccess } from "@/utils/notify";

// ui imports
import ScriptSnippetFormModal from "@/components/scripts/ScriptSnippetFormModal";

// static data
const columns = [
  {
    name: "shell",
    label: "Shell",
    field: "shell",
    align: "left",
    sortable: true,
  },
  {
    name: "name",
    label: "Name",
    field: "name",
    align: "left",
    sortable: true,
  },
  {
    name: "desc",
    label: "Description",
    field: "description",
    align: "left",
    sortable: false,
  },
];

export default {
  name: "ScriptSnippetManager",
  emits: [...useDialogPluginComponent.emits],
  setup() {
    // setup quasar plugins
    const { dialogRef, onDialogHide } = useDialogPluginComponent();
    const $q = useQuasar();

    // script snippet manager logic
    const snippets = ref([]);

    async function getSnippets() {
      loading.value = true;
      try {
        snippets.value = await fetchScriptSnippets();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    function deleteSnippet(snippet) {
      $q.dialog({
        title: `Delete script snippet: ${snippet.name}?`,
        cancel: true,
        ok: { label: "Delete", color: "negative" },
      }).onOk(async () => {
        loading.value = true;
        try {
          const data = await removeScriptSnippet(snippet.id);
          notifySuccess(data);
          getSnippets();
        } catch (e) {}

        loading.value = false;
      });
    }

    // table setup
    const loading = ref(false);

    function newSnippetModal() {
      $q.dialog({
        component: ScriptSnippetFormModal,
      }).onOk(() => {
        getSnippets();
      });
    }

    function editSnippetModal(snippet) {
      $q.dialog({
        component: ScriptSnippetFormModal,
        componentProps: {
          snippet,
        },
      }).onOk(getSnippets);
    }

    // component life cycle hooks
    onMounted(getSnippets);

    return {
      // reactive data
      snippets,
      loading,

      // non-reactive data
      columns,

      // api methods
      getSnippets,
      deleteSnippet,

      // dialog methods
      newSnippetModal,
      editSnippetModal,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>