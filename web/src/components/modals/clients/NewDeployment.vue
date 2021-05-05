<template>
  <q-card style="min-width: 25vw">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Create a Deployment</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="create">
        <q-card-section class="q-gutter-sm">
          <q-select
            outlined
            dense
            options-dense
            label="Client"
            v-model="client"
            :options="client_options"
            @input="site = sites[0].value"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-select dense options-dense outlined label="Site" v-model="site" :options="sites" map-options emit-value />
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-sm">
            <q-radio v-model="agenttype" val="server" label="Server" @input="power = false" />
            <q-radio v-model="agenttype" val="workstation" label="Workstation" />
          </div>
        </q-card-section>
        <q-card-section>
          Expiry
          <div class="q-gutter-sm">
            <q-input filled v-model="datetime">
              <template v-slot:prepend>
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy transition-show="scale" transition-hide="scale">
                    <q-date v-model="datetime" mask="YYYY-MM-DD HH:mm" />
                  </q-popup-proxy>
                </q-icon>
              </template>

              <template v-slot:append>
                <q-icon name="access_time" class="cursor-pointer">
                  <q-popup-proxy transition-show="scale" transition-hide="scale">
                    <q-time v-model="datetime" mask="YYYY-MM-DD HH:mm" />
                  </q-popup-proxy>
                </q-icon>
              </template>
            </q-input>
          </div>
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-sm">
            <q-checkbox v-model="rdp" dense label="Enable RDP" />
            <q-checkbox v-model="ping" dense label="Enable Ping" />
            <q-checkbox v-model="power" dense v-show="agenttype === 'workstation'" label="Disable sleep/hibernate" />
          </div>
        </q-card-section>
        <q-card-section>
          OS
          <div class="q-gutter-sm">
            <q-radio v-model="arch" val="64" label="64 bit" />
            <q-radio v-model="arch" val="32" label="32 bit" />
          </div>
        </q-card-section>
        <q-card-actions align="left">
          <q-btn label="Create" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
import { date } from "quasar";

export default {
  name: "NewDeployment",
  mixins: [mixins],
  data() {
    return {
      client_options: [],
      datetime: null,
      client: null,
      site: null,
      agenttype: "server",
      power: false,
      rdp: false,
      ping: false,
      arch: "64",
    };
  },
  methods: {
    create() {
      const data = {
        client: this.client.value,
        site: this.site,
        expires: this.datetime,
        agenttype: this.agenttype,
        power: this.power ? 1 : 0,
        rdp: this.rdp ? 1 : 0,
        ping: this.ping ? 1 : 0,
        arch: this.arch,
      };
      this.$axios
        .post("/clients/deployments/", data)
        .then(r => {
          this.$emit("close");
          this.$emit("added");
          this.notifySuccess("Deployment added");
        })
        .catch(e => {});
    },
    getCurrentDate() {
      let d = new Date();
      d.setDate(d.getDate() + 30);
      this.datetime = date.formatDate(d, "YYYY-MM-DD HH:mm");
    },
    getClients() {
      this.$q.loading.show();
      this.$axios
        .get("/clients/clients/")
        .then(r => {
          this.client_options = this.formatClientOptions(r.data);
          this.client = this.client_options[0];
          this.site = this.formatSiteOptions(this.client.sites)[0].value;
          this.$q.loading.hide();
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
  },
  computed: {
    sites() {
      return this.client !== null ? this.formatSiteOptions(this.client.sites) : [];
    },
  },
  created() {
    this.getCurrentDate();
    this.getClients();
  },
};
</script>