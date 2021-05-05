<template>
  <q-card style="min-width: 85vh">
    <q-card-section class="row items-center">
      <div class="text-h6">Code Signing</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section class="row">
      <q-btn
        :disable="!settings.token"
        label="Code sign all agents"
        color="positive"
        class="full-width"
        @click="doCodeSign"
      >
        <q-tooltip>Force all existing agents to be updated to the code-signed version</q-tooltip>
      </q-btn>
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
        .catch(e => {});
    },
    editToken() {
      this.$q.loading.show();
      this.$axios
        .patch("/core/codesign/", this.settings)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    doCodeSign() {
      this.$q.loading.show();
      this.$axios
        .post("/core/codesign/")
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
  },
  created() {
    this.getToken();
  },
};
</script>