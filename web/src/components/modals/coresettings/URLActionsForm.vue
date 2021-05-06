<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="submit">
        <!-- name -->
        <q-card-section>
          <q-input label="Name" outlined dense v-model="localAction.name" :rules="[val => !!val || '*Required']" />
        </q-card-section>

        <!-- description -->
        <q-card-section>
          <q-input label="Description" outlined dense v-model="localAction.desc" />
        </q-card-section>

        <!-- pattern -->
        <q-card-section>
          <q-input
            label="URL Pattern"
            outlined
            dense
            v-model="localAction.pattern"
            :rules="[val => !!val || '*Required']"
          />
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
  name: "URLActionsForm",
  mixins: [mixins],
  props: { action: Object },
  data() {
    return {
      localAction: {
        name: "",
        desc: "",
        pattern: "",
      },
    };
  },
  computed: {
    title() {
      return this.editing ? "Edit URL Action" : "Add URL Action";
    },
    editing() {
      return !!this.globalAction;
    },
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let data = {
        ...this.localAction,
      };

      if (this.editing) {
        this.$axios
          .put(`/core/urlaction/${data.id}/`, data)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess("Url Action was edited!");
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      } else {
        this.$axios
          .post("/core/urlaction/", data)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess("URL Action was added!");
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
    if (this.action) Object.assign(this.localAction, this.action);
  },
};
</script>