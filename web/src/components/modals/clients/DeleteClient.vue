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
      <q-form @submit="deleteClient">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select client"
            v-model="client"
            :options="client_options"
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-section></q-card-section>
        <q-card-actions align="left">
          <q-btn :disable="client === null" label="Delete" class="full-width" color="negative" type="submit" />
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
  props: {
    clientpk: Number,
  },
  data() {
    return {
      client_options: [],
      client: null,
    };
  },
  methods: {
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        this.client_options = r.data.map(client => ({ label: client.name, value: client.id }));
      });
    },
    deleteClient() {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: "Delete client",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/clients/${this.client}/client/`)
            .then(r => {
              this.$q.loading.hide();
              this.$emit("edited");
              this.$emit("close");
              this.notifySuccess(r.data);
            })
            .catch(e => {
              this.$q.loading.hide();
              this.notifyError(e.response.data, 6000);
            });
        });
    },
  },
  created() {
    this.getClients();

    if (this.clientpk !== undefined && this.clientpk !== null) {
      this.client = this.clientpk;
    }
  },
};
</script>