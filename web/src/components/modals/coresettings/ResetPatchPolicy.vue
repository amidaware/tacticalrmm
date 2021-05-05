<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="min-width: 400px">
      <q-bar>
        Reset Agent Patch Policy
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <div class="text-subtitle3">
          Reset the patch policies for agents in a specific client or site. You can also leave the client and site blank
          to reset the patch policy for all agents. (This might take a while)
        </div>
        <q-form @submit.prevent="submit">
          <q-card-section>
            <q-select
              label="Clients"
              @clear="clearClient"
              clearable
              options-dense
              outlined
              v-model="client"
              :options="client_options"
            />
          </q-card-section>
          <q-card-section>
            <q-select
              :disabled="client === null"
              @clear="clearSite"
              label="Sites"
              clearable
              options-dense
              outlined
              v-model="site"
              :options="site_options"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn :label="buttonText" color="primary" type="submit" />
            <q-btn label="Cancel" v-close-popup />
          </q-card-actions>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "ResetPatchPolicy",
  mixins: [mixins],
  data() {
    return {
      client: null,
      site: null,
      client_options: [],
    };
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let data = {};

      if (this.client !== null) {
        data.client = this.client.value;
      }

      if (this.site !== null) {
        data.site = this.site.value;
      }

      this.$axios
        .patch("automation/winupdatepolicy/reset/", data)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess("The agent policies were reset successfully!");
          this.onOk();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    getClients() {
      this.$store.dispatch("loadClients").then(r => {
        this.client_options = this.formatClientOptions(r.data);
      });
    },
    clearClient() {
      this.client = null;
      this.site = null;
    },
    clearSite() {
      this.site = null;
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
    onOk() {
      this.$emit("ok");
      this.hide();
    },
  },
  computed: {
    site_options() {
      return !!this.client ? this.formatSiteOptions(this.client.sites) : [];
    },
    buttonText() {
      return !this.client ? "Clear Policies for ALL Agents" : "Clear Policies";
    },
  },
  mounted() {
    this.getClients();
  },
};
</script>