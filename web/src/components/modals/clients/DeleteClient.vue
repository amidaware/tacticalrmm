<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Delete Client</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="deleteClient">
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
        <q-card-section></q-card-section>
        <q-card-actions align="left">
          <q-btn
            :disable="client.client === null"
            :label="deleteLabel"
            class="full-width"
            color="negative"
            type="submit"
          />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
export default {
  name: "DeleteClient",
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
    deleteLabel() {
      return this.client.client !== null ? `Delete ${this.client.client}` : "Delete";
    },
  },
  methods: {
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        r.data.forEach(client => {
          this.clients.push({ label: client.client, value: client.id });
        });
      });
    },
    onChange() {
      this.client.client = this.clients.find(i => i.value === this.client.id).label;
    },
    deleteClient() {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete client ${this.client.client}`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$axios
            .delete(`/clients/${this.client.id}/client/`)
            .then(r => {
              this.$emit("edited");
              this.$emit("close");
              this.notifySuccess(r.data);
            })
            .catch(e => this.notifyError(e.response.data, 6000));
        });
    },
  },
  created() {
    this.getClients();
  },
};
</script>