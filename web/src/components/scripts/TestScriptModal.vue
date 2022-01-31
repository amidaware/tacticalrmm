<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="min-width: 65vw">
      <q-bar>
        Script Test
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section class="scroll" style="max-height: 70vh; height: 70vh">
        <pre v-if="ret">{{ ret }}</pre>
        <q-inner-loading :showing="loading" />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, onMounted } from "vue";
import { testScript } from "@/api/scripts";
import { useDialogPluginComponent } from "quasar";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown";

export default {
  name: "TestScriptModal",
  emits: [...useDialogPluginComponent.emits],
  components: {
    TacticalDropdown,
  },
  props: {
    script: !Object,
    agent: !String,
  },
  setup(props) {
    // setup quasar dialog plugin
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    // main run script functionality
    const ret = ref(null);
    const loading = ref(false);

    async function runTestScript() {
      loading.value = true;
      const data = {
        code: props.script.script_body,
        timeout: props.script.default_timeout,
        args: props.script.args,
        shell: props.script.shell,
      };
      try {
        ret.value = await testScript(props.agent, data);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    onMounted(runTestScript);

    return {
      // reactive data
      ret,
      loading,

      // methods
      runTestScript,

      // quasar dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>