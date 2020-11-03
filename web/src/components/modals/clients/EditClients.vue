<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Edit Clients</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit="editClient">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select client"
            v-model="client"
            :options="client_options"
          />
        </q-card-section>
        <q-card-section>
          <q-input :rules="[val => !!val || '*Required']" outlined v-model="client.label" label="Rename client" />
        </q-card-section>
        <q-card-actions align="left">
          <q-btn label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "EditClients",
  mixins: [mixins],
  props: {
    clientpk: Number,
  },
  data() {
    return {
      client_options: [],
      client: {},
    };
  },
  methods: {
    getClients() {
      axios.get("/clients/clients/").then(r => {
        this.client_options = r.data.map(client => ({ label: client.name, value: client.id }));

        if (this.clientpk !== undefined && this.clientpk !== null) {
          let client = this.client_options.find(client => client.value === this.clientpk);

          this.client = client;
        } else {
          this.client = this.client_options[0];
        }
      });
    },
    editClient() {
      const data = {
        id: this.client.value,
        name: this.client.label,
      };
      axios
        .put(`/clients/${this.client.value}/client/`, data)
        .then(r => {
          this.$emit("edited");
          this.$emit("close");
          this.notifySuccess(r.data);
        })
        .catch(e => {
          if (e.response.data.client) {
            this.notifyError(e.response.data.client);
          } else {
            this.notifyError(e.response.data.non_field_errors);
          }
        });
    },
  },
  created() {
    this.getClients();
  },
};
</script>