<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Add Site</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="addSite">
        <q-card-section>
          <q-select options-dense outlined v-model="clientName" :options="Object.keys(clients).sort()" />
        </q-card-section>
        <q-card-section>
          <q-input
            outlined
            v-model="siteName"
            label="Site Name:"
            :rules="[val => (val && val.length > 0) || 'This field is required']"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Add Site" color="primary" type="submit" />
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
  name: "AddSite",
  props: ["clients"],
  mixins: [mixins],
  data() {
    return {
      clientName: "",
      siteName: "",
    };
  },
  methods: {
    loadFirstClient() {
      axios.get("/clients/listclients/").then(resp => {
        this.clientName = resp.data.map(k => k.client).sort()[0];
      });
    },
    addSite() {
      axios
        .post("/clients/addsite/", {
          client: this.clientName,
          site: this.siteName,
        })
        .then(() => {
          this.$emit("close");
          this.$store.dispatch("loadTree");
          this.notifySuccess(`Site ${this.siteName} was added!`);
        })
        .catch(err => this.notifyError(err.response.data.error));
    },
  },
  created() {
    this.loadFirstClient();
  },
};
</script>