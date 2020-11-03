<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Edit Sites</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="editSite">
        <q-card-section v-if="tree !== null">
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
          />
        </q-card-section>
        <q-card-section>
          <q-input :rules="[val => !!val || '*Required']" outlined v-model="site.label" label="Rename site" />
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
  name: "EditSites",
  mixins: [mixins],
  props: {
    sitepk: Number,
  },
  data() {
    return {
      client_options: [],
      client: null,
      site: {},
    };
  },
  computed: {
    sites() {
      return !!this.client ? this.client.sites(site => ({ label: site.name, value: site.id })) : [];
    },
  },
  methods: {
    getClients() {
      axios.get("/clients/clients/").then(r => {
        this.client_options = this.formatClientoptions(r.data);

        if (this.sitepk !== undefined && this.sitepk !== null) {
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
    editSite() {
      const data = {
        id: this.site.value,
        name: this.site.label,
      };
      axios
        .put(`/clients/${this.site.value}/site/`, data)
        .then(() => {
          this.$emit("edited");
          this.$emit("close");
          this.notifySuccess("Site was edited");
        })
        .catch(e => this.notifyError(e.response.data));
    },
  },
  created() {
    this.getClients();
  },
};
</script>