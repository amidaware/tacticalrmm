<template>
  <q-dialog ref="dialog" @hide="onHide" persistent :maximized="maximized">
    <q-card class="q-dialog-plugin" :style="getMaxWidth">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="minimize" @click="maximized = false" :disable="!maximized">
          <q-tooltip v-if="maximized" class="bg-white text-primary">Minimize</q-tooltip>
        </q-btn>
        <q-btn dense flat icon="crop_square" @click="maximized = true" :disable="maximized">
          <q-tooltip v-if="!maximized" class="bg-white text-primary">Maximize</q-tooltip>
        </q-btn>
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="submit">
        <q-card-section class="row">
          <div class="q-pa-sm col-1" style="width: auto">
            <q-icon
              class="cursor-pointer"
              :name="favoriteIcon"
              size="md"
              color="yellow-8"
              @[clickEvent]="localScript.favorite = !localScript.favorite"
            />
          </div>
          <div class="q-pa-sm col-2">
            <q-input
              filled
              dense
              :readonly="readonly"
              v-model="localScript.name"
              label="Name"
              :rules="[val => !!val || '*Required']"
            />
          </div>
          <div class="q-pa-sm col-2">
            <q-select
              :readonly="readonly"
              options-dense
              filled
              dense
              v-model="localScript.shell"
              :options="shellOptions"
              emit-value
              map-options
              label="Shell Type"
            />
          </div>
          <div class="q-pa-sm col-2">
            <q-input
              type="number"
              filled
              dense
              :readonly="readonly"
              v-model.number="localScript.default_timeout"
              label="Timeout (seconds)"
              :rules="[val => val >= 5 || 'Minimum is 5']"
            />
          </div>
          <div class="q-pa-sm col-3">
            <q-select
              hint="Press Enter or Tab when adding a new value"
              dense
              options-dense
              filled
              v-model="localScript.category"
              :options="filterOptions"
              use-input
              clearable
              new-value-mode="add-unique"
              debounce="0"
              @filter="filterFn"
              label="Category"
              :readonly="readonly"
            />
          </div>
          <div class="q-pa-sm col-2">
            <q-input filled dense :readonly="readonly" v-model="localScript.description" label="Description" />
          </div>
        </q-card-section>
        <div class="q-px-sm q-pt-none q-pb-sm q-mt-none row">
          <q-select
            label="Script Arguments (press Enter after typing each argument)"
            class="col-12"
            filled
            v-model="localScript.args"
            use-input
            use-chips
            multiple
            dense
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </div>
        <prism-editor
          class="editor"
          :readonly="readonly"
          v-model="localScript.code"
          :highlight="highlighter"
          :style="heightVar"
          line-numbers
          @click="focusTextArea"
        />
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn dense flat color="primary" label="Test Script" @click="runTestScript" />
          <q-btn v-if="!readonly" dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import TestScriptModal from "@/components/modals/scripts/TestScriptModal";
import mixins from "@/mixins/mixins";
import { PrismEditor } from "vue-prism-editor";
import "vue-prism-editor/dist/prismeditor.min.css";

import { highlight, languages } from "prismjs/components/prism-core";
import "prismjs/components/prism-batch";
import "prismjs/components/prism-python";
import "prismjs/components/prism-powershell";
import "prismjs/themes/prism-tomorrow.css";

export default {
  name: "ScriptFormModal",
  emits: ["hide", "ok", "cancel"],
  mixins: [mixins],
  components: {
    PrismEditor,
  },
  props: {
    script: Object,
    categories: !Array,
    readonly: Boolean,
  },
  data() {
    return {
      localScript: {
        name: "",
        code: "",
        shell: "powershell",
        description: "",
        args: [],
        category: "",
        favorite: false,
        script_type: "userdefined",
        default_timeout: 90,
      },
      maximized: false,
      filterOptions: [],
      shellOptions: [
        { label: "Powershell", value: "powershell" },
        { label: "Batch", value: "cmd" },
        { label: "Python", value: "python" },
      ],
    };
  },
  methods: {
    submit() {
      this.$q.loading.show();

      if (!!this.script) {
        this.$axios
          .put(`/scripts/${this.script.id}/script/`, this.localScript)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess(r.data);
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      } else {
        this.$axios
          .post(`/scripts/scripts/`, this.localScript)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess(r.data);
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      }
    },
    getCode() {
      this.$q.loading.show();
      this.$axios
        .get(`/scripts/${this.script.id}/download/`)
        .then(r => {
          this.$q.loading.hide();
          this.localScript.code = r.data.code;
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    highlighter(code) {
      let lang = this.localScript.shell === "cmd" ? "batch" : this.localScript.shell;
      return highlight(code, languages[lang]);
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
    onOk() {
      this.$emit("ok");
      this.hide();
    },
    onCancel() {
      this.hide();
    },
    filterFn(val, update) {
      update(() => {
        if (val === "") {
          this.filterOptions = this.categories;
        } else {
          const needle = val.toLowerCase();
          this.filterOptions = this.categories.filter(v => v.toLowerCase().indexOf(needle) > -1);
        }
      });
    },
    focusTextArea() {
      document.getElementsByClassName("prism-editor__textarea")[0].focus();
    },
    runTestScript() {
      this.$q.dialog({
        component: TestScriptModal,
        componentProps: {
          script: this.localScript,
        },
      });
    },
  },
  computed: {
    favoriteIcon() {
      return this.localScript.favorite ? "star" : "star_outline";
    },
    title() {
      if (!!this.script) {
        return this.readonly ? `Viewing ${this.script.name}` : `Editing ${this.script.name}`;
      } else {
        return "Adding new script";
      }
    },
    clickEvent() {
      return !this.readonly ? "click" : null;
    },
    getMaxWidth() {
      return this.maximized ? "" : "width: 70vw; max-width: 90vw";
    },
    heightVar() {
      return this.maximized ? "--prism-height: 76vh" : "--prism-height: 70vh";
    },
  },
  mounted() {
    if (!!this.script) {
      this.localScript.id = this.script.id;
      this.localScript.name = this.script.name;
      this.localScript.description = this.script.description;
      this.localScript.favorite = this.script.favorite;
      this.localScript.shell = this.script.shell;
      this.localScript.category = this.script.category;
      this.localScript.script_type = this.script.script_type;
      this.localScript.default_timeout = this.script.default_timeout;
      this.localScript.args = this.script.args;
      this.getCode();
    }
  },
};
</script>

<style>
/* required class */
.editor {
  /* we dont use `language-` classes anymore so thats why we need to add background and text color manually */
  background: #2d2d2d;
  color: #ccc;

  /* you must provide font-family font-size line-height. Example: */
  font-family: Fira code, Fira Mono, Consolas, Menlo, Courier, monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 5px;
  height: var(--prism-height);
}

/* optional class for removing the outline */
.prism-editor__textarea:focus {
  outline: none;
}

.prism-editor__textarea,
.prism-editor__container {
  width: 500em !important;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.prism-editor__container::-webkit-scrollbar,
.prism-editor__textarea::-webkit-scrollbar {
  display: none;
}

.prism-editor__editor {
  white-space: pre !important;
}
.prism-editor__container {
  overflow-x: auto !important;
}
</style>