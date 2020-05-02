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
            label="Select client"
            v-model="clientPK"
            :options="clients"
            @input="clientChanged"
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            v-model="newName"
            label="Rename client"
          />
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
      clientPK: null,
      newName: null
    };
  },
  computed: {
    nameChanged() {
      if (this.clients.length !== 0) {
        const origName = this.clients.find(k => k.value === this.clientPK).label;
        return this.newName === origName ? false : true;
      }
    }
  },
  methods: {
    getClients() {
      axios.get("/clients/listclients/").then(r => {
        r.data.forEach(client => {
          this.clients.push({ label: client.client, value: client.id });
        });
        this.clientPK = this.clients.map(k => k.value)[0];
        this.newName = this.clients.map(k => k.label)[0];
      });
    },
    clientChanged() {
      this.newName = this.clients.find(k => k.value === this.clientPK).label;
    },
    editClient() {
      const data = {
        pk: this.clientPK,
        name: this.newName
      };
      axios
        .patch("/clients/editclient/", data)
        .then(() => {
          this.$emit("edited");
          this.$emit("close");
          this.notifySuccess("Client was edited");
        })
        .catch(e => this.notifyError(e.response.data));
    }
  },
  created() {
    this.getClients();
  }
};
</script>