<template>
  <q-card style="width: 60vw">
    <q-card-section class="row items-center">
      <div class="text-h6">Edit policies assigned to {{ type }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-form @submit="submit" ref="form">
      <q-card-section v-if="type !== 'agent'">
        <q-select
          v-model="selectedServerPolicy"
          :options="options"
          filled
          options-selected-class="text-green"
          dense
          clearable
          label="Server Policy"
        >
          <template v-slot:option="props">
            <q-item v-bind="props.itemProps" v-on="props.itemEvents">
              <q-item-section avatar>
                <q-icon v-if="props.selected" name="check" />
              </q-item-section>
              <q-item-section>
                <q-item-label v-html="props.opt.label" />
              </q-item-section>
            </q-item>
          </template>
        </q-select>
      </q-card-section>
      <q-card-section v-if="type !== 'agent'">
        <q-select
          v-model="selectedWorkstationPolicy"
          :options="options"
          filled
          options-selected-class="text-green"
          dense
          clearable
          label="Workstation Policy"
        >
          <template v-slot:option="props">
            <q-item v-bind="props.itemProps" v-on="props.itemEvents">
              <q-item-section avatar>
                <q-icon v-if="props.selected" name="check" />
              </q-item-section>
              <q-item-section>
                <q-item-label v-html="props.opt.label" />
              </q-item-section>
            </q-item>
          </template>
        </q-select>
      </q-card-section>
      <q-card-section v-if="type === 'agent'">
        <q-select
          v-model="selectedAgentPolicy"
          :options="options"
          filled
          options-selected-class="text-green"
          dense
          clearable
          label="Policy"
        >
          <template v-slot:option="props">
            <q-item v-bind="props.itemProps" v-on="props.itemEvents">
              <q-item-section avatar>
                <q-icon v-if="props.selected" name="check" />
              </q-item-section>
              <q-item-section>
                <q-item-label v-html="props.opt.label" />
              </q-item-section>
            </q-item>
          </template>
        </q-select>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Add Policies" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import { mapGetters } from "vuex";
import mixins, { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";

export default {
  name: "PolicyAdd",
  props: {
    pk: Number,
    type: {
      required: true,
      type: String,
      validator: function (value) {
        // The value must match one of these strings
        return ["agent", "site", "client"].includes(value);
      },
    },
  },
  data() {
    return {
      selectedWorkstationPolicy: null,
      selectedServerPolicy: null,
      selectedAgentPolicy: null,
      options: [],
    };
  },
  computed: {
    ...mapGetters({
      policies: "automation/policies",
    }),
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let data = {};
      data.pk = this.pk;
      data.type = this.type;

      if (this.type !== "agent") {
        data.server_policy = this.selectedServerPolicy === null ? 0 : this.selectedServerPolicy.value;
        data.workstation_policy = this.selectedWorkstationPolicy === null ? 0 : this.selectedWorkstationPolicy.value;
      } else {
        data.policy = this.selectedAgentPolicy === null ? 0 : this.selectedAgentPolicy.value;
      }

      this.$store
        .dispatch("automation/updateRelatedPolicies", data)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$q.notify(notifySuccessConfig("Policies Updated Successfully!"));
        })
        .catch(e => {
          this.$q.loading.hide();
          this.$q.notify(notifyErrorConfig("Something went wrong!"));
        });
    },
    getPolicies() {
      this.$store
        .dispatch("automation/loadPolicies")
        .then(() => {
          this.options = this.policies.map(policy => ({
            label: policy.name,
            value: policy.id,
          }));
        })
        .catch(e => {
          this.$q.loading.hide();
          this.$q.notify(notifyErrorConfig("Add error occured while loading"));
        });
    },
    getRelation(pk, type) {
      this.$store
        .dispatch("automation/getRelatedPolicies", { pk, type })
        .then(r => {
          if (type === "agent") {
            if (r.data.policy !== null) {
              if (r.data.policy.id !== null) {
                this.selectedAgentPolicy = {
                  label: r.data.policy.name,
                  value: r.data.policy.id,
                };
              }
            }
          }

          if (type !== "agent") {
            if (r.data.server_policy !== null) {
              if (r.data.server_policy.id !== undefined) {
                this.selectedServerPolicy = {
                  label: r.data.server_policy.name,
                  value: r.data.server_policy.id,
                };
              }
            }

            if (r.data.workstation_policy !== null) {
              if (r.data.workstation_policy.id !== undefined) {
                this.selectedWorkstationPolicy = {
                  label: r.data.workstation_policy.name,
                  value: r.data.workstation_policy.id,
                };
              }
            }
          }
        })
        .catch(e => {
          this.$q.notify(notifyErrorConfig("Add error occured while loading"));
        });
    },
  },
  mounted() {
    this.getPolicies();
    this.getRelation(this.pk, this.type);
  },
};
</script>