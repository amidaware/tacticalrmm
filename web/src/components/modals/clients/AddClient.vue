<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Add Client</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="addClient">
        <q-card-section>
          <q-input
            outlined
            v-model="client.client"
            label="Client:"
            :rules="[val => (val && val.length > 0) || '*Required']"
          />
        </q-card-section>
        <q-card-section>
          <q-input
            outlined
            v-model="client.site"
            label="Default first site:"
            :rules="[val => (val && val.length > 0) || '*Required']"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Add Client" color="primary" type="submit" />
          <q-btn label="Cancel" v-close-popup />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "AddClient",
  mixins: [mixins],
  data() {
    return {
      client: {
        client: null,
        site: null,
      },
    };
  },
  methods: {
    addClient() {
      this.$q.loading.show();

      axios
        .post("/clients/clients/", this.client)
        .then(r => {
          this.$emit("close");
          this.$store.dispatch("loadTree");
          this.$store.dispatch("getUpdatedSites");
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
          if (e.response.data.client) {
            this.notifyError(e.response.data.client);
          } else {
            this.notifyError(e.response.data.non_field_errors);
          }
        });
    },
  },
};
</script>