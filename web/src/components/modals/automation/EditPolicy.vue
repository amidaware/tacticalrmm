<template>
  <q-card style="width: 40vw">
    <q-form @submit.prevent="editPolicy">
      <q-card-section class="row items-center">
        <div class="text-h6">Edit Policy</div>
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
        <q-btn label="Edit" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "EditPolicy",
  mixins: [mixins],
  props: ["pk"],
  data() {
    return {
      name: "",
      desc: "",
      associations: []
    };
  },
  methods: {
    getPolicy() {
      axios.get(`/automation/policies/${this.pk}/`).then(r => {
        this.name = r.data.name;
        this.desc = r.data.desc;
      })
    },
    editPolicy() {
      if (!this.name) {
        this.notifyError("Name is required!");
        return false;
      }

      this.$q.loading.show();
      let formData = new FormData();
      
      formData.append("name", this.name);
      formData.append("desc", this.desc);

      axios.put(`/automation/policies/${this.pk}/`, formData)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$emit("edited");
          this.notifySuccess("Policy edited!");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    }
  },
  created() {
    this.getPolicy();
  }
};
</script>