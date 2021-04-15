<template>
  <q-card style="min-width: 85vh">
    <q-card-section class="row items-center">
      <div class="text-h6">Code Signing</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-form @submit.prevent="editToken">
      <q-card-section class="row">
        <div class="col-2">Token:</div>
        <div class="col-1"></div>
        <q-input
          outlined
          dense
          v-model="settings.token"
          class="col-9 q-pa-none"
          :rules="[val => !!val || 'Token is required']"
        />
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Save" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
export default {
  name: "CodeSign",
  mixins: [mixins],
  data() {
    return {
      settings: {
        token: "",
      },
    };
  },
  methods: {
    getToken() {
      this.$axios
        .get("/core/codesign/")
        .then(r => {
          this.settings = r.data;
        })
        .catch(e => this.notifyError(e.response.data));
    },
    editToken() {
      this.$q.loading.show();
      this.$axios
        .patch("/core/codesign/", this.settings)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
          this.$emit("close");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data, 4000);
        });
    },
  },
  created() {
    this.getToken();
  },
};
</script>