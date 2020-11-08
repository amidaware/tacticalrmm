<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">{{ modalTitle }}</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="submit">
        <q-card-section v-if="op === 'edit' || op === 'delete'">
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select client"
            v-model="selected_client"
            :options="client_options"
          />
        </q-card-section>
        <q-card-section v-if="op === 'add'">
          <q-input
            outlined
            v-model="client.name"
            label="Client"
            :rules="[val => (val && val.length > 0) || '*Required']"
          />
        </q-card-section>
        <q-card-section v-if="op === 'add' || op === 'edit'">
          <q-input
            v-if="op === 'add'"
            :rules="[val => !!val || '*Required']"
            outlined
            v-model="client.site"
            label="Default first site"
          />
          <q-input
            v-else-if="op === 'edit'"
            :rules="[val => !!val || '*Required']"
            outlined
            v-model="client.name"
            label="Rename client"
          />
        </q-card-section>
        <q-card-actions align="left">
          <q-btn
            :label="capitalize(op)"
            :color="op === 'delete' ? 'negative' : 'primary'"
            type="submit"
            class="full-width"
          />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
export default {
  name: "ClientsForm",
  mixins: [mixins],
  props: {
    op: !String,
    clientpk: Number,
  },
  data() {
    return {
      client_options: [],
      selected_client: {},
      client: {
        id: null,
        name: "",
        site: "",
      },
    };
  },
  watch: {
    selected_client(newClient, oldClient) {
      this.client.id = newClient.value;
      this.client.name = newClient.label;
    },
  },
  computed: {
    modalTitle() {
      if (this.op === "add") return "Add Client";
      if (this.op === "edit") return "Edit Client";
      if (this.op === "delete") return "Delete Client";
    },
  },
  methods: {
    submit() {
      if (this.op === "add") this.addClient();
      if (this.op === "edit") this.editClient();
      if (this.op === "delete") this.deleteClient();
    },
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        this.client_options = r.data.map(client => ({ label: client.name, value: client.id }));

        if (this.clientpk !== undefined && this.clientpk !== null) {
          let client = this.client_options.find(client => client.value === this.clientpk);

          this.selected_client = client;
        } else {
          this.selected_client = this.client_options[0];
        }
      });
    },
    addClient() {
      this.$q.loading.show();
      const data = {
        client: this.client.name,
        site: this.client.site,
      };
      this.$axios
        .post("/clients/clients/", data)
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
    editClient() {
      this.$q.loading.show();
      const data = {
        id: this.client.id,
        name: this.client.name,
      };
      this.$axios
        .put(`/clients/${this.client.id}/client/`, this.client)
        .then(r => {
          this.$emit("edited");
          this.$emit("close");
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
    deleteClient() {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete client ${this.client.name}`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/clients/${this.client.id}/client/`)
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
    if (this.op !== "add") this.getClients();
  },
};
</script>