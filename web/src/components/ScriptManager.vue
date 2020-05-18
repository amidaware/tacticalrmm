<template>
  <div class="q-pa-md q-gutter-sm">
    <q-dialog :value="toggleScriptManager" @hide="hideScriptManager" @show="getScripts">
      <q-card style="width: 900px; max-width: 90vw;">
        <q-bar>
          <q-btn @click="getScripts" class="q-mr-sm" dense flat push icon="refresh" />Script Manager
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-md">
          <div class="q-gutter-sm">
            <q-btn
              label="New"
              dense
              flat
              push
              unelevated
              no-caps
              icon="add"
              @click="showUploadScriptModal = true; clearRow"
            />
            <q-btn
              label="Edit"
              :disable="selectedRow === null"
              dense
              flat
              push
              unelevated
              no-caps
              icon="edit"
              @click="showEditScriptModal = true"
            />
            <q-btn
              label="Delete"
              :disable="selectedRow === null"
              dense
              flat
              push
              unelevated
              no-caps
              icon="delete"
              @click="deleteScript"
            />
            <q-btn
              label="View Code"
              :disable="selectedRow === null"
              dense
              flat
              push
              unelevated
              no-caps
              icon="remove_red_eye"
              @click="viewCode"
            />
            <q-btn
              label="Download Script"
              :disable="selectedRow === null"
              dense
              flat
              push
              unelevated
              no-caps
              icon="cloud_download"
              @click="downloadScript"
            />
          </div>
          <q-table
            dense
            class="settings-tbl-sticky"
            :data="scripts"
            :columns="columns"
            :visible-columns="visibleColumns"
            :pagination.sync="pagination"
            row-key="id"
            binary-state-sort
            hide-bottom
            virtual-scroll
            flat
            :rows-per-page-options="[0]"
          >
            <template slot="body" slot-scope="props" :props="props">
              <q-tr
                :class="{highlight: selectedRow === props.row.id}"
                @click="scriptRowSelected(props.row.id, props.row.filename)"
              >
                <q-td>{{ props.row.name }}</q-td>
                <q-td>{{ props.row.description }}</q-td>
                <q-td>{{ props.row.filename }}</q-td>
                <q-td>{{ props.row.shell }}</q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
        <q-card-section></q-card-section>
        <q-separator />
        <q-card-section></q-card-section>
      </q-card>
    </q-dialog>
    <q-dialog v-model="showUploadScriptModal">
      <UploadScript @close="showUploadScriptModal = false" @uploaded="getScripts" />
    </q-dialog>
    <q-dialog v-model="showEditScriptModal">
      <EditScript :pk="selectedRow" @close="showEditScriptModal = false" @edited="getScripts" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import UploadScript from "@/components/modals/scripts/UploadScript";
import EditScript from "@/components/modals/scripts/EditScript";
export default {
  name: "ScriptManager",
  components: { UploadScript, EditScript },
  mixins: [mixins],
  data() {
    return {
      selectedRow: null,
      showUploadScriptModal: false,
      showEditScriptModal: false,
      filename: null,
      pagination: {
        rowsPerPage: 0,
        sortBy: "id",
        descending: false
      },
      columns: [
        { name: "id", label: "ID", field: "id" },
        {
          name: "name",
          label: "Name",
          field: "name",
          align: "left",
          sortable: true
        },
        {
          name: "desc",
          label: "Description",
          field: "description",
          align: "left",
          sortable: false
        },
        {
          name: "file",
          label: "File",
          field: "filename",
          align: "left",
          sortable: true
        },
        {
          name: "shell",
          label: "Type",
          field: "shell",
          align: "left",
          sortable: true
        }
      ],
      visibleColumns: ["name", "desc", "file", "shell"]
    };
  },
  methods: {
    getScripts() {
      this.clearRow();
      this.$store.dispatch("getScripts");
    },
    hideScriptManager() {
      this.$store.commit("TOGGLE_SCRIPT_MANAGER", false);
    },
    scriptRowSelected(pk, filename) {
      this.selectedRow = pk;
      this.filename = filename;
    },
    clearRow() {
      this.selectedRow = null;
      this.filename = null;
    },
    viewCode() {
      axios
        .get(`/checks/viewscriptcode/${this.selectedRow}/`)
        .then(r => {
          this.$q.dialog({
            title: r.data.name,
            message: `<pre>${r.data.text}</pre>`,
            html: true,
            fullWidth: true
          });
        })
        .catch(() => this.notifyError("Something went wrong"));
    },
    deleteScript() {
      this.$q
        .dialog({
          title: "Delete script?",
          cancel: true,
          ok: { label: "Delete", color: "negative" }
        })
        .onOk(() => {
          const data = { pk: this.selectedRow };
          axios.delete("/checks/deletescript/", { data: data }).then(r => {
            this.getScripts();
            this.notifySuccess(`Script ${r.data} was deleted!`);
          });
        });
    },
    downloadScript() {
      axios
        .get(`/checks/downloadscript/${this.selectedRow}/`, { responseType: "blob" })
        .then(({ data }) => {
          const blob = new Blob([data], { type: "text/plain" });
          let link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = this.filename;
          link.click();
        })
        .catch(error => console.error(error));
    }
  },
  computed: {
    ...mapState({
      toggleScriptManager: state => state.toggleScriptManager,
      scripts: state => state.scripts
    })
  },
  mounted() {
    this.getScripts();
  }
};
</script>