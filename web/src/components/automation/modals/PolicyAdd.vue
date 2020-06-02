<template>
  <q-card style="width: 60vw" >
    <q-card-section class="row items-center">
      <div class="text-h6">Edit policies assigned to {{ type }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
      <q-form @submit="submit" ref="form">
        <q-card-section>
          <q-select 
            v-model="selected" 
            :options="options" 
            filled 
            multiple 
            use-chips
            options-selected-class="text-green"
            dense
          >
            <template v-slot:option="props">
              <q-item
                v-bind="props.itemProps"
                v-on="props.itemEvents"
              >
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
          <q-btn label="Add Polices" color="primary" type="submit" />
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
        }
    }
  },
  data() {
    return {
      selected: [],
      options: []
    }
  },
  computed: {
    ...mapGetters({
      policies: "automation/policies"
    })
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let data = {};
      data.pk = this.pk,
      data.type = this.type;
      data.policies = this.selected.map(policy => policy.value);

      this.$store
        .dispatch("automation/updateRelatedPolicies", data)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$q.notify(notifySuccessConfig("Policies Updated Successfully!"));
        })
        .catch(e => {
          this.$q.loading.hide();
          this.$q.notify(notifyErrorConfig("Something went wrong!"))
        });
    },
    getPolicies() {
      this.$store
        .dispatch("automation/loadPolicies")
        .then(() => {
          this.options = this.policies.map(policy => ({
            label: policy.name,
            value: policy.id
          }))
        })
        .catch(e => {
          this.$q.loading.hide();
          this.$q.notify(notifyErrorConfig("Add error occured while loading"));
        });;

    },
    getRelations(pk, type) {
      this.$store
        .dispatch("automation/getRelatedPolicies", {pk, type})
        .then(r => {
          this.selected = r.data.map(item => ({
            label: item.name,
            value: item.id
          }))
        })
        .catch(e => {
          this.$q.notify(notifyErrorConfig("Add error occured while loading"));
        });
    }
  },
  mounted() {
    this.getPolicies();
    this.getRelations(this.pk, this.type);
  }
}
</script>