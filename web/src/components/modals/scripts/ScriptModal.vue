<template>
  <q-card style="width: 40vw">
    <q-form @submit.prevent="handleScript">
      <q-card-section class="row items-center">
        <div v-if="mode === 'add'" class="text-h6">Add Script</div>
        <div v-else-if="mode === 'edit'" class="text-h6">Edit Script</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Name:</div>
        <div class="col-10">
          <q-input
            :disable="isBuiltInScript"
            outlined
            dense
            v-model="script.name"
            :rules="[val => !!val || '*Required']"
          />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Description:</div>
        <div class="col-10">
          <q-input :disable="isBuiltInScript" outlined dense v-model="script.description" type="textarea" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">File Upload:</div>
        <div v-if="mode === 'add'" class="col-10">
          <q-file
            v-model="script.filename"
            label="Supported file types: .ps1, .bat, .py"
            stack-label
            filled
            counter
            accept=".ps1, .bat, .py"
            :rules="[val => !!val || '*Required']"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
        </div>
        <!-- don't enforce rules if edit mode -->
        <div v-if="mode === 'edit'" class="col-10">
          <q-file
            v-model="script.filename"
            :disable="isBuiltInScript"
            label="Upload new script version"
            stack-label
            filled
            counter
            accept=".ps1, .bat, .py"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Type:</div>
        <q-select
          :disable="isBuiltInScript"
          dense
          options-dense
          class="col-10"
          outlined
          v-model="script.shell"
          :options="shellOptions"
          emit-value
          map-options
          :rules="[val => !!val || '*Required']"
        />
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn v-if="mode === 'add'" label="Upload" color="primary" type="submit" />
        <q-btn v-else-if="mode === 'edit'" :disable="isBuiltInScript" label="Edit" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "ScriptModal",
  mixins: [mixins],
  props: {
    scriptpk: Number,
    mode: String,
  },
  data() {
    return {
      script: {},
      originalFile: null,
      shellOptions: [
        { label: "Powershell", value: "powershell" },
        { label: "Batch (CMD)", value: "cmd" },
        { label: "Python", value: "python" },
      ],
    };
  },
  methods: {
    getScript() {
      axios.get(`/scripts/${this.scriptpk}/script/`).then(r => {
        this.originalFile = r.data.filename;
        delete r.data.filename;
        this.script = r.data;
      });
    },
    handleScript() {
      let formData = new FormData();

      if (this.mode === "add") {
        formData.append("filename", this.script.filename);
      }
      // only append file if uploading a new file
      else if (this.mode === "edit" && this.script.filename) {
        formData.append("filename", this.script.filename);

        // filename needs to be the same if editing so we don't have a ghost file on server
        if (this.script.filename.name !== this.originalFile) {
          this.notifyError("Script filename must be the same if editing.", 4000);
          return;
        }
      }

      let url;
      switch (this.mode) {
        case "add":
          url = "/scripts/scripts/";
          break;
        case "edit":
          url = `/scripts/${this.scriptpk}/script/`;
          break;
      }

      formData.append("name", this.script.name);
      formData.append("shell", this.script.shell);
      formData.append("description", this.script.description);

      this.$q.loading.show();
      axios
        .put(url, formData)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$emit("uploaded");
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data.non_field_errors, 4000);
        });
    },
  },
  computed: {
    ...mapState({
      scripts: state => state.scripts,
    }),
    isBuiltInScript() {
      if (this.mode === "edit") {
        return this.scripts.find(i => i.id === this.scriptpk).script_type === "builtin" ? true : false;
      } else {
        return false;
      }
    },
  },
  created() {
    if (this.mode === "edit") {
      this.getScript();
    }
  },
};
</script>