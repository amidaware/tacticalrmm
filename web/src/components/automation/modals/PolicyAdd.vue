<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        Edit policies assigned to {{ type }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="submit">
        <q-card-section v-if="options.length > 0">
          <q-select
            v-if="type === 'client' || type === 'site'"
            class="q-mb-md"
            v-model="selectedServerPolicy"
            :options="options"
            outlined
            dense
            options-dense
            clearable
            map-options
            emit-value
            label="Server Policy"
          >
          </q-select>
          <q-select
            v-if="type === 'client' || type === 'site'"
            v-model="selectedWorkstationPolicy"
            :options="options"
            outlined
            options-dense
            dense
            clearable
            map-options
            emit-value
            label="Workstation Policy"
          >
          </q-select>
          <q-select
            v-if="type === 'agent'"
            v-model="selectedAgentPolicy"
            :options="options"
            outlined
            options-dense
            dense
            clearable
            map-options
            emit-value
            label="Policy"
          >
          </q-select>
        </q-card-section>
        <q-card-section v-else>
          No Automation Policies have been setup. Go to Settings > Automation Manager
        </q-card-section>
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn v-if="options.length > 0" flat label="Submit" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "PolicyAdd",
  props: {
    object: !Object,
    type: {
      required: true,
      type: String,
      validator: function (value) {
        // The value must match one of these strings
        return ["agent", "site", "client"].includes(value);
      },
    },
  },
  mixins: [mixins],
  data() {
    return {
      selectedWorkstationPolicy: null,
      selectedServerPolicy: null,
      selectedAgentPolicy: null,
      options: [],
    };
  },
  methods: {
    submit() {
      // check if data was changed
      if (this.type === "client" || this.type === "site") {
        if (
          this.object.workstation_policy === this.selectedWorkstationPolicy &&
          this.object.server_policy === this.selectedServerPolicy
        ) {
          this.hide();
          return;
        }
      } else if (this.type === "agent") {
        if (this.object.policy === this.selectedAgentPolicy) {
          this.hide();
          return;
        }
      } else {
        return;
      }
      this.$q.loading.show();

      let data = {};
      let url = "";
      if (this.type === "client") {
        url = `/clients/${this.object.id}/client/`;
        data = {
          client: {
            pk: this.object.id,
            server_policy: this.selectedServerPolicy,
            workstation_policy: this.selectedWorkstationPolicy,
          },
        };
      } else if (this.type === "site") {
        url = `/clients/sites/${this.object.id}/`;
        data = {
          site: {
            pk: this.object.id,
            server_policy: this.selectedServerPolicy,
            workstation_policy: this.selectedWorkstationPolicy,
          },
        };
      } else if (this.type === "agent") {
        url = "/agents/editagent/";
        data = {
          id: this.object.id,
          policy: this.selectedAgentPolicy,
        };
      }

      this.$axios
        .put(url, data)
        .then(r => {
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess("Policies Updated Successfully!");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("There was an error updating policies");
        });
    },
    getPolicies() {
      this.$q.loading.show();
      this.$axios
        .get("/automation/policies/")
        .then(r => {
          this.options = r.data.map(policy => ({
            label: policy.name,
            value: policy.id,
          }));

          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Add error occured while loading policies");
        });
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
  mounted() {
    this.getPolicies();

    if (this.type !== "agent") {
      this.selectedServerPolicy = this.object.server_policy;
      this.selectedWorkstationPolicy = this.object.workstation_policy;
    } else {
      this.selectedAgentPolicy = this.object.policy;
    }
  },
};
</script>