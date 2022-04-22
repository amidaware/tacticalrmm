<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="min-width: 800px">
      <q-splitter v-model="splitterModel">
        <template v-slot:before>
          <q-tabs dense v-model="tab" vertical class="text-primary">
            <q-tab name="general" label="General" />
            <q-tab name="customfields" label="Custom Fields" />
            <q-tab name="patch" label="Patches" />
            <q-tab name="policies" label="Automation Policies" />
          </q-tabs>
        </template>
        <template v-slot:after>
          <q-form @submit.prevent="editAgent">
            <q-card-section class="row items-center">
              <div class="text-h6">Edit {{ agent.hostname }}</div>
              <q-space />
              <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>
            <div class="scroll" style="height: 65vh; max-height: 65vh">
              <q-tab-panels v-model="tab" animated transition-prev="jump-up" transition-next="jump-up">
                <!-- general -->
                <q-tab-panel name="general">
                  <q-card-section class="row">
                    <div class="col-2">Site:</div>
                    <div class="col-2"></div>
                    <tactical-dropdown
                      class="col-8"
                      v-model="agent.site"
                      :options="siteOptions"
                      outlined
                      mapOptions
                      filterable
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
                    <q-input outlined dense v-model="agent.description" class="col-8" />
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
                    <q-checkbox v-model="agent.overdue_dashboard_alert" label="Get overdue dashboard alerts" />
                  </q-card-section>
                </q-tab-panel>

                <!-- custom fields -->
                <q-tab-panel name="customfields">
                  <div class="text-subtitle" v-if="customFields.length === 0">
                    No agent custom fields found. Go to **Settings > Global Settings > Custom Settings**
                  </div>
                  <q-card-section v-for="field in customFields" :key="field.id">
                    <CustomField v-model="custom_fields[field.name]" :field="field" />
                  </q-card-section>
                </q-tab-panel>

                <!-- patch -->
                <q-tab-panel name="patch">
                  <PatchPolicyForm :agent="agent" />
                </q-tab-panel>

                <!-- automation policies -->
                <q-tab-panel name="policies">
                  <div class="text-subtitle2">Policies</div>
                  <q-list separator padding dense>
                    <q-item v-for="(policy, key) in agent.applied_policies" :key="key">
                      <q-item-section>
                        <q-item-label overline>
                          {{ capitalize(key).split("_").join(" ") }}
                        </q-item-label>
                        <q-item-label>{{ policy ? policy.name : "None" }}</q-item-label>
                      </q-item-section>
                      <q-item-section side v-if="policy">
                        <q-item-label>
                          <i>{{ policy.active ? "" : "disabled" }}</i>
                        </q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>

                  <div class="text-subtitle2">Alert Template</div>
                  <q-list dense padding>
                    <q-item>
                      <q-item-section>
                        <q-item-label>{{ agent.alert_template ? agent.alert_template.name : "None" }}</q-item-label>
                      </q-item-section>
                      <q-item-section side v-if="agent.alert_template">
                        <q-item-label>
                          <i>{{ agent.alert_template.is_active ? "" : "disabled" }}</i>
                        </q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>
                  <div class="text-subtitle2">Effective Patch Policy</div>
                  <q-list separator padding dense>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Critical</q-item-label>
                        <q-item-label>{{
                          agent.effective_patch_policy.critical !== "inherit"
                            ? capitalize(agent.effective_patch_policy.critical)
                            : "Do Nothing"
                        }}</q-item-label>
                      </q-item-section>
                    </q-item>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Important</q-item-label>
                        <q-item-label>{{
                          agent.effective_patch_policy.important !== "inherit"
                            ? capitalize(agent.effective_patch_policy.important)
                            : "Do Nothing"
                        }}</q-item-label>
                      </q-item-section>
                    </q-item>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Moderate</q-item-label>
                        <q-item-label>{{
                          agent.effective_patch_policy.moderate !== "inherit"
                            ? capitalize(agent.effective_patch_policy.moderate)
                            : "Do Nothing"
                        }}</q-item-label>
                      </q-item-section>
                    </q-item>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Low</q-item-label>
                        <q-item-label>{{
                          agent.effective_patch_policy.low !== "inherit"
                            ? capitalize(agent.effective_patch_policy.low)
                            : "Do Nothing"
                        }}</q-item-label>
                      </q-item-section>
                    </q-item>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Other</q-item-label>
                        <q-item-label>{{
                          agent.effective_patch_policy.other !== "inherit"
                            ? capitalize(agent.effective_patch_policy.other)
                            : "Do Nothing"
                        }}</q-item-label>
                      </q-item-section>
                    </q-item>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Run Time Frequency</q-item-label>
                        <q-item-label>{{ capitalize(agent.effective_patch_policy.run_time_frequency) }}</q-item-label>
                      </q-item-section>
                      <q-item-section v-if="agent.effective_patch_policy.run_time_frequency === 'daily'">
                        <q-item-label>
                          <b>week days:</b>
                          {{ weekDaystoString(agent.effective_patch_policy.run_time_days) }} <b>at hour:</b>
                          {{ agent.effective_patch_policy.run_time_hour }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section v-else-if="agent.effective_patch_policy.run_time_frequency === 'monthly'">
                        <q-item-label>
                          <b>Every month on day:</b> {{ agent.effective_patch_policy.run_time_day }} <b>at hour:</b>
                          {{ agent.effective_patch_policy.run_time_hour }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section v-else>
                        <q-item-label>None</q-item-label>
                      </q-item-section>
                    </q-item>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Reboot after installation</q-item-label>
                        <q-item-label>{{
                          agent.effective_patch_policy.reboot_after_install !== "inherit"
                            ? capitalize(agent.effective_patch_policy.reboot_after_install)
                            : "Do Nothing"
                        }}</q-item-label>
                      </q-item-section>
                    </q-item>
                    <q-item>
                      <q-item-section>
                        <q-item-label overline>Failed patch options</q-item-label>
                        <q-item-label v-if="agent.effective_patch_policy.reprocess_failed_inherit"
                          >Do Nothing</q-item-label
                        >
                        <q-item-label v-else>
                          <b>Reprocess failed patches:</b>
                          {{
                            agent.effective_patch_policy.reprocess_failed
                              ? agent.effective_patch_policy.reprocess_failed_times
                              : "Never"
                          }}
                          <b>Email on fail:</b> {{ agent.effective_patch_policy.email_if_fail ? "Yes" : "Never" }}
                        </q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>
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
  </q-dialog>
</template>

<script>
import { useDialogPluginComponent } from "quasar";
import mixins from "@/mixins/mixins";
import PatchPolicyForm from "@/components/modals/agents/PatchPolicyForm";
import CustomField from "@/components/ui/CustomField";
import TacticalDropdown from "@/components/ui/TacticalDropdown";
import { capitalize } from "@/utils/format";

export default {
  name: "EditAgent",
  emits: [...useDialogPluginComponent.emits],
  components: { PatchPolicyForm, CustomField, TacticalDropdown },
  mixins: [mixins],
  props: {
    agent_id: !String,
  },
  setup(props) {
    // quasar dialog setup
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    return {
      // methods
      capitalize,

      // dialog
      dialogRef,
      onDialogHide,
    };
  },
  data() {
    return {
      customFields: [],
      custom_fields: {},
      agent: {},
      monTypes: ["server", "workstation"],
      client_options: [],
      splitterModel: 25,
      tab: "general",
      timezone: null,
      tz_inherited: true,
      original_tz: null,
      allTimezones: [],
      siteOptions: [],
    };
  },
  methods: {
    getAgentInfo() {
      this.$axios
        .get(`/agents/${this.agent_id}/`)
        .then(r => {
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

          for (let field of this.customFields) {
            const value = r.data.custom_fields.find(value => value.field === field.id);

            if (field.type === "multiple") {
              if (value) this.custom_fields[field.name] = value.value;
              else this.custom_fields[field.name] = [];
            } else if (field.type === "checkbox") {
              if (value) this.custom_fields[field.name] = value.value;
              else this.custom_fields[field.name] = false;
            } else {
              if (value) this.custom_fields[field.name] = value.value;
              else this.custom_fields[field.name] = "";
            }
          }
        })
        .catch(e => {});
    },
    getSiteOptions() {
      this.$axios
        .get("/clients/")
        .then(r => {
          r.data.forEach(client => {
            this.siteOptions.push({ category: client.name });
            client.sites.forEach(site => this.siteOptions.push({ label: site.name, value: site.id }));
          });
        })
        .catch(e => {});
    },
    editAgent() {
      delete this.agent.all_timezones;
      delete this.agent.timezone;

      // only send the timezone data if it has changed
      // this way django will keep the db column as null and inherit from the global setting
      // until we explicity change the agent's timezone
      if (this.timezone !== this.original_tz) {
        this.agent.time_zone = this.timezone;
      }

      this.$axios
        .put(`/agents/${this.agent_id}/`, {
          ...this.agent,
          custom_fields: this.formatCustomFields(this.customFields, this.custom_fields),
        })
        .then(r => {
          this.$refs.dialogRef.hide();
          this.$emit("ok");
          this.notifySuccess("Agent was edited!");
        })
        .catch(e => {});
    },
    weekDaystoString(array) {
      if (array.length === 0) return "not set";

      let result = "";
      for (let day in array) {
        if (day === 1) result += "Mon, ";
        else if (day === 2) result += "Tue, ";
        else if (day === 3) result += "Wed, ";
        else if (day === 4) result += "Thur, ";
        else if (day === 5) result += "Fri, ";
        else if (day === 6) result += "Sat, ";
        else if (day === 0) result += "Sun, ";
      }

      return result.trimRight(",");
    },
  },
  mounted() {
    // Get custom fields
    this.getCustomFields("agent").then(r => {
      this.customFields = r.data.filter(field => !field.hide_in_ui);
    });
    this.getAgentInfo();
    this.getSiteOptions();
  },
};
</script>