<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" v-bind="dialogProps">
    <q-card
      v-if="!noCard"
      class="q-dialog-plugin"
      :style="`min-width: ${width}vw`"
    >
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <div class="scroll" :style="`height: ${height}vh`">
        <component
          :is="vuecomponent"
          v-bind="{ ...$attrs, ...componentProps }"
          @close="onDialogOK"
          @hide="onDialogHide"
        />
      </div>
    </q-card>
    <component
      v-else
      class="q-dialog-plugin"
      :is="vuecomponent"
      v-bind="{ ...$attrs, ...componentProps }"
    />
  </q-dialog>
</template>

<script>
import { useDialogPluginComponent } from "quasar";

export default {
  name: "DialogWrapper",
  emits: [...useDialogPluginComponent.emits],
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
    noCard: {
      type: Boolean,
      default: false,
    },
    componentProps: Object,
    dialogProps: Object,
  },
  inheritAttrs: false,
  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } =
      useDialogPluginComponent();

    return {
      // quasar dialog plugin
      dialogRef,
      onDialogHide,
      onDialogOK,
      onDialogCancel,
    };
  },
};
</script>
