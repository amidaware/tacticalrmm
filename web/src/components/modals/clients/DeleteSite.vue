<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Delete Site</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="deleteSite">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select client"
            v-model="client"
            :options="client_options"
            @input="site = sites[0]"
          />
        </q-card-section>
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select site"
            v-model="site"
            :options="sites"
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-actions align="left">
          <q-btn :disable="site === null" label="Delete" class="full-width" color="negative" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
export default {
  name: "DeleteSite",
  mixins: [mixins],
  props: {
    sitepk: Number,
  },
  data() {
    return {
      client_options: [],
      client: null,
      site: null,
    };
  },
  computed: {
    sites() {
      return !!this.client ? this.client.sites.map(site => ({ label: site.name, value: site.id })) : [];
    },
  },
  methods: {
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        this.client_options = this.formatClientOptions(r.data);

        if (this.sitepk !== null && this.sitepk !== undefined) {
          this.client_options.forEach(client => {
            let site = client.sites.find(site => (site.id = this.sitepk));

            if (site !== undefined) {
              this.site = site.id;
              this.client = client;
            }
          });
        } else {
          this.client = this.client_options[0];
        }
      });
    },
    deleteSite() {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: "Delete site",
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$axios
            .delete(`/clients/${this.site}/site/`)
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