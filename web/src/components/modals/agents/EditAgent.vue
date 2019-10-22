<template>
  <q-card style="min-width: 450px">
    <q-card-section class="row items-center">
      <div class="text-h6">Edit {{ hostname }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-form @submit.prevent="editAgent">
      <q-card-section>
        <q-select
          @input="site = sites[0]"
          dense
          outlined
          v-model="client"
          :options="Object.keys(tree)"
          label="Client"
        />
      </q-card-section>
      <q-card-section>
        <q-select dense outlined v-model="site" :options="sites" label="Site" />
      </q-card-section>
      <q-card-section>
        <q-select dense outlined v-model="monType" :options="monTypes" label="Monitoring mode" />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          dense
          v-model="desc"
          label="Description"
          :rules="[val => !!val || '*Required']"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          v-model.number="pingInterval"
          label="Interval for ping checks (seconds)"
          :rules="[ 
                    val => !!val || '*Required',
                    val => val >= 60 || 'Minimum is 60 seconds',
                    val => val <= 3600 || 'Maximum is 3600 seconds'
                ]"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          v-model.number="overdueTime"
          label="Send an overdue alert if the server has not reported in after (minutes)"
          :rules="[ 
                    val => !!val || '*Required',
                    val => val >= 5 || 'Minimum is 5 minutes',
                    val => val < 9999999 || 'Maximum is 9999999 minutes'
                ]"
        />
      </q-card-section>
      <q-card-section>
        <q-checkbox v-model="emailAlert" label="Get overdue email alerts" />
        <q-space />
        <q-checkbox v-model="textAlert" label="Get overdue text alerts" />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn label="Save" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "EditAgent",
  mixins: [mixins],
  data() {
    return {
      pk: null,
      hostname: "",
      client: "",
      site: "",
      monType: "",
      monTypes: ["server", "workstation"],
      desc: "",
      overdueTime: null,
      pingInterval: null,
      emailAlert: null,
      textAlert: null,
      tree: {}
    };
  },
  methods: {
    getAgentInfo() {
      axios.get(`/agents/${this.selectedAgentPk}/agentdetail/`).then(r => {
        this.pk = r.data.id;
        this.hostname = r.data.hostname;
        this.client = r.data.client;
        this.site = r.data.site;
        this.monType = r.data.monitoring_type;
        this.desc = r.data.description;
        this.overdueTime = r.data.overdue_time;
        this.pingInterval = r.data.ping_check_interval;
        this.emailAlert = r.data.overdue_email_alert;
        this.textAlert = r.data.overdue_text_alert;
      });
    },
    getClientsSites() {
      axios.get("/clients/loadclients/").then(r => this.tree = r.data);
    },
    editAgent() {
      const data = {
        pk: this.pk,
        client: this.client,
        site: this.site,
        montype: this.monType,
        desc: this.desc,
        overduetime: this.overdueTime,
        pinginterval: this.pingInterval,
        emailalert: this.emailAlert,
        textalert: this.textAlert
      };
      axios
        .patch("/agents/editagent/", data)
        .then(r => {
          this.$emit("close");
          this.$emit("edited");
          this.notifySuccess("Agent was edited!");
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    sites() {
      return this.tree[this.client];
    }
  },
  created() {
    this.getAgentInfo();
    this.getClientsSites();
  }
};
</script>