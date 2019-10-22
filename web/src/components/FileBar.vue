<template>
  <div class="q-pa-xs q-ma-xs">
    <q-bar>
      <div class="cursor-pointer non-selectable">
        File
        <q-menu>
          <q-list dense style="min-width: 100px">
            <q-item clickable v-close-popup @click="toggleAddClient = true">
              <q-item-section>Add Client</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="toggleAddSite = true">
              <q-item-section>Add Site</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="getLog">
              <q-item-section>Debug Log</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </div>
      <q-space />
      <!-- add client modal -->
      <q-dialog v-model="toggleAddClient">
        <q-card style="min-width: 400px">
          <q-card-section class="row">
            <q-card-actions align="left">
              <div class="text-h6">Add Client</div>
            </q-card-actions>
            <q-space />
            <q-card-actions align="right">
              <q-btn v-close-popup flat round dense icon="close" />
            </q-card-actions>
          </q-card-section>
          <q-card-section>
            <q-form @submit.prevent="addClient">
              <q-card-section>
                <q-input
                  outlined
                  v-model="addClientClient"
                  label="Client:"
                  :rules="[ val => val && val.length > 0 || 'This field is required']"
                />
              </q-card-section>
              <q-card-section>
                <q-input
                  outlined
                  v-model="defaultSite"
                  label="Default first site:"
                  :rules="[ val => val && val.length > 0 || 'This field is required']"
                />
              </q-card-section>
              <q-card-actions align="right">
                <q-btn label="Cancel" color="red-4" v-close-popup />
                <q-btn label="Add Client" color="positive" type="submit" />
              </q-card-actions>
            </q-form>
          </q-card-section>
        </q-card>
      </q-dialog>
      <!-- add site modal -->
      <q-dialog v-model="toggleAddSite">
        <q-card style="min-width: 400px">
          <q-card-section class="row">
            <q-card-actions align="left">
              <div class="text-h6">Add Site</div>
            </q-card-actions>
            <q-space />
            <q-card-actions align="right">
              <q-btn v-close-popup flat round dense icon="close" />
            </q-card-actions>
          </q-card-section>
          <q-card-section>
            <q-form @submit.prevent="addSite">
              <q-card-section>
                <q-select outlined v-model="addSiteClient" :options="Object.keys(clients)" />
              </q-card-section>
              <q-card-section>
                <q-input
                  outlined
                  v-model="defaultSiteSite"
                  label="Site Name:"
                  :rules="[ val => val && val.length > 0 || 'This field is required']"
                />
              </q-card-section>
              <q-card-actions align="right">
                <q-btn label="Cancel" color="red-4" v-close-popup />
                <q-btn label="Add Site" color="positive" type="submit" />
              </q-card-actions>
            </q-form>
          </q-card-section>
        </q-card>
      </q-dialog>
      <LogModal />
    </q-bar>
  </div>
</template>

<script>
import axios from "axios";
import LogModal from "@/components/modals/logs/LogModal";
export default {
  name: "FileBar",
  components: { LogModal },
  props: ["clients"],
  data() {
    return {
      toggleAddClient: false,
      toggleAddSite: false,
      addClientClient: "",
      addSiteClient: "",
      defaultSite: "",
      defaultSiteSite: ""
    };
  },
  methods: {
    getLog() {
      this.$store.commit("logs/TOGGLE_LOG_MODAL", true);
    },
    loadFirstClient() {
      axios.get("/clients/listclients/").then(resp => {
        this.addSiteClient = resp.data.map(k => k.client)[0];
      });
    },
    addClient() {
      return axios
        .post("/clients/addclient/", {
          client: this.addClientClient,
          site: this.defaultSite
        })
        .then(() => {
          this.toggleAddClient = false;
          this.$store.dispatch("loadTree");
          this.$store.dispatch("getUpdatedSites");
          this.$q.notify({
            color: "green",
            icon: "fas fa-check-circle",
            message: `Client ${this.addClientClient} was added!`
          });
        })
        .catch(err => {
          this.$q.notify({
            color: "red",
            icon: "fas fa-times-circle",
            message: err.response.data.error
          });
        });
    },
    addSite() {
      axios
        .post("/clients/addsite/", {
          client: this.addSiteClient,
          site: this.defaultSiteSite
        })
        .then(() => {
          this.toggleAddSite = false;
          this.$store.dispatch("loadTree");
          this.$q.notify({
            color: "green",
            icon: "fas fa-check-circle",
            message: `Site ${this.defaultSiteSite} was added!`
          });
        })
        .catch(err => {
          this.$q.notify({
            color: "red",
            icon: "fas fa-times-circle",
            message: err.response.data.error
          });
        });
    }
  },
  created() {
    this.loadFirstClient();
  }
};
</script>
