<template>
  <q-card style="width: 60vw">
    <q-form ref="form" @submit="submit">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ title }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section v-if="copyPolicy">
        <div class="text-subtitle1">
          You are copying checks and tasks from Policy:
          <b>{{ copyPolicy.name }}</b> into a new policy.
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Name:</div>
        <div class="col-10">
          <q-input outlined dense v-model="name" :rules="[ val => !!val || '*Required']" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Description:</div>
        <div class="col-10">
          <q-input outlined dense v-model="desc" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Active:</div>
        <div class="col-10">
          <q-toggle v-model="active" color="green" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Enforced:</div>
        <div class="col-10">
          <q-toggle v-model="enforced" color="green" />
        </div>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn :label="title" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import mixins, { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";

export default {
  name: "PolicyForm",
  mixins: [mixins],
  props: { pk: Number, copyPolicy: Object },
  data() {
    return {
      name: "",
      desc: "",
      enforced: false,
      active: false,
    };
  },
  computed: {
    title() {
      return this.pk ? "Edit Policy" : "Add Policy";
    },
  },
  methods: {
    getPolicy() {
      this.$q.loading.show();

      this.$store.dispatch("automation/loadPolicy", this.pk).then(r => {
        this.$q.loading.hide();

        this.name = r.data.name;
        this.desc = r.data.desc;
        this.active = r.data.active;
        this.enforced = r.data.enforced;
      });
    },
    submit() {
      if (!this.name) {
        this.$q.notify(notifySuccessConfig("Name is required!"));
        return false;
      }

      this.$q.loading.show();

      let formData = {
        id: this.pk,
        name: this.name,
        desc: this.desc,
        active: this.active,
        enforced: this.enforced,
      };

      if (this.pk) {
        this.$store
          .dispatch("automation/editPolicy", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.$q.notify(notifySuccessConfig("Policy edited!"));
          })
          .catch(e => {
            this.$q.loading.hide();
            this.$q.notify(notifyErrorConfig(e.response.data));
          });
      } else {
        if (this.copyPolicy) {
          formData.copyId = this.copyPolicy.id;
        }

        this.$store
          .dispatch("automation/addPolicy", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.$q.notify(notifySuccessConfig("Policy added! Now you can add Tasks and Checks!"));
          })
          .catch(e => {
            this.$q.loading.hide();
            this.$q.notify(notifyErrorConfig(e.response.data));
          });
      }
    },
  },
  mounted() {
    // If pk prop is set that means we are editting
    if (this.pk) {
      this.getPolicy();
    }
  },
};
</script>