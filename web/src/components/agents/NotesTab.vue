<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else>
    <q-table
      grid
      class="tabs-tbl-sticky"
      :style="{ 'max-height': tabHeight }"
      :rows="notes"
      :columns="columns"
      v-model:pagination="pagination"
      row-key="id"
      :rows-per-page-options="[0]"
      :loading="loading"
      hide-bottom
      virtual-scroll
      no-data-label="No notes"
    >
      <template v-slot:top>
        <q-btn class="q-mr-sm" dense flat push @click="getNotes" icon="refresh" />
        <q-btn icon="add" label="Add Note" no-caps dense flat push @click="addNote" />
        <q-space />
        <export-table-btn :data="notes" :columns="columns" />
      </template>

      <template v-slot:loading>
        <q-inner-loading showing color="primary" />
      </template>

      <template v-slot:item="props">
        <q-card class="notes-card q-pa-none q-ma-xs" bordered>
          <q-card-section>
            <div class="row">
              <div class="col">
                <div class="text-subtitle2">{{ formatDate(props.row.entry_time) }}</div>
                <div class="text-caption">{{ props.row.username }}</div>
              </div>
              <div class="col-auto">
                <q-btn color="grey-7" round flat icon="more_vert">
                  <q-menu cover auto-close>
                    <q-list dense>
                      <q-item clickable v-close-popup @click="editNote(props.row)">
                        <q-item-section side>
                          <q-icon name="edit" />
                        </q-item-section>
                        <q-item-section>Edit</q-item-section>
                      </q-item>

                      <q-item clickable v-close-popup @click="deleteNote(props.row)">
                        <q-item-section side>
                          <q-icon name="delete" />
                        </q-item-section>
                        <q-item-section>Delete</q-item-section>
                      </q-item>
                    </q-list>
                  </q-menu>
                </q-btn>
              </div>
            </div>
          </q-card-section>
          <q-card-section style="max-height: 20vh" class="scroll">
            <pre>{{ props.row.note }}</pre>
          </q-card-section>
        </q-card>
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { useQuasar } from "quasar";
import { fetchAgentNotes, editAgentNote, saveAgentNote, removeAgentNote } from "@/api/agents";
import { notifySuccess } from "@/utils/notify";

// ui imports
import ExportTableBtn from "@/components/ui/ExportTableBtn";

// static data
const columns = [
  {
    name: "entry_time",
    label: "Date",
    field: "entry_time",
  },
  {
    name: "username",
    label: "User",
    field: "username",
  },
  {
    name: "note",
    label: "Note",
    field: "note",
  },
];

export default {
  name: "NotesTab",
  components: {
    ExportTableBtn,
  },
  setup(props) {
    // setup vuex
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const tabHeight = computed(() => store.state.tabHeight);
    const formatDate = computed(() => store.getters.formatDate);

    // setup quasar
    const $q = useQuasar();

    // notes tab logic
    const noteText = ref("");
    const notes = ref([]);
    const loading = ref(false);
    const pagination = ref({
      rowsPerPage: 0,
      sortBy: "id",
      descending: false,
    });

    async function getNotes() {
      loading.value = true;
      notes.value = await fetchAgentNotes(selectedAgent.value);
      loading.value = false;
    }

    function addNote() {
      noteText.value = "";
      $q.dialog({
        title: "Add Note",
        prompt: {
          model: noteText,
          type: "textarea",
          isValid: val => !!val,
        },
        style: "width: 30vw; max-width: 50vw;",
        ok: { label: "Add" },
        cancel: true,
      }).onOk(async () => {
        loading.value = true;
        try {
          const result = await saveAgentNote({ agent_id: selectedAgent.value, note: noteText.value });
          notifySuccess(result);
          await getNotes();
        } catch (e) {
          console.error(e);
        }
        loading.value = false;
      });
    }

    function editNote(note) {
      $q.dialog({
        title: "Edit Note",
        prompt: {
          model: note.note,
          type: "textarea",
          isValid: val => !!val,
        },
        style: "width: 30vw; max-width: 50vw;",
        ok: { label: "Save" },
        cancel: true,
      }).onOk(async data => {
        loading.value = true;
        try {
          const result = await editAgentNote(note.pk, { note: data });
          notifySuccess(result);
          await getNotes();
        } catch (e) {
          console.error(e);
        }
        loading.value = false;
      });
    }

    function deleteNote(note) {
      $q.dialog({
        title: "Delete note?",
        cancel: true,
        ok: { label: "Delete", color: "negative" },
      }).onOk(async () => {
        loading.value = true;
        try {
          const result = await removeAgentNote(note.pk);
          notifySuccess(result);
          await getNotes();
        } catch (e) {
          console.error(e);
        }
        loading.value = false;
      });
    }

    watch(selectedAgent, (newValue, oldValue) => {
      if (newValue) {
        getNotes();
      }
    });

    onMounted(() => {
      if (selectedAgent.value) getNotes();
    });

    return {
      // reactive data
      notes,
      loading,
      pagination,
      selectedAgent,
      tabHeight,
      noteText,

      // non-reactive data
      columns,

      // methods
      formatDate,
      getNotes,
      addNote,
      editNote,
      deleteNote,
    };
  },
};
</script>

<style lang="sass" scoped>
.notes-card
  width: 100%
  max-width: 20vw
</style>