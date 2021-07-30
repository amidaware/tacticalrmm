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
          <p>Agent Type</p>
          <q-option-group v-model="monType" :options="monTypeOptions" color="primary" dense inline class="q-pl-sm" />
        </q-card-section>
        <q-card-section>
          <p>Choose Target</p>
          <q-option-group v-model="target" :options="targetOptions" color="primary" dense inline class="q-pl-sm" />
        </q-card-section>

        <q-card-section>
          <tactical-dropdown
            v-if="target === 'client'"
            :rules="[val => !!val || '*Required']"
            v-model="client"
            :options="clientOptions"
            label="Select Client"
            outlined
            mapOptions
            filterable
          />
          <tactical-dropdown
            v-else-if="target === 'site'"
            :rules="[val => !!val || '*Required']"
            v-model="site"
            :options="siteOptions"
            label="Select Site"
            outlined
            mapOptions
            filterable
          />
          <tactical-dropdown
            v-else-if="target === 'agents'"
            v-model="agents"
            :options="agentOptions"
            label="Select Agents"
            filled
            multiple
            mapOptions
            filterable
          />
        </q-card-section>

        <q-card-section v-if="mode === 'script'" class="q-pt-none">
          <tactical-dropdown
            :rules="[val => !!val || '*Required']"
            v-model="script"
            :options="scriptOptions"
            label="Select Script"
            outlined
            mapOptions
            filterable
          />
        </q-card-section>
        <q-card-section v-if="mode === 'script'" class="q-pt-none">
          <q-select
            label="Script Arguments (press Enter after typing each argument)"
            filled
            dense
            v-model="args"
            use-input
            use-chips
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>

        <q-card-section v-if="mode === 'command'">
          <p>Shell</p>
          <q-option-group v-model="shell" :options="shellOptions" color="primary" dense inline class="q-pl-sm" />
        </q-card-section>
        <q-card-section v-if="mode === 'command'">
          <q-input
            v-model="cmd"
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
            v-model.number="timeout"
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
            v-model="patchMode"
            :options="patchModeOptions"
            color="primary"
            dense
            inline
            class="q-pl-sm"
          />
        </q-card-section>

        <q-card-section v-show="false">
          <q-checkbox v-model="offlineAgents" label="Offline Agents (Run on next checkin)">
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
    const target = ref("client");
    const monType = ref("all");
    const cmd = ref("");
    const shell = ref("cmd");
    const patchMode = ref("scan");
    const offlineAgents = ref(false);
    const loading = ref(false);

    watch(target, () => (agents.value = []));

    async function submit() {
      loading.value = true;

      const payload = {
        mode: props.mode,
        monType: monType.value,
        target: target.value,
        site: site.value,
        client: client.value,
        agents: agents.value,
        script: script.value,
        timeout: defaultTimeout.value,
        args: defaultArgs.value,
        shell: shell.value,
        cmd: cmd.value,
        patchMode: patchMode.value,
        offlineAgents: offlineAgents.value,
      };

      try {
        const data = await runBulkAction(payload);
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
      if (props.mode === "script") getScriptOptions(showCommunityScripts);
    });

    return {
      // reactive data
      target,
      monType,
      client,
      site,
      agents,
      cmd,
      shell,
      patchMode,
      script,
      scriptOptions,
      timeout: defaultTimeout.value,
      args: defaultArgs.value,
      agentOptions,
      clientOptions,
      siteOptions,
      offlineAgents,
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