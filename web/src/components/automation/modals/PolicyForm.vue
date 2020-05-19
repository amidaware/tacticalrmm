<template>
  <q-card style="width: 60vw">
    <q-form ref="form" @submit="submit">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ title }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Name:</div>
        <div class="col-10">
          <q-input outlined dense v-model="name" :rules="[ val => !!val || '*Required']" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Description:</div>
        <div class="col-10">
          <q-input outlined dense v-model="desc" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Active:</div>
        <div class="col-10">
          <q-toggle v-model="active" color="green" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Clients:</div>
        <div class="col-10">
          <q-select 
            v-model="selectedClients" 
            :options="clientOptions" 
            filled 
            multiple 
            use-chips
            options-selected-class="text-green"
          >
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">No Results</q-item-section>
              </q-item>
            </template>
            <template v-slot:option="props">
              <q-item
                v-bind="props.itemProps"
                v-on="props.itemEvents"
              >
                <q-item-section avatar>
                  <q-icon v-if="props.selected" name="check" />
                </q-item-section>
                <q-item-section>
                  <q-item-label v-html="props.opt.label" />
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Sites:</div>
        <div class="col-10">
          <q-select 
            v-model="selectedSites" 
            :options="siteOptions" 
            filled 
            multiple 
            use-chips
            options-selected-class="text-green"
          >
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">No Results</q-item-section>
              </q-item>
            </template>
            <template v-slot:option="props">
              <q-item
                v-bind="props.itemProps"
                v-on="props.itemEvents"
              >
                <q-item-section avatar>
                  <q-icon v-if="props.selected" name="check" />
                </q-item-section>
                <q-item-section>
                  <!-- <q-item-label overline>{{ props.opt.client }}</q-item-label> -->
                  <q-item-label v-html="props.opt.label" />
                  <q-item-label caption>{{ props.opt.client }}</q-item-label>
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </div>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn :label="title" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
import dropdown_formatter from "@/mixins/dropdown_formatter";

export default {
  name: "PolicyForm",
  mixins: [mixins, dropdown_formatter],
  props: { pk: Number },
  data() {
    return {
      name: "",
      desc: "",
      active: false,
      selectedSites: [],
      selectedClients: [],
      clientOptions: [],
      siteOptions: []
    };
  },
  computed: {
    title() {
      return this.pk ? "Edit Policy" : "Add Policy";
    }
  },
  methods: {
    getPolicy() {
      this.$q.loading.show();

      this.$store
        .dispatch("automation/loadPolicy", this.pk)
        .then(r => {

          this.$q.loading.hide();
          
          this.name = r.data.name;
          this.desc = r.data.desc;
          this.active = r.data.active;
          this.selectedSites = r.data.sites.map(site => ({
            label: site.site,
            value: site.id
          }) );
          this.selectedClients = r.data.clients.map(client => ({
            label: client.client,
            value: client.id
          }) );
        });
    },
    submit() {
      if (!this.name) {
        this.notifyError("Name is required!");
        return false;
      }

      this.$q.loading.show();

      let formData = {
        id: this.pk,
        name: this.name,
        desc: this.desc,
        active: this.active,
        sites: this.selectedSites.map(site => site.value),
        clients: this.selectedClients.map(client => client.value)
      };

      if (this.pk) {
        this.$store
          .dispatch("automation/editPolicy", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.$emit("refresh");
            this.notifySuccess("Policy edited!");
          })
          .catch(e => {
            this.$q.loading.hide();
            this.notifyError(e.response.data);
          });
      } else {
        this.$store
          .dispatch("automation/addPolicy", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.$emit("refresh");
            this.notifySuccess("Policy added! Now you can add Tasks and Checks!");
          })
          .catch(e => {
            this.$q.loading.hide();
            this.notifyError(e.response.data);
          });
      }
    },
    getClients() {
      this.$store
        .dispatch("loadClients")
        .then(r => {
          this.clientOptions = this.formatClients(r.data);
        });
    },
    getSites() {
      this.$store
        .dispatch("loadSites")
        .then(r => {
          this.siteOptions = this.formatSites(r.data);
        });
    }
  },
  mounted() {
    // If pk prop is set that means we are editting
    if (this.pk) {
      this.getPolicy();
    }

    this.getClients();
    this.getSites();
  }
};
</script>