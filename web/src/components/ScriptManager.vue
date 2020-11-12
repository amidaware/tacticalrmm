<template>
  <div class="q-pa-md q-gutter-sm">
    <q-dialog :value="toggleScriptManager" @hide="hideScriptManager" @show="getScripts">
      <q-card style="min-width: 70vw">
        <q-bar>
          <q-btn @click="getScripts" class="q-mr-sm" dense flat push icon="refresh" />Script Manager
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-md">
          <div class="q-gutter-sm row">
            <q-btn
              label="New"
              dense
              flat
              push
              unelevated
              no-caps
              icon="add"
              @click="
                showScript('add');
                clearRow();
              "
            />
            <q-btn
              label="Edit"
              :disable="scriptpk === null"
              dense
              flat
              push
              unelevated
              no-caps
              icon="edit"
              @click="showScript('edit')"
            />
            <q-btn
              label="Delete"
              :disable="scriptpk === null || isBuiltInScript(scriptpk)"
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
              :disable="scriptpk === null"
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
              :disable="scriptpk === null"
              dense
              flat
              push
              unelevated
              no-caps
              icon="cloud_download"
              @click="downloadScript"
            />
            <q-space />
            <q-toggle :value="showBuiltIn" label="Show Community Scripts" @input="showBuiltIn = !showBuiltIn" />
          </div>
          <q-table
            dense
            :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
            class="settings-tbl-sticky"
            :data="visibleScripts"
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
                :class="rowSelectedClass(props.row.id)"
                @click="
                  scriptpk = props.row.id;
                  filename = props.row.filename;
                  code = props.row.code;
                "
              >
                <q-td>{{ props.row.name }}</q-td>
                <q-td>
                  {{ truncateText(props.row.description) }}
                  <q-tooltip v-if="props.row.description.length >= 60" content-style="font-size: 12px">{{
                    props.row.description
                  }}</q-tooltip>
                </q-td>
                <q-td>{{ props.row.filename }}</q-td>
                <q-td>{{ props.row.shell }}</q-td>
                <q-td v-show="props.row.script_type === 'userdefined'">User Defined</q-td>
                <q-td v-show="props.row.script_type === 'builtin'">Community Uploaded</q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
        <q-card-section></q-card-section>
        <q-separator />
        <q-card-section></q-card-section>
      </q-card>
    </q-dialog>
    <q-dialog v-model="showScriptModal">
      <ScriptModal :mode="mode" :scriptpk="scriptpk" @close="showScriptModal = false" @uploaded="getScripts" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import ScriptModal from "@/components/modals/scripts/ScriptModal";
export default {
  name: "ScriptManager",
  components: { ScriptModal },
  mixins: [mixins],
  data() {
    return {
      mode: "add",
      scriptpk: null,
      showScriptModal: false,
      filename: null,
      code: null,
      showBuiltIn: true,
      pagination: {
        rowsPerPage: 0,
        sortBy: "script_type",
        descending: true,
      },
      columns: [
        { name: "id", label: "ID", field: "id" },
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
        {
          name: "file",
          label: "File",
          field: "filename",
          align: "left",
          sortable: true,
        },
        {
          name: "shell",
          label: "Shell",
          field: "shell",
          align: "left",
          sortable: true,
        },
        {
          name: "script_type",
          label: "Type",
          field: "script_type",
          align: "left",
          sortable: true,
        },
      ],
      visibleColumns: ["name", "desc", "file", "shell", "script_type"],
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
    clearRow() {
      this.scriptpk = null;
      this.filename = null;
    },
    viewCode() {
      this.$q.dialog({
        title: this.filename,
        message: `<pre>${this.code}</pre>`,
        html: true,
        style: "width: 70vw; max-width: 80vw;",
      });
    },
    deleteScript() {
      this.$q
        .dialog({
          title: "Delete script?",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          axios
            .delete(`/scripts/${this.scriptpk}/script/`)
            .then(r => {
              this.getScripts();
              this.notifySuccess(r.data);
            })
            .catch(() => this.notifySuccess("Something went wrong"));
        });
    },
    downloadScript() {
      axios
        .get(`/scripts/${this.scriptpk}/download/`, { responseType: "blob" })
        .then(({ data }) => {
          const blob = new Blob([data], { type: "text/plain" });
          let link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = this.filename;
          link.click();
        })
        .catch(() => this.notifyError("Something went wrong"));
    },
    showScript(mode) {
      switch (mode) {
        case "add":
          this.mode = "add";
          break;
        case "edit":
          this.mode = "edit";
          break;
      }
      this.showScriptModal = true;
    },
    truncateText(txt) {
      return txt.length >= 60 ? txt.substring(0, 60) + "..." : txt;
    },
    isBuiltInScript(pk) {
      try {
        return this.scripts.find(i => i.id === pk).script_type === "builtin" ? true : false;
      } catch (e) {
        return false;
      }
    },
    rowSelectedClass(id) {
      if (this.scriptpk === id) return this.$q.dark.isActive ? "highlight-dark" : "highlight";
    },
  },
  computed: {
    ...mapState({
      toggleScriptManager: state => state.toggleScriptManager,
      scripts: state => state.scripts,
    }),
    visibleScripts() {
      return this.showBuiltIn ? this.scripts : this.scripts.filter(i => i.script_type !== "builtin");
    },
  },
  mounted() {
    this.getScripts();
  },
};
</script>