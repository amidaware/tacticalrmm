<template>
  <div style="width: 90vw; max-width: 90vw">
    <q-card>
      <q-bar>
        <q-btn @click="getScripts" class="q-mr-sm" dense flat push icon="refresh" />Script Manager
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <div class="q-pa-md">
        <div class="q-gutter-sm row">
          <q-btn-dropdown icon="add" label="New" no-caps dense flat>
            <q-list dense>
              <q-item clickable v-close-popup @click="newScript">
                <q-item-section side>
                  <q-icon size="xs" name="add" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>New Script</q-item-label>
                </q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showScriptUploadModal = true">
                <q-item-section side>
                  <q-icon size="xs" name="cloud_upload" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Upload Script</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>
          <q-btn
            label="View Code"
            :disable="!isRowSelected"
            dense
            flat
            push
            unelevated
            no-caps
            icon="remove_red_eye"
            @click="viewCode(selectedScript)"
          />
          <q-btn
            label="Download Script"
            :disable="!isRowSelected"
            dense
            flat
            push
            unelevated
            no-caps
            icon="cloud_download"
            @click="downloadScript(selectedScript)"
          />
        </div>
        <div class="row">
          <q-btn
            dense
            flat
            class="q-ml-sm"
            :label="tableView ? 'Folder View' : 'Table View'"
            :icon="tableView ? 'folder' : 'list'"
            @click="setTableView(!tableView)"
          />
          <q-btn
            dense
            flat
            class="q-ml-sm"
            :label="showCommunityScripts ? 'Hide Community Scripts' : 'Show Community Scripts'"
            :icon="showCommunityScripts ? 'visibility_off' : 'visibility'"
            @click="setShowCommunityScripts(!showCommunityScripts)"
          />
          <q-space />
          <q-input
            v-model="search"
            style="width: 300px"
            label="Search"
            dense
            outlined
            clearable
            class="q-pr-md q-pb-xs"
          >
            <template v-slot:prepend>
              <q-icon name="search" color="primary" />
            </template>
          </q-input>
        </div>
        <div class="scroll" style="min-height: 65vh; max-height: 65vh">
          <!-- List View -->
          <q-tree
            ref="folderTree"
            v-if="!tableView"
            :nodes="tree"
            :filter="search"
            no-connectors
            node-key="id"
            :expanded.sync="expanded"
            @update:selected="nodeSelected"
            :selected.sync="selected"
            no-results-label="No Scripts Found"
            no-nodes-label="No Scripts Found"
          >
            <template v-slot:header-script="props">
              <div :class="props.node.id === props.tree.selected ? 'text-primary' : ''">
                <q-icon v-if="props.node.favorite" color="yellow-8" name="star" size="sm" class="q-px-sm" />
                <q-icon v-else color="yellow-8" name="star_outline" size="sm" class="q-px-sm" />

                <q-icon v-if="props.node.shell === 'powershell'" name="mdi-powershell" color="primary">
                  <q-tooltip> Powershell </q-tooltip>
                </q-icon>
                <q-icon v-else-if="props.node.shell === 'python'" name="mdi-language-python" color="primary">
                  <q-tooltip> Python </q-tooltip>
                </q-icon>
                <q-icon v-else-if="props.node.shell === 'cmd'" name="mdi-microsoft-windows" color="primary">
                  <q-tooltip> Batch </q-tooltip>
                </q-icon>

                <span class="q-pl-xs text-weight-bold">{{ props.node.name }}</span>
                <span class="q-pl-xs">{{ props.node.description }}</span>
              </div>

              <!-- Context Menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item
                    clickable
                    v-close-popup
                    @click="editScript(props.node)"
                    :disable="props.node.script_type === 'builtin'"
                  >
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>

                  <q-item
                    clickable
                    v-close-popup
                    @click="deleteScript(props.node.id)"
                    :disable="props.node.script_type === 'builtin'"
                  >
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>

                  <q-item clickable v-close-popup @click="favoriteScript(props.node)">
                    <q-item-section side>
                      <q-icon name="star" />
                    </q-item-section>
                    <q-item-section>{{ favoriteText(props.node.favorite) }}</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup @click="viewCode(props.node)">
                    <q-item-section side>
                      <q-icon name="remove_red_eye" />
                    </q-item-section>
                    <q-item-section>View Code</q-item-section>
                  </q-item>

                  <q-item clickable v-close-popup @click="downloadScript(props.node)">
                    <q-item-section side>
                      <q-icon name="cloud_download" />
                    </q-item-section>
                    <q-item-section>Download Script</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup>
                    <q-item-section>Close</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
            </template>
          </q-tree>
          <q-table
            v-if="tableView"
            dense
            :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
            class="settings-tbl-sticky"
            :data="visibleScripts"
            :columns="columns"
            :visible-columns="visibleColumns"
            :pagination.sync="pagination"
            :filter="search"
            row-key="id"
            binary-state-sort
            hide-pagination
            virtual-scroll
            :rows-per-page-options="[0]"
          >
            <template v-slot:header-cell-favorite="props">
              <q-th :props="props" auto-width>
                <q-icon name="star" color="yellow-8" size="sm" />
              </q-th>
            </template>

            <template v-slot:header-cell-shell="props">
              <q-th :props="props" auto-width> Shell </q-th>
            </template>

            <template v-slot:no-data> No Scripts Found </template>
            <template slot="body" slot-scope="props" :props="props">
              <!-- Table View -->
              <q-tr
                :class="`${rowSelectedClass(props.row.id)} cursor-pointer`"
                @click="selectedScript = props.row"
                @contextmenu="selectedScript = props.row"
              >
                <!-- Context Menu -->
                <q-menu context-menu>
                  <q-list dense style="min-width: 200px">
                    <q-item
                      clickable
                      v-close-popup
                      @click="editScript(props.row)"
                      :disable="props.row.script_type === 'builtin'"
                    >
                      <q-item-section side>
                        <q-icon name="edit" />
                      </q-item-section>
                      <q-item-section>Edit</q-item-section>
                    </q-item>

                    <q-item
                      clickable
                      v-close-popup
                      @click="deleteScript(props.row.id)"
                      :disable="props.row.script_type === 'builtin'"
                    >
                      <q-item-section side>
                        <q-icon name="delete" />
                      </q-item-section>
                      <q-item-section>Delete</q-item-section>
                    </q-item>

                    <q-item clickable v-close-popup @click="favoriteScript(props.row)">
                      <q-item-section side>
                        <q-icon name="star" />
                      </q-item-section>
                      <q-item-section>{{ favoriteText(props.row.favorite) }}</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup @click="viewCode(props.row)">
                      <q-item-section side>
                        <q-icon name="remove_red_eye" />
                      </q-item-section>
                      <q-item-section>View Code</q-item-section>
                    </q-item>

                    <q-item clickable v-close-popup @click="downloadScript(props.row)">
                      <q-item-section side>
                        <q-icon name="cloud_download" />
                      </q-item-section>
                      <q-item-section>Download Script</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup>
                      <q-item-section>Close</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
                <q-td>
                  <q-icon v-if="props.row.favorite" color="yellow-8" name="star" size="sm" />
                </q-td>
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
                </q-td>
                <q-td>{{ props.row.name }}</q-td>
                <q-td>
                  <span v-if="props.row.args.length > 0">{{ props.row.args }}</span>
                </q-td>
                <q-td>{{ props.row.category }}</q-td>
                <q-td>
                  {{ truncateText(props.row.description) }}
                  <q-tooltip v-if="props.row.description.length >= 60" content-style="font-size: 12px">{{
                    props.row.description
                  }}</q-tooltip>
                </q-td>
                <q-td>{{ props.row.default_timeout }}</q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
      </div>
    </q-card>
    <q-dialog v-model="showScriptUploadModal">
      <ScriptUploadModal
        :script="selectedScript"
        :categories="categories"
        @close="showScriptUploadModal = false"
        @added="getScripts"
      />
    </q-dialog>
  </div>
