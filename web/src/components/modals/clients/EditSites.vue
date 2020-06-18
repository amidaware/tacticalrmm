<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Edit Sites</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="editSite">
        <q-card-section v-if="tree !== null">
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            label="Select client"
            v-model="client"
            :options="Object.keys(tree)"
            @input="site = sites[0]; newName=sites[0]"
          />
        </q-card-section>
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            label="Select site"
            v-model="site"
            :options="sites"
            @input="newName = site"
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            v-model="newName"
            label="Rename site"
          />
        </q-card-section>
        <q-card-actions align="left">
          <q-btn :disable="!nameChanged" label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "EditSites",
  mixins: [mixins],
  data() {
    return {
      tree: null,
      client: null,
      site: null,
      newName: null
    };
  },
  computed: {
    sites() {
      if (this.tree !== null && this.client !== null) {
        this.site = this.tree[this.client][0];
        this.newName = this.tree[this.client][0];
        return this.tree[this.client];
      }
    },
    nameChanged() {
      if (this.site !== null) {
        return this.newName === this.site ? false : true;
      }
    }
  },
  methods: {
    getTree() {
      axios.get("/clients/loadclients/").then(r => {
        this.tree = r.data;
        this.client = Object.keys(r.data)[0];
      });
    },
    editSite() {
      const data = {
        client: this.client,
        site: this.site,
        name: this.newName
      };
      axios
        .patch("/clients/editsite/", data)
        .then(() => {
          this.$emit("edited");
          this.$emit("close");
          this.notifySuccess("Site was edited");
        })
        .catch(e => this.notifyError(e.response.data));
    }
  },
  created() {
    this.getTree();
  }
};
</script>