<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 60vw">
      <q-form ref="form" @submit="onSubmit">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ user.username }} Password Reset</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section class="row">
          <div class="col-2">New Password:</div>
          <div class="col-10">
            <q-input
              outlined
              dense
              v-model="password"
              :type="isPwd ? 'password' : 'text'"
              :rules="[(val) => !!val || '*Required']"
            >
              <template v-slot:append>
                <q-icon
                  :name="isPwd ? 'visibility_off' : 'visibility'"
                  class="cursor-pointer"
                  @click="isPwd = !isPwd"
                />
              </template>
            </q-input>
          </div>
        </q-card-section>
        <q-card-section class="row items-center">
          <q-btn label="Reset" color="primary" type="submit" />
        </q-card-section>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "UserResetPasswordForm",
  emits: ["cancel", "ok", "hide"],
  mixins: [mixins],
  props: { user: !Object },
  data() {
    return {
      password: "",
      isPwd: true,
    };
  },
  methods: {
    onSubmit() {
      this.$q.loading.show();
      let data = {
        id: this.user.id,
        password: this.password,
      };

      this.$axios
        .post("/accounts/users/reset/", data)
        .then(() => {
          this.onOk();
          this.$q.loading.hide();
          this.notifySuccess("User Password Reset!");
        })
        .catch(() => {
          this.$q.loading.hide();
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
};
</script>
