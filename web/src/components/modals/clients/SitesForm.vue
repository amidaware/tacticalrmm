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
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select client"
            v-model="selected_client"
            :options="client_options"
            @input="op === 'edit' || op === 'delete' ? (selected_site = sites[0]) : () => {}"
          />
        </q-card-section>
        <q-card-section v-if="op === 'edit' || op === 'delete'">
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select site"
            v-model="selected_site"
            :options="sites"
          />
        </q-card-section>
        <q-card-section v-if="op === 'add' || op === 'edit'">
          <q-input
            v-if="op === 'add'"
            outlined
            v-model="site.name"
            label="Site"
            :rules="[val => !!val || '*Required']"
          />
          <q-input
            v-else-if="op === 'edit'"
            :rules="[val => !!val || '*Required']"
            outlined
            v-model="site.name"
            label="Rename site"
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
  name: "SitesForm",
  mixins: [mixins],
  props: {
    op: !String,
    sitepk: Number,
  },
  data() {
    return {
      client_options: [],
      selected_client: null,
      selected_site: null,
      site: {
        id: null,
        name: "",
      },
    };
  },
  watch: {
    selected_site(newSite, oldSite) {
      this.site.id = newSite.value;
      this.site.name = newSite.label;
    },
  },
  computed: {
    sites() {
      return !!this.selected_client ? this.formatSiteOptions(this.selected_client.sites) : [];
    },
    modalTitle() {
      if (this.op === "add") return "Add Site";
      if (this.op === "edit") return "Edit Site";
      if (this.op === "delete") return "Delete Site";
    },
  },
  methods: {
    submit() {
      if (this.op === "add") this.addSite();
      if (this.op === "edit") this.editSite();
      if (this.op === "delete") this.deleteSite();
    },
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        this.client_options = this.formatClientOptions(r.data);

        if (this.sitepk !== undefined && this.sitepk !== null) {
          this.client_options.forEach(client => {
            let site = client.sites.find(site => site.id === this.sitepk);

            if (site !== undefined) {
              this.selected_client = client;
              this.selected_site = { value: site.id, label: site.name };
            }
          });
        } else {
          this.selected_client = this.client_options[0];
          if (this.op !== "add") this.selected_site = this.sites[0];
        }
      });
    },
    addSite() {
      this.$q.loading.show();

      const data = {
        client: this.selected_client.value,
        name: this.site.name,
      };

      this.$axios
        .post("/clients/sites/", data)
        .then(() => {
          this.$emit("close");
          this.$store.dispatch("loadTree");
          this.$q.loading.hide();
          this.notifySuccess(`Site ${this.site.name} was added!`);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data.non_field_errors);
        });
    },
    editSite() {
      this.$q.loading.show();

      const data = {
        id: this.site.id,
        name: this.site.name,
        client: this.selected_client.value,
      };

      this.$axios
        .put(`/clients/${this.site.id}/site/`, data)
        .then(() => {
          this.$emit("edited");
          this.$emit("close");
          this.$q.loading.hide();
          this.notifySuccess("Site was edited");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data.non_field_errors);
        });
    },
    deleteSite() {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete site ${this.site.name}`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/clients/${this.site.id}/site/`)
            .then(r => {
              this.$emit("edited");
              this.$emit("close");
              this.$q.loading.hide();
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
  },
};
</script>