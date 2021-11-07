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
      <q-form @submit="submit">
        <q-card-section>
          <tactical-dropdown outlined label="Site" v-model="state.site" :options="siteOptions" mapOptions />
        </q-card-section>
        <q-card-section>
          <div class="q-pl-sm">Agent Type</div>
          <q-radio v-model="state.agenttype" val="server" label="Server" @update:model-value="power = false" />
          <q-radio v-model="state.agenttype" val="workstation" label="Workstation" />
        </q-card-section>
        <q-card-section>
          <q-input label="Expiry" dense filled v-model="state.expires" hint="Agent timezone will be used">
            <template v-slot:append>
              <q-icon name="event" class="cursor-pointer">
                <q-popup-proxy transition-show="scale" transition-hide="scale">
                  <q-date v-model="state.expires" mask="YYYY-MM-DD HH:mm">
                    <div class="row items-center justify-end">
                      <q-btn v-close-popup label="Close" color="primary" flat />
                    </div>
                  </q-date>
                </q-popup-proxy>
              </q-icon>
              <q-icon name="access_time" class="cursor-pointer">
                <q-popup-proxy transition-show="scale" transition-hide="scale">
                  <q-time v-model="state.expires" mask="YYYY-MM-DD HH:mm">
                    <div class="row items-center justify-end">
                      <q-btn v-close-popup label="Close" color="primary" flat />
                    </div>
                  </q-time>
                </q-popup-proxy>
              </q-icon>
            </template>
          </q-input>
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
          <q-btn :loading="loading" dense flat label="Create" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref } from "vue";
import { useDialogPluginComponent } from "quasar";
import { useSiteDropdown } from "@/composables/clients";
import { saveDeployment } from "@/api/clients";
import { notifySuccess } from "@/utils/notify";
import { date } from "quasar";

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
      expires: date.formatDate(new Date().setDate(new Date().getDate() + 30), "YYYY-MM-DD HH:mm"),
      agenttype: "server",
      power: false,
      rdp: false,
      ping: false,
      arch: "64",
    });

    const loading = ref(false);

    async function submit() {
      loading.value = true;
      try {
        const result = await saveDeployment(state.value);
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