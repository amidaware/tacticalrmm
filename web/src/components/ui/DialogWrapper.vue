<template>
  <q-dialog ref="dialog" @hide="onHide" v-bind="dialogProps">
    <q-card class="q-dialog-plugin" :style="`min-width: ${width}vw`">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <div class="scroll" :style="`height: ${height}vh`">
        <component :is="vuecomponent" v-bind="{ ...$attrs, ...componentProps }" @close="onOk" @hide="hide" />
      </div>
    </q-card>
  </q-dialog>
</template>

<script>
export default {
  name: "DialogWrapper",
  emits: ["hide", "ok", "cancel"],
  props: {
    vuecomponent: {},
    title: String,
    width: {
      type: String,
      default: "50",
    },
    height: {
      type: String,
      default: "50",
    },
    componentProps: Object,
    dialogProps: Object,
  },
  inheritAttrs: false,
  methods: {
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