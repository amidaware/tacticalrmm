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
      <q-form @submit.prevent="editClient">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select client"
            v-model="client.id"
            :options="clients"
            @input="onChange"
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-section>
          <q-input :rules="[val => !!val || '*Required']" outlined v-model="client.client" label="Rename client" />
        </q-card-section>
        <q-card-actions align="left">
          <q-btn :disable="!nameChanged" label="Save" color="primary" type="submit" />
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
  data() {
    return {
      clients: [],
      client: {
        client: null,
        id: null,
      },
    };
  },
  computed: {
    nameChanged() {
      if (this.clients.length !== 0 && this.client.client !== null) {
        const origName = this.clients.find(i => i.value === this.client.id).label;
        return this.client.client === origName ? false : true;
      }
    },
  },
  methods: {
    getClients() {
      axios.get("/clients/clients/").then(r => {
        r.data.forEach(client => {
          this.clients.push({ label: client.client, value: client.id });
        });
        this.clients.sort((a, b) => a.label.localeCompare(b.label));
      });
    },
    onChange() {
      this.client.client = this.clients.find(i => i.value === this.client.id).label;
    },
    editClient() {
      axios
        .patch(`/clients/${this.client.id}/client/`, this.client)
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