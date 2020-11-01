<template>
  <q-card style="min-width: 800px" v-if="agentLoaded && clientsLoaded">
    <q-splitter v-model="splitterModel">
      <template v-slot:before>
        <q-tabs dense v-model="tab" vertical class="text-primary">
          <q-tab name="general" label="General" />
          <q-tab name="patch" label="Patches" />
        </q-tabs>
      </template>
      <template v-slot:after>
        <q-form @submit.prevent="editAgent">
          <q-card-section class="row items-center">
            <div class="text-h6">Edit {{ agent.hostname }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-scroll-area :thumb-style="thumbStyle" style="height: 500px">
            <q-tab-panels v-model="tab" animated transition-prev="jump-up" transition-next="jump-up">
              <!-- general -->
              <q-tab-panel name="general">
                <q-card-section class="row">
                  <div class="col-2">Client:</div>
                  <div class="col-2"></div>
                  <q-select
                    @input="agent.site = sites[0]"
                    dense
                    options-dense
                    outlined
                    v-model="agent.client"
                    :options="Object.keys(tree).sort()"
                    class="col-8"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Site:</div>
                  <div class="col-2"></div>
                  <q-select class="col-8" dense options-dense outlined v-model="agent.site" :options="sites" />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Type:</div>
                  <div class="col-2"></div>
                  <q-select
                    dense
                    options-dense
                    outlined
                    v-model="agent.monitoring_type"
                    :options="monTypes"
                    class="col-8"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Description:</div>
                  <div class="col-2"></div>
                  <q-input
                    outlined
                    dense
                    v-model="agent.description"
                    class="col-8"
                    :rules="[val => !!val || '*Required']"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Timezone:</div>
                  <div class="col-2"></div>
                  <q-select outlined dense options-dense v-model="timezone" :options="allTimezones" class="col-8" />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-10">Check interval:</div>
                  <q-input
                    dense
                    type="number"
                    filled
                    label="Seconds"
                    v-model.number="agent.check_interval"
                    class="col-2"
                    :rules="[
                      val => !!val || '*Required',
                      val => val >= 60 || 'Minimum is 60 seconds',
                      val => val <= 3600 || 'Maximum is 3600 seconds',
                    ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-10">Send an overdue alert if the server has not reported in after:</div>
                  <q-input
                    dense
                    type="number"
                    filled
                    label="Minutes"
                    v-model.number="agent.overdue_time"
                    class="col-2"
                    :rules="[
                      val => !!val || '*Required',
                      val => val >= 5 || 'Minimum is 5 minutes',
                      val => val < 9999999 || 'Maximum is 9999999 minutes',
                    ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <q-checkbox v-model="agent.overdue_email_alert" label="Get overdue email alerts" />
                  <q-checkbox v-model="agent.overdue_text_alert" label="Get overdue sms alerts" />
                </q-card-section>
              </q-tab-panel>
              <!-- patch -->
              <q-tab-panel name="patch">
                <PatchPolicyForm :agent="agent" />
              </q-tab-panel>
            </q-tab-panels>
          </q-scroll-area>
          <q-card-section class="row items-center">
            <q-btn label="Save" color="primary" type="submit" />
            <q-btn label="Cancel" v-close-popup />
          </q-card-section>
        </q-form>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import PatchPolicyForm from "@/components/modals/agents/PatchPolicyForm";

export default {
  name: "EditAgent",
  components: { PatchPolicyForm },
  mixins: [mixins],
  data() {
    return {
      agentLoaded: false,
      clientsLoaded: false,
      agent: {},
      monTypes: ["server", "workstation"],
      tree: {},
      splitterModel: 15,
      tab: "general",
      timezone: null,
      tz_inherited: true,
      original_tz: null,
      allTimezones: [],
      thumbStyle: {
        right: "2px",
        borderRadius: "5px",
        backgroundColor: "#027be3",
        width: "5px",
        opacity: 0.75,
      },
    };
  },
  methods: {
    getAgentInfo() {
      axios.get(`/agents/${this.selectedAgentPk}/agenteditdetails/`).then(r => {
        this.agent = r.data;
        this.allTimezones = Object.freeze(r.data.all_timezones);

        // r.data.time_zone is the actual db column from the agent
        // r.data.timezone is a computed property based on the db time_zone field
        // which whill return null if the time_zone field is not set
        // and is therefore inheriting from the default global setting
        if (r.data.time_zone === null) {
          this.timezone = r.data.timezone;
          this.original_tz = r.data.timezone;
        } else {
          this.tz_inherited = false;
          this.timezone = r.data.time_zone;
          this.original_tz = r.data.time_zone;
        }

        this.agentLoaded = true;
      });
    },
    getClientsSites() {
      axios.get("/clients/loadclients/").then(r => {
        this.tree = r.data;
        this.clientsLoaded = true;
      });
    },
    editAgent() {
      let data = this.agent;

      // only send the timezone data if it has changed
      // this way django will keep the db column as null and inherit from the global setting
      // until we explicity change the agent's timezone
      if (this.timezone !== this.original_tz) {
        data.time_zone = this.timezone;
      }

      delete data.all_timezones;

      axios
        .patch("/agents/editagent/", data)
        .then(r => {
          this.$emit("close");
          this.$emit("edited");
          this.notifySuccess("Agent was edited!");
        })
        .catch(() => this.notifyError("Something went wrong"));
    },
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    sites() {
      if (this.agentLoaded && this.clientsLoaded) {
        return this.tree[this.agent.client].sort();
      }
    },
  },
  created() {
    this.getAgentInfo();
    this.getClientsSites();
  },
};
</script>