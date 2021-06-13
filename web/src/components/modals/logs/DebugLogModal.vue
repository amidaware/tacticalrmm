<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card class="q-dialog-plugin bg-grey-10 text-white">
      <q-bar>
        <q-btn @click="getDebugLog" class="q-mr-sm" dense flat push icon="refresh" label="Refresh" />Debug Log
        <q-space />
        <q-btn color="primary" text-color="white" label="Download log" @click="downloadDebugLog" />
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <div class="q-pa-md row">
        <div class="col-2">
          <q-select dark dense options-dense outlined v-model="agent" :options="agents" label="Filter Agent" />
        </div>
        <div class="col-1">
          <q-select dark dense options-dense outlined v-model="order" :options="orders" label="Order" />
        </div>
      </div>
      <q-card-section>
        <q-radio dark v-model="logLevel" color="cyan" val="info" label="Info" />
        <q-radio dark v-model="logLevel" color="red" val="critical" label="Critical" />
        <q-radio dark v-model="logLevel" color="red" val="error" label="Error" />
        <q-radio dark v-model="logLevel" color="yellow" val="warning" label="Warning" />
      </q-card-section>
      <q-separator />
      <q-card-section class="scroll" style="max-height: 80vh">
        <pre>{{ debugLog }}</pre>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import { useDialogPluginComponent } from "quasar";
import { useDebugLog } from "@/composables/logs";
import { downloadDebugLog } from "@/api/logs";
//import {getAgentOptions}

export default {
  name: "LogModal",
  setup() {
    const { debugLog, logLevel, order, agent, getDebugLog } = useDebugLog();
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    return {
      //data
      debugLog,
      logLevel,
      order,
      agent,
      agents: [],

      //non-reactive data
      orders: ["latest", "oldest"],

      //methods
      getDebugLog,
      downloadDebugLog,

      //quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>