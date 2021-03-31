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
          <div class="scroll" style="max-height: 65vh">
            <q-tab-panels v-model="tab" animated transition-prev="jump-up" transition-next="jump-up">
              <!-- general -->
              <q-tab-panel name="general">
                <q-card-section class="row">
                  <div class="col-2">Client:</div>
                  <div class="col-2"></div>
                  <q-select
                    @input="agent.site = site_options[0].value"
                    dense
                    options-dense
                    outlined
                    v-model="agent.client"
                    :options="client_options"
                    class="col-8"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Site:</div>
                  <div class="col-2"></div>
                  <q-select
                    class="col-8"
                    dense
                    options-dense
                    emit-value
                    map-options
                    outlined
                    v-model="agent.site"
                    :options="site_options"
                  />
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
                  <div class="col-10">Run checks every:</div>
                  <q-input
                    dense
                    type="number"
                    filled
                    label="Seconds"
                    v-model.number="agent.check_interval"
                    class="col-2"
                    :rules="[
                      val => !!val || '*Required',
                      val => val >= 15 || 'Minimum is 15 seconds',
                      val => val <= 86400 || 'Maximum is 86400 seconds',
                    ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-10">
                    <q-icon class="q-pr-sm" name="fas fa-signal" size="1.2em" color="warning" /> Mark an agent as
                    <span class="text-weight-bold">offline</span> if it has not checked in after:
                  </div>
                  <q-input
                    dense
                    type="number"
                    filled
                    label="Minutes"
                    v-model.number="agent.offline_time"
                    class="col-2"
                    :rules="[
                      val => !!val || '*Required',
                      val => val >= 2 || 'Minimum is 2 minutes',
                      val => val < 9999999 || 'Maximum is 9999999 minutes',
                    ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-10">
                    <q-icon class="q-pr-sm" name="fas fa-signal" size="1.2em" color="negative" /> Mark an agent as
                    <span class="text-weight-bold">overdue</span> if it has not checked in after:
                  </div>
                  <q-input
                    dense
                    type="number"
                    filled
                    label="Minutes"
                    v-model.number="agent.overdue_time"
                    class="col-2"
                    :rules="[
                      val => !!val || '*Required',
                      val => val >= 3 || 'Minimum is 3 minutes',
                      val => val < 9999999 || 'Maximum is 9999999 minutes',
                    ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <q-checkbox v-model="agent.overdue_email_alert" label="Get overdue email alerts" />
                  <q-checkbox v-model="agent.overdue_text_alert" label="Get overdue sms alerts" />
                </q-card-section>
                <div class="text-h6">Custom Fields</div>
                <q-card-section v-for="field in customFields" :key="field.id">
                  <CustomField v-model="custom_fields[field.name]" :field="field" />
                </q-card-section>
              </q-tab-panel>
              <!-- patch -->
              <q-tab-panel name="patch">
                <PatchPolicyForm :agent="agent" />
              </q-tab-panel>
            </q-tab-panels>
          </div>
          <q-card-section class="row items-center">
            <q-btn label="Save" color="primary" type="submit" />
          </q-card-section>
        </q-form>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import PatchPolicyForm from "@/components/modals/agents/PatchPolicyForm";
import CustomField from "@/components/CustomField";

export default {
  name: "EditAgent",
  components: { PatchPolicyForm, CustomField },
  mixins: [mixins],
  data() {
    return {
      customFields: [],
      custom_fields: {},
      agentLoaded: false,
      clientsLoaded: false,
      agent: {},
      monTypes: ["server", "workstation"],
      client_options: [],
      splitterModel: 15,
      tab: "general",
      timezone: null,
      tz_inherited: true,
      original_tz: null,
      allTimezones: [],
    };
  },
  methods: {
    getAgentInfo() {
      this.$axios.get(`/agents/${this.selectedAgentPk}/agenteditdetails/`).then(r => {
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

        this.agent.client = { label: r.data.client.name, id: r.data.client.id, sites: r.data.client.sites };
        this.agentLoaded = true;

        for (let field of this.customFields) {
          const value = r.data.custom_fields.find(value => value.field === field.id);

          if (field.type === "multiple") {
            if (value) this.$set(this.custom_fields, field.name, value.value);
            else this.$set(this.custom_fields, field.name, []);
          } else if (field.type === "checkbox") {
            if (value) this.$set(this.custom_fields, field.name, value.value);
            else this.$set(this.custom_fields, field.name, false);
          } else {
            if (value) this.$set(this.custom_fields, field.name, value.value);
            else this.$set(this.custom_fields, field.name, "");
          }
        }
      });
    },
    getClientsSites() {
      this.$axios.get("/clients/clients/").then(r => {
        this.client_options = this.formatClientOptions(r.data);
        this.clientsLoaded = true;
      });
    },
    editAgent() {
      delete this.agent.all_timezones;
      delete this.agent.client;
      delete this.agent.sites;
      delete this.agent.timezone;
      delete this.agent.winupdatepolicy[0].created_by;
      delete this.agent.winupdatepolicy[0].created_time;
      delete this.agent.winupdatepolicy[0].modified_by;
      delete this.agent.winupdatepolicy[0].modified_time;
      delete this.agent.winupdatepolicy[0].policy;

      // only send the timezone data if it has changed
      // this way django will keep the db column as null and inherit from the global setting
      // until we explicity change the agent's timezone
      if (this.timezone !== this.original_tz) {
        this.agent.time_zone = this.timezone;
      }

      this.$axios
        .patch("/agents/editagent/", {
          ...this.agent,
          custom_fields: this.formatCustomFields(this.customFields, this.custom_fields),
        })
        .then(r => {
          this.$emit("close");
          this.$emit("edited");
          this.notifySuccess("Agent was edited!");
        })
        .catch(e => {
          this.notifyError("Something went wrong");
        });
    },
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    site_options() {
      if (this.agentLoaded && this.clientsLoaded) {
        return this.formatSiteOptions(this.agent.client["sites"]);
      }
    },
  },
  created() {
    // Get custom fields
    this.getCustomFields("agent").then(r => {
      this.customFields = r.data;
    });
    this.getAgentInfo();
    this.getClientsSites();
  },
};
</script>