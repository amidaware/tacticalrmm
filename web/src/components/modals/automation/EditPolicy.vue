<template>
  <q-card style="width: 60vw">
    <q-form @submit.prevent="editPolicy">
      <q-card-section class="row items-center">
        <div class="text-h6">Edit Policy</div>
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
          >
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">
                  No Results
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
          >
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">
                  No Results
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Agents:</div>
        <div class="col-10">
          <q-select
            v-model="selectedAgents"
            :options="agentOptions"
            filled
            multiple
            use-chips
          >
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">
                  No Results
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </div>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Edit" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "EditPolicy",
  mixins: [mixins],
  props: ["pk"],
  data() {
    return {
      name: "",
      desc: "",
      active: false,
      selectedAgents: [],
      selectedSites: [],
      selectedClients: [],
      clientOptions: [],
      siteOptions: [],
      agentOptions: [],
    };
  },
  methods: {
    getPolicy() {
      axios.get(`/automation/policies/${this.pk}/`).then(r => {

        this.name = r.data.name;
        this.desc = r.data.desc;
        this.active = r.data.active;
        this.selectedAgents = r.data.agents.map(agent => {
          return {
            label: agent.hostname,
            value: agent.pk
          }
        });
        this.selectedSites = r.data.sites.map(site => {
          return {
            label: site.site,
            value: site.id
          }
        });
        this.selectedClients = r.data.clients.map(client => {
          return {
            label: client.client,
            value: client.id
          }
        });
      });
    },
    editPolicy() {
      if (!this.name) {
        this.notifyError("Name is required!");
        return false;
      }

      this.$q.loading.show();
      
      let formData = {
        name: this.name,
        desc: this.desc,
        active: this.active,
        agents: this.selectedAgents.map(agent => agent.value),
        sites: this.selectedSites.map(site => site.value),
        clients: this.selectedClients.map(client => client.value)
      }

      axios.put(`/automation/policies/${this.pk}/`, formData)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$emit("edited");
          this.notifySuccess("Policy edited!");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
    getClients() {

      axios.get(`/clients/listclients/`).then(r => {
        this.clientOptions = r.data.map(client => {
          return {
            label: client.client,
            value: client.id
          }
        });
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError(e.response.data);
      });
    },
    getSites() {

      axios.get(`/clients/listsites/`).then(r => {
        this.siteOptions = r.data.map(site => {
          return {
            label: `${site.client_name}\\${site.site}`,
            value: site.id
          }
        });
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError(e.response.data);
      });
    },
    getAgents() {

      axios.get(`/agents/listagents/`).then(r => {
        this.agentOptions = r.data.map(agent => {
          return {
            label: `${agent.client}\\${agent.site}\\${agent.hostname}`,
            value: agent.pk
          }
        });
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError(e.response.data);
      });
    },
  },
  created() {
    this.getPolicy();
    this.getClients();
    this.getSites();
    this.getAgents();
  }
};
</script>