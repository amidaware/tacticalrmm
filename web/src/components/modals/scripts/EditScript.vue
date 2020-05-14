<template>
  <q-card style="width: 40vw">
    <q-form @submit.prevent="editScript">
      <q-card-section class="row items-center">
        <div class="text-h6">Edit Script</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Name:</div>
        <div class="col-10">
          <q-input outlined dense v-model="name" :rules="[ val => !!val || '*Required']" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Description:</div>
        <div class="col-10">
          <q-input outlined dense v-model="desc" type="textarea" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">File Upload:</div>
        <div class="col-10">
          <q-file
            v-model="script"
            label="Upload new script version"
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
          dense
          class="col-10"
          outlined
          v-model="shell"
          :options="shellOptions"
          emit-value
          map-options
          :rules="[ val => !!val || '*Required']"
        />
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Edit" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "EditScript",
  mixins: [mixins],
  props: ["pk"],
  data() {
    return {
      name: null,
      desc: null,
      shell: null,
      script: null,
      shellOptions: [
        { label: "Powershell", value: "powershell" },
        { label: "Batch (CMD)", value: "cmd" },
        { label: "Python", value: "python" }
      ]
    };
  },
  methods: {
    getScript() {
      axios.get(`/checks/getscript/${this.pk}/`).then(r => {
        this.name = r.data.name;
        this.desc = r.data.description;
        this.shell = r.data.shell;
      });
    },
    editScript() {
      if (!this.name || !this.shell) {
        this.notifyError("Name and Type are required!");
        return false;
      }

      this.$q.loading.show();
      let formData = new FormData();
      if (this.script) {
        formData.append("script", this.script);
      }
      formData.append("pk", this.pk);
      formData.append("name", this.name);
      formData.append("shell", this.shell);
      formData.append("desc", this.desc);
      axios
        .put(`/checks/editscript/`, formData)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$emit("edited");
          this.notifySuccess("Script edited!");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    }
  },
  created() {
    this.getScript();
  }
};
</script>