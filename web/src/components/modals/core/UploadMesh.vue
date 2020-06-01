<template>
  <q-card style="min-width: 40vw">
    <q-card-section class="row items-center">
      <div class="text-h6">Upload New Mesh Agent</div>
    </q-card-section>
    <q-form @submit.prevent="upload">
      <q-card-section>
        <div class="row">
          <q-file
            v-model="meshagent"
            :rules="[ val => !!val || '*Required' ]"
            label="Upload MeshAgent"
            stack-label
            filled
            counter
            accept=".exe"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
        </div>
      </q-card-section>
      <q-card-actions align="center">
        <q-btn label="Upload" color="primary" class="full-width" type="submit" />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "UploadMesh",
  mixins: [mixins],
  data() {
    return {
      meshagent: null
    };
  },
  methods: {
    upload() {
      let formData = new FormData();
      formData.append("meshagent", this.meshagent);
      axios
        .put("/core/uploadmesh/", formData)
        .then(() => {
          this.$q.loading.hide();
          this.$emit("close");
          this.notifySuccess("Uploaded successfully!");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Unable to upload");
        });
    }
  }
};
</script>