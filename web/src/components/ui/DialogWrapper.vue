<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin">
      <q-bar>
        <slot name="bar">
          {{ title }}
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </slot>
      </q-bar>
      <div class="scroll" style="height: 70vh">
        <component :is="vuecomponent" v-bind="{ ...$attrs, ...componentProps }" @close="onOk" @hide="hide" />
      </div>
    </q-card>
  </q-dialog>
</template>

<script>
export default {
  name: "DialogWrapper",
  props: {
    vuecomponent: {},
    title: String,
    componentProps: Object,
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