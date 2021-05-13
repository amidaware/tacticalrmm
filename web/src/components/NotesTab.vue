<template>
  <div v-if="!selectedAgentPk">No agent selected</div>
  <div v-else class="q-pa-xs">
    <q-btn size="sm" color="grey-5" icon="fas fa-plus" label="Add Note" text-color="black" @click="addNote" />
    <q-btn dense flat push @click="refreshNotes" icon="refresh" />
    <q-btn class="q-ml-xl" size="sm" color="primary" icon-right="archive" label="Export to csv" @click="exportTable" />
    <template v-if="notes === undefined || notes.length === 0">
      <p>No Notes</p>
    </template>
    <template v-else>
      <q-table
        grid
        class="tabs-tbl-sticky"
        :style="{ 'max-height': tabsTableHeight }"
        :rows="notes"
        :columns="columns"
        :visible-columns="visibleColumns"
        :v-model:pagination="pagination"
        row-key="id"
        :rows-per-page-options="[0]"
        hide-bottom
      >
        <template v-slot:top-right></template>
        <template v-slot:item="props">
          <q-card class="notes-card q-pa-none q-ma-xs" bordered>
            <q-card-section>
              <div class="row">
                <div class="col">
                  <div class="text-subtitle2">{{ props.row.entry_time }}</div>
                  <div class="text-caption">{{ props.row.username }}</div>
                </div>
                <div class="col-auto">
                  <q-btn color="grey-7" round flat icon="more_vert">
                    <q-menu cover auto-close>
                      <q-list>
                        <q-btn color="primary" push flat icon="edit" label="Edit" @click="editNote(props.row.id)" />
                        <br />
                        <q-btn
                          color="negative"
                          push
                          flat
                          icon="delete"
                          label="Delete"
                          @click="deleteNote(props.row.id)"
                        />
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
    </template>
  </div>
</template>

<script>
import { mapState, mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import { exportFile } from "quasar";

function wrapCsvValue(val, formatFn) {
  let formatted = formatFn !== void 0 ? formatFn(val) : val;

  formatted = formatted === void 0 || formatted === null ? "" : String(formatted);

  formatted = formatted.split('"').join('""').split("\n").join("\\n").split("\r").join("\\r");

  return `"${formatted}"`;
}

export default {
  name: "NotesTab",
  mixins: [mixins],
  data() {
    return {
      note: {},
      pagination: {
        rowsPerPage: 0,
        sortBy: "id",
        descending: false,
      },
      columns: [
        { name: "id", label: "ID", field: "id" },
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
      ],
      visibleColumns: ["entry_time", "username", "note"],
    };
  },
  methods: {
    addNote() {
      this.$q
        .dialog({
          title: "Add Note",
          prompt: {
            type: "textarea",
          },
          style: "width: 30vw; max-width: 50vw;",
          ok: { label: "Add" },
        })
        .onOk(data => {
          this.$axios
            .post(`/agents/${this.selectedAgentPk}/notes/`, { note: data })
            .then(r => {
              this.refreshNotes();
              this.notifySuccess(r.data);
            })
            .catch(e => {});
        });
    },
    editNote(pk) {
      this.$axios.get(`/agents/${pk}/note/`).then(r => {
        this.note = r.data;
        this.$q
          .dialog({
            title: "Edit Note",
            prompt: {
              model: this.note.note,
              type: "textarea",
            },
            style: "width: 30vw; max-width: 50vw;",
            ok: { label: "Save" },
            cancel: true,
          })
          .onOk(data => {
            this.note.note = data;
            this.$axios
              .patch(`/agents/${pk}/note/`, this.note)
              .then(r => {
                this.refreshNotes();
                this.notifySuccess(r.data);
              })
              .catch(e => {});
          })
          .onDismiss(() => {
            this.note = {};
          });
      });
    },
    deleteNote(pk) {
      this.$q
        .dialog({
          title: "Delete note?",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$axios
            .delete(`/agents/${pk}/note/`)
            .then(r => {
              this.refreshNotes();
              this.notifySuccess(r.data);
            })
            .catch(e => {});
        });
    },
    refreshNotes() {
      this.$store.dispatch("loadNotes", this.selectedAgentPk);
    },
    exportTable() {
      // naive encoding to csv format
      const content = [this.columns.map(col => wrapCsvValue(col.label))]
        .concat(
          this.notes.map(row =>
            this.columns
              .map(col =>
                wrapCsvValue(
                  typeof col.field === "function" ? col.field(row) : row[col.field === void 0 ? col.name : col.field],
                  col.format
                )
              )
              .join(",")
          )
        )
        .join("\r\n");

      const status = exportFile(`${this.agentHostname}-notes.csv`, content, "text/csv");

      if (status !== true) {
        this.$q.notify({
          message: "Browser denied file download...",
          color: "negative",
          icon: "warning",
        });
      }
    },
  },
  computed: {
    ...mapState({
      notes: state => state.notes,
    }),
    ...mapGetters(["selectedAgentPk", "tabsTableHeight", "agentHostname"]),
  },
};
</script>

<style lang="sass" scoped>
.notes-card
  width: 100%
  max-width: 20vw
</style>