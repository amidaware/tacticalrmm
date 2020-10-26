<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Delete Site</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="deleteSite">
        <q-card-section v-if="tree !== null">
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select client"
            v-model="client"
            :options="Object.keys(tree).sort()"
            @input="site = sites[0]"
          />
        </q-card-section>
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Select site"
            v-model="site"
            :options="sites"
          />
        </q-card-section>
        <q-card-actions align="left">
          <q-btn :disable="site === null" :label="`Delete ${site}`" class="full-width" color="negative" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
export default {
  name: "DeleteSite",
  mixins: [mixins],
  data() {
    return {
      tree: null,
      client: null,
      site: null,
    };
  },
  computed: {
    sites() {
      if (this.tree !== null && this.client !== null) {
        this.site = this.tree[this.client].sort()[0];
        return this.tree[this.client].sort();
      }
    },
  },
  methods: {
    getTree() {
      this.$axios.get("/clients/loadclients/").then(r => {
        this.tree = r.data;
        this.client = Object.keys(r.data).sort()[0];
      });
    },
    deleteSite() {
      const data = {
        client: this.client,
        site: this.site,
      };
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete site ${this.site}`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$axios
            .delete("/clients/deletesite/", { data })
            .then(r => {
              this.$emit("edited");
              this.$emit("close");
              this.notifySuccess(r.data);
            })
            .catch(e => this.notifyError(e.response.data, 6000));
        });
    },
  },
  created() {
    this.getTree();
  },
};
</script>