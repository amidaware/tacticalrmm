<template>
  <q-card style="width: 40vw">
    <q-bar>
      Add Script
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-form @submit.prevent="submit">
      <q-card-section class="row">
        <div class="col-2">Name:</div>
        <div class="col-10">
          <q-input outlined dense v-model="script.name" :rules="[val => !!val || '*Required']" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Description:</div>
        <div class="col-10">
          <q-input outlined dense v-model="script.description" type="textarea" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Category:</div>
        <q-select
          hint="Press Enter or Tab when adding a new value"
          dense
          options-dense
          class="col-10"
          outlined
          v-model="script.category"
          :options="filterOptions"
          use-input
          clearable
          new-value-mode="add-unique"
          debounce="0"
          @filter="filterFn"
        />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">File Upload:</div>
        <div class="col-10">
          <q-file
            v-model="script.filename"
            label="Supported file types: .ps1, .bat, .py"
            stack-label
            filled
            counter
            class="full-width"
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
          dense
          options-dense
          class="col-10"
          outlined
          v-model="script.shell"
          :options="shellOptions"
          emit-value
          map-options
        />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Script Arguments:</div>
        <q-select
          label="(press Enter after typing each argument)"
          class="col-10"
          filled
          v-model="script.args"
          use-input
          use-chips
          multiple
          dense
          hide-dropdown-icon
          input-debounce="0"
          new-value-mode="add"
        />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-4">Default Timeout (seconds)</div>
        <q-input
          type="number"
          outlined
          dense
          class="col-8"
          v-model.number="script.default_timeout"
          :rules="[val => val >= 5 || 'Minimum is 5']"
        />
      </q-card-section>
      <q-card-actions>
        <q-space />
        <q-btn dense flat label="Cancel" v-close-popup />
        <q-btn dense flat label="Add" color="primary" type="submit" />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "ScriptModal",
  mixins: [mixins],
  props: {
    categories: !Array,
  },
  data() {
    return {
      script: {
        name: "",
        description: "",
        shell: "powershell",
        category: null,
        default_timeout: 90,
        args: [],
      },
      shellOptions: [
        { label: "Powershell", value: "powershell" },
        { label: "Batch (CMD)", value: "cmd" },
        { label: "Python", value: "python" },
      ],
      filterOptions: [],
    };
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let formData = new FormData();

      if (!!this.script.filename) {
        formData.append("filename", this.script.filename);
      }

      if (!!this.script.category) {
        formData.append("category", this.script.category);
      } else {
        formData.append("category", "");
      }

      formData.append("file_upload", true);
      formData.append("name", this.script.name);
      formData.append("shell", this.script.shell);
      formData.append("description", this.script.description);
      formData.append("default_timeout", this.script.default_timeout);
      formData.append("args", JSON.stringify(this.script.args));

      this.$axios
        .post("/scripts/scripts/", formData)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$emit("added");
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
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
};
</script>