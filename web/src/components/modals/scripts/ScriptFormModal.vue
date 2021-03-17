<template>
  <q-dialog ref="dialog" @hide="onHide" persistent :maximized="maximized">
    <q-card class="q-dialog-plugin" :style="getMaxWidth">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="minimize" @click="maximized = false" :disable="!maximized">
          <q-tooltip v-if="maximized" content-class="bg-white text-primary">Minimize</q-tooltip>
        </q-btn>
        <q-btn dense flat icon="crop_square" @click="maximized = true" :disable="maximized">
          <q-tooltip v-if="!maximized" content-class="bg-white text-primary">Maximize</q-tooltip>
        </q-btn>
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
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
          <div class="q-pa-sm col-4">
            <q-input filled dense :readonly="readonly" v-model="localScript.description" label="Description" />
          </div>
        </q-card-section>
        <prism-editor
          class="editor"
          :readonly="readonly"
          v-model="localScript.code"
          :highlight="highlighter"
          :style="heightVar"
          lineNumbers
        ></prism-editor>
        <q-card-actions v-if="!readonly" align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
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
        category: "",
        favorite: false,
        script_type: "userdefined",
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
            this.notifyError(e.response.data.non_field_errors, 4000);
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
            this.notifyError(e.response.data.non_field_errors, 4000);
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
          this.notifyError(e.response.data.non_field_errors, 4000);
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
      return this.maximized ? "" : "width: 60vw; max-width: 90vw";
    },
    heightVar() {
      return this.maximized ? "--prism-height: 80vh" : "--prism-height: 70vh";
    },
  },
  created() {
    if (!!this.script) {
      this.localScript.id = this.script.id;
      this.localScript.name = this.script.name;
      this.localScript.description = this.script.description;
      this.localScript.favorite = this.script.favorite;
      this.localScript.shell = this.script.shell;
      this.localScript.category = this.script.category;
      this.localScript.script_type = this.script.script_type;
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

.prism-editor__container {
  height: 30000em;
}

/* optional class for removing the outline */
.prism-editor__textarea:focus {
  outline: none;
}

.prism-editor__textarea,
.prism-editor__container {
  width: 1000em !important;
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