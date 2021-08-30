<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="min-width: 50vw">
      <q-bar>
        {{ modalTitle }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit.prevent="submit">
        <q-card-section>
          <p>Choose Target</p>
          <q-option-group
            v-model="state.target"
            :options="targetOptions"
            color="primary"
            dense
            inline
            class="q-pl-sm"
          />
        </q-card-section>

        <q-card-section>
          <tactical-dropdown
            v-if="state.target === 'client'"
            :rules="[val => !!val || '*Required']"
            v-model="state.client"
            :options="clientOptions"
            label="Select Client"
            outlined
            mapOptions
            filterable
          />
          <tactical-dropdown
            v-else-if="state.target === 'site'"
            :rules="[val => !!val || '*Required']"
            v-model="state.site"
            :options="siteOptions"
            label="Select Site"
            outlined
            mapOptions
            filterable
          />
          <tactical-dropdown
            v-else-if="state.target === 'agents'"
            :rules="[val => !!val || '*Required']"
            v-model="state.agents"
            :options="agentOptions"
            label="Select Agents"
            filled
            multiple
            mapOptions
            filterable
          />
        </q-card-section>

        <q-card-section v-show="state.target !== 'agents'">
          <p>Agent Type</p>
          <q-option-group
            v-model="state.monType"
            :options="monTypeOptions"
            color="primary"
            dense
            inline
            class="q-pl-sm"
          />
        </q-card-section>

        <q-card-section v-if="mode === 'script'" class="q-pt-none">
          <tactical-dropdown
            :rules="[val => !!val || '*Required']"
            v-model="state.script"
            :options="scriptOptions"
            label="Select Script"
            outlined
            mapOptions
            filterable
          />
        </q-card-section>
        <q-card-section v-if="mode === 'script'" class="q-pt-none">
          <tactical-dropdown
            v-model="state.args"
            label="Script Arguments (press Enter after typing each argument)"
            filled
            use-input
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>

        <q-card-section v-if="mode === 'command'">
          <p>Shell</p>
          <q-option-group v-model="state.shell" :options="shellOptions" color="primary" dense inline class="q-pl-sm" />
        </q-card-section>
        <q-card-section v-if="mode === 'command'">
          <q-input
            v-model="state.cmd"
            outlined
            label="Command"
            stack-label
            :placeholder="
              shell === 'cmd'
                ? 'rmdir /S /Q C:\\Windows\\System32'
                : 'Remove-Item -Recurse -Force C:\\Windows\\System32'
            "
            :rules="[val => !!val || '*Required']"
          />
        </q-card-section>

        <q-card-section v-if="mode === 'script' || mode === 'command'">
          <q-input
            v-model.number="state.timeout"
            dense
            outlined
            type="number"
            style="max-width: 150px"
            label="Timeout (seconds)"
            stack-label
            :rules="[val => !!val || '*Required', val => val >= 5 || 'Minimum is 5 seconds']"
          />
        </q-card-section>

        <q-card-section v-if="mode === 'patch'">
          <p>Action</p>
          <q-option-group
            v-model="state.patchMode"
            :options="patchModeOptions"
            color="primary"
            dense
            inline
            class="q-pl-sm"
          />
        </q-card-section>

        <q-card-section v-show="false">
          <q-checkbox v-model="state.offlineAgents" label="Offline Agents (Run on next checkin)">
            <q-tooltip>If the agent is offline, a pending action will be created to run on agent checkin</q-tooltip>
          </q-checkbox>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn label="Cancel" v-close-popup />
          <q-btn label="Run" color="primary" type="submit" :disable="loading" :loading="loading" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { useDialogPluginComponent } from "quasar";
import { useScriptDropdown } from "@/composables/scripts";
import { useAgentDropdown } from "@/composables/agents";
import { useClientDropdown, useSiteDropdown } from "@/composables/clients";
import { runBulkAction } from "@/api/agents";
import { notifySuccess } from "@/utils/notify";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown";

// static data
const monTypeOptions = [
  { label: "All", value: "all" },
  { label: "Servers", value: "servers" },
  { label: "Workstations", value: "workstations" },
];

const targetOptions = [
  { label: "Client", value: "client" },
  { label: "Site", value: "site" },
  { label: "Selected Agents", value: "agents" },
  { label: "All", value: "all" },
];

const shellOptions = [
  { label: "CMD", value: "cmd" },
  { label: "Powershell", value: "powershell" },
];

const patchModeOptions = [
  { label: "Scan", value: "scan" },
  { label: "Install", value: "install" },
];

export default {
  name: "BulkAction",
  components: { TacticalDropdown },
  emits: [...useDialogPluginComponent.emits],
  props: {
    mode: !String,
  },
  setup(props) {
    // setup vuex store
    const store = useStore();
    const showCommunityScripts = computed(() => store.state.showCommunityScripts);

    // quasar dialog setup
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    // dropdown setup
    const { script, scriptOptions, defaultTimeout, defaultArgs, getScriptOptions } = useScriptDropdown();
    const { agents, agentOptions, getAgentOptions } = useAgentDropdown();
    const { site, siteOptions, getSiteOptions } = useSiteDropdown();
    const { client, clientOptions, getClientOptions } = useClientDropdown();

    // bulk action logic
    const state = ref({
      mode: props.mode,
      target: "client",
      monType: "all",
      cmd: "",
      shell: "cmd",
      patchMode: "scan",
      offlineAgents: false,
      client,
      site,
      agents,
      script,
      timeout: defaultTimeout,
      args: defaultArgs,
    });
    const loading = ref(false);

    watch(
      () => state.value.target,
      (newValue, oldValue) => {
        client.value = null;
        site.value = null;
        agents.value = [];
      }
    );

    async function submit() {
      loading.value = true;

      try {
        const data = await runBulkAction(state.value);
        notifySuccess(data);
      } catch (e) {}

      loading.value = false;
    }

    // set modal title and caption
    const modalTitle = computed(() => {
      return props.mode === "command"
        ? "Run Bulk Command"
        : props.mode === "script"
        ? "Run Bulk Script"
        : props.mode === "scan"
        ? "Bulk Patch Management"
        : "";
    });

    // component lifecycle hooks
    onMounted(() => {
      getAgentOptions();
      getSiteOptions();
      getClientOptions();
      if (props.mode === "script") getScriptOptions(showCommunityScripts.value);
    });

    return {
      // reactive data
      state,
      agentOptions,
      clientOptions,
      siteOptions,
      scriptOptions,
      loading,

      // non-reactive data
      monTypeOptions,
      targetOptions,
      shellOptions,
      patchModeOptions,

      //computed
      modalTitle,

      //methods
      submit,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>