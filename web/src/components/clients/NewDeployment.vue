<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="width: 40vw">
      <q-bar>
        Add Deployment
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary" />
        </q-btn>
      </q-bar>
      <q-card-section>
        <tactical-dropdown
          :rules="[val => !!val || '*Required']"
          outlined
          label="Site"
          v-model="state.site"
          :options="siteOptions"
          mapOptions
        />
      </q-card-section>
      <q-card-section>
        <div class="q-pl-sm">Agent Type</div>
        <q-radio v-model="state.agenttype" val="server" label="Server" @update:model-value="power = false" />
        <q-radio v-model="state.agenttype" val="workstation" label="Workstation" />
      </q-card-section>
      <q-card-section>
        <q-input type="datetime-local" dense label="Expiry" stack-label filled v-model="state.expires" />
      </q-card-section>
      <q-card-section class="q-gutter-sm">
        <q-checkbox v-model="state.rdp" dense label="Enable RDP" />
        <q-checkbox v-model="state.ping" dense label="Enable Ping" />
        <q-checkbox
          v-model="state.power"
          dense
          v-show="state.agenttype === 'workstation'"
          label="Disable sleep/hibernate"
        />
      </q-card-section>
      <q-card-section>
        <div class="q-pl-sm">OS</div>
        <q-radio v-model="state.arch" val="64" label="64 bit" />
        <q-radio v-model="state.arch" val="32" label="32 bit" />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn dense flat label="Cancel" v-close-popup />
        <q-btn :loading="loading" dense flat label="Create" color="primary" @click="submit" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref } from "vue";
import { useDialogPluginComponent, date } from "quasar";
import { useSiteDropdown } from "@/composables/clients";
import { saveDeployment } from "@/api/clients";
import { notifySuccess } from "@/utils/notify";
import { formatDateInputField, formatDateStringwithTimezone } from "@/utils/format";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown";
export default {
  name: "NewDeployment",
  components: {
    TacticalDropdown,
  },
  emits: [...useDialogPluginComponent.emits],
  setup(props) {
    // setup quasar dialog
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // setup site dropdown
    const { siteOptions } = useSiteDropdown(true);

    // add deployment logic
    const state = ref({
      site: null,
      expires: formatDateInputField(date.addToDate(Date.now(), { days: 30 })),
      agenttype: "server",
      power: false,
      rdp: false,
      ping: false,
      arch: "64",
    });

    const loading = ref(false);

    async function submit() {
      loading.value = true;

      const data = {
        ...state.value,
      };

      if (data.expires) data.expires = formatDateStringwithTimezone(data.expires);

      try {
        const result = await saveDeployment(data);
        notifySuccess(result);
        onDialogOK();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    return {
      // reactive data
      state,
      loading,
      siteOptions,

      // methods
      submit,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>