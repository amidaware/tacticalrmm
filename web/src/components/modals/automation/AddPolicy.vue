<template>
  <q-card style="width: 40vw">
    <q-form @submit.prevent="addPolicy">
      <q-card-section class="row items-center">
        <div class="text-h6">Add Policy</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
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
          <q-input outlined dense v-model="desc" type="textarea" />
        </div>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Add" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "AddPolicy",
  mixins: [mixins],
  data() {
    return {
      name: "",
      desc: ""
    };
  },
  methods: {
    addPolicy() {
      if (!this.name) {
        this.notifyError("Name is required!");
        return false;
      }

      this.$q.loading.show();
      let formData = new FormData();
      formData.append("name", this.name);
      formData.append("desc", this.desc);
      axios
        .post("/automation/policies/", formData)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$emit("added");
          this.notifySuccess("Policy added! Edit the policy to add Checks!");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    }
  }
};
</script>