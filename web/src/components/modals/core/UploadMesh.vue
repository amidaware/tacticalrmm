<template>
  <q-card style="min-width: 40vw">
    <q-card-section class="row items-center">
      <div class="text-h6">Upload New Mesh Agent</div>
    </q-card-section>
    <q-form @submit.prevent="upload">
      <q-card-section>
        <div class="q-gutter-sm">
          <q-radio v-model="arch" val="64" label="64 bit" />
          <q-radio v-model="arch" val="32" label="32 bit" />
        </div>
      </q-card-section>
      <q-card-section>
        <div class="row">
          <q-file
            v-model="meshagent"
            :rules="[val => !!val || '*Required']"
            label="Upload MeshAgent"
            stack-label
            filled
            counter
            class="full-width"
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
import mixins from "@/mixins/mixins";

export default {
  name: "UploadMesh",
  mixins: [mixins],
  data() {
    return {
      meshagent: null,
      arch: "64",
    };
  },
  methods: {
    upload() {
      this.$q.loading.show({ message: "Uploading..." });
      let formData = new FormData();
      formData.append("arch", this.arch);
      formData.append("meshagent", this.meshagent);
      this.$axios
        .put("/core/uploadmesh/", formData)
        .then(() => {
          this.$q.loading.hide();
          this.$emit("close");
          this.notifySuccess("Uploaded successfully!");
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
  },
};
</script>