</template>

<script>
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";
import ScriptUploadModal from "@/components/modals/scripts/ScriptUploadModal";
import ScriptFormModal from "@/components/modals/scripts/ScriptFormModal";

export default {
  name: "ScriptManager",
  components: { ScriptUploadModal },
  mixins: [mixins],
  data() {
    return {
      scripts: [],
      selectedScript: {},
      showScriptUploadModal: false,
      search: "",
      tableView: true,
      expanded: [],
      selected: null,
      pagination: {
        rowsPerPage: 0,
        sortBy: "favorite",
        descending: true,
      },
      columns: [
        {
          name: "favorite",
          label: "",
          field: "favorite",
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
          name: "name",
          label: "Name",
          field: "name",
          align: "left",
          sortable: true,
        },
        {
          name: "args",
          label: "Default Args",
          field: "args",
          align: "left",
        },
        {
          name: "category",
          label: "Category",
          field: "category",
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
          name: "default_timeout",
          label: "Default Timeout (seconds)",
          field: "default_timeout",
          align: "left",
          sortable: true,
        },
      ],
      visibleColumns: ["favorite", "name", "args", "category", "desc", "shell", "default_timeout"],
    };
  },
  methods: {
    getScripts() {
      this.clearRow();
      this.$axios.get("/scripts/scripts/").then(r => {
        this.scripts = r.data;
      });
    },
    setShowCommunityScripts(show) {
      this.$store.dispatch("setShowCommunityScripts", show);
    },
    clearRow() {
      this.selectedScript = {};
    },
    viewCode(script) {
      this.$q.dialog({
        component: ScriptFormModal,
        parent: this,
        script: script,
        readonly: true,
      });
    },
    favoriteScript(script) {
      this.$q.loading.show();
      const notifyText = !script.favorite ? "Script was favorited!" : "Script was removed as a favorite!";
      this.$axios
        .put(`/scripts/${script.id}/script/`, { favorite: !script.favorite })
        .then(() => {
          this.getScripts();
          this.$q.loading.hide();
          this.notifySuccess(notifyText);
        })
        .catch(() => {
          this.$q.loading.hide();
          this.notifyError("Something went wrong");
        });
    },
    deleteScript(scriptpk) {
      this.$q
        .dialog({
          title: "Delete script?",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$axios
            .delete(`/scripts/${scriptpk}/script/`)
            .then(r => {
              this.getScripts();
              this.notifySuccess(r.data);
            })
            .catch(() => this.notifySuccess("Something went wrong"));
        });
    },
    downloadScript(script) {
      this.$axios
        .get(`/scripts/${script.id}/download/`)
        .then(({ data }) => {
          const blob = new Blob([data.code], { type: "text/plain;charset=utf-8" });
          let link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = data.filename;
          link.click();
        })
        .catch(() => this.notifyError("Something went wrong"));
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
      if (this.selectedScript.id === id) return this.$q.dark.isActive ? "highlight-dark" : "highlight";
    },
    favoriteText(isFavorite) {
      return isFavorite ? "Remove as Favorite" : "Add as Favorite";
    },
    newScript() {
      this.$q
        .dialog({
          component: ScriptFormModal,
          parent: this,
          categories: this.categories,
          readonly: false,
        })
        .onOk(() => {
          this.getScripts();
        });
    },
    editScript(script) {
      this.$q
        .dialog({
          component: ScriptFormModal,
          parent: this,
          script: script,
          categories: this.categories,
          readonly: false,
        })
        .onOk(() => {
          this.getScripts();
        });
    },
    setTableView(view) {
      this.tableView = view;
      this.selectedScript = {};
      this.selected = null;
      this.expanded = [];
    },
    nodeSelected(nodeid) {
      if (nodeid) {
        this.selectedScript = this.$refs.folderTree.getNodeByKey(nodeid);
      } else {
        this.selectedScript = {};
      }
    },
  },
  computed: {
    ...mapState(["showCommunityScripts"]),
    visibleScripts() {
      return this.showCommunityScripts ? this.scripts : this.scripts.filter(i => i.script_type !== "builtin");
    },
    categories() {
      let list = [];
      this.scripts.forEach(script => {
        if (!!script.category && !list.includes(script.category)) {
          if (script.category !== "Community") {
            list.push(script.category);
          }
        }
      });
      return list;
    },
    isRowSelected() {
      return this.selectedScript.id !== null && this.selectedScript.id !== undefined;
    },
    tree() {
      if (this.tableView || this.visibleScripts.length === 0) {
        return [];
      } else {
        let nodes = [];

        // copy scripts and categories to new array
        let scriptsTemp = Object.assign([], this.visibleScripts);
        let categoriesTemp = Object.assign([], this.categories);

        // add Community and Unassigned values and categories array
        if (this.showCommunityScripts) categoriesTemp.push("Community");
        categoriesTemp.push("Unassigned");

        const sorted = categoriesTemp.sort();

        sorted.forEach(category => {
          let temp = {
            icon: "folder",
            iconColor: "yellow-9",
            label: category,
            selectable: false,
            id: category,
            children: [],
          };
          for (var i = scriptsTemp.length - 1; i >= 0; i--) {
            if (scriptsTemp[i].category === category) {
              temp.children.push({ label: scriptsTemp[i].name, header: "script", ...scriptsTemp[i] });
              scriptsTemp.splice(i, 1);
            } else if (category === "Unassigned" && !scriptsTemp[i].category) {
              temp.children.push({ label: scriptsTemp[i].name, header: "script", ...scriptsTemp[i] });
              scriptsTemp.splice(i, 1);
            }
          }

          nodes.push(temp);
        });

        return nodes;
      }
    },
  },
  mounted() {
    this.getScripts();
  },
};
</script>