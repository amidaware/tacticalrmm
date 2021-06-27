<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="submit">
        <!-- name -->
        <q-card-section>
          <q-input label="Name" outlined dense v-model="localKey.name" :rules="[val => !!val || '*Required']" />
        </q-card-section>

        <!-- value -->
        <q-card-section>
          <q-input label="Value" outlined dense v-model="localKey.value" :rules="[val => !!val || '*Required']" />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn flat label="Submit" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "KeyStoreForm",
  emits: ["hide", "ok", "cancel"],
  mixins: [mixins],
  props: { globalKey: Object },
  data() {
    return {
      localKey: {
        name: "",
        value: "",
      },
    };
  },
  computed: {
    title() {
      return this.editing ? "Edit Global Key" : "Add Global Key";
    },
    editing() {
      return !!this.globalKey;
    },
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let data = {
        ...this.localKey,
      };

      if (this.editing) {
        this.$axios
          .put(`/core/keystore/${data.id}/`, data)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess("Key was edited!");
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      } else {
        this.$axios
          .post("/core/keystore/", data)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess("Key was added!");
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      }
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
    // If pk prop is set that means we are editing
    if (this.globalKey) Object.assign(this.localKey, this.globalKey);
  },
};
</script>