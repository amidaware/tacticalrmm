  <template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="width: 600px; max-width: 80vw">
      <q-bar>
        Service Details - {{ service.display_name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>

      <q-card-section>
        <div class="row">
          <div class="col-3">Service name:</div>
          <div class="col-9">{{ service.name }}</div>
        </div>
        <br />
        <div class="row">
          <div class="col-3">Display name:</div>
          <div class="col-9">{{ service.display_name }}</div>
        </div>
        <br />
        <div class="row">
          <div class="col-3">Description:</div>
          <div class="col-9">
            <q-field outlined :color="$q.dark.isActive ? 'white' : 'black'">{{ service.description }}</q-field>
          </div>
        </div>
        <br />
        <div class="row">
          <div class="col-3">Path:</div>
          <div class="col-9">
            <code>{{ service.binpath }}</code>
          </div>
        </div>
        <br />
        <br />
        <div class="row">
          <div class="col-3">Startup type:</div>
          <div class="col-5">
            <q-select
              dense
              options-dense
              outlined
              v-model="startupType"
              :options="startupOptions"
              map-options
              emit-value
            />
          </div>
        </div>
      </q-card-section>
      <hr />
      <q-card-section>
        <div class="row">
          <div class="col-3">Service status:</div>
          <div class="col-9">{{ service.status }}</div>
        </div>
        <br />
        <div class="row">
          <q-btn-group color="primary" push>
            <q-btn label="Start" @click="sendServiceAction(service, 'start')" />
            <q-btn label="Stop" @click="sendServiceAction(service, 'stop')" />
            <q-btn label="Restart" @click="sendServiceAction(service, 'restart')" />
          </q-btn-group>
        </div>
      </q-card-section>
      <hr />
      <q-card-actions align="right">
        <q-btn flat dense label="Cancel" v-close-popup />
        <q-btn
          :loading="loading"
          :disable="!startupTypeEdited"
          dense
          flat
          label="Save"
          color="primary"
          @click="editServiceStartup"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, computed, onMounted } from "vue";
import { useDialogPluginComponent } from "quasar";
import { editAgentServiceStartType, sendAgentServiceAction } from "@/api/services";
import { notifySuccess } from "@/utils/notify";

// static data
const startupOptions = [
  {
    label: "Automatic (Delayed Start)",
    value: "autodelay",
  },
  {
    label: "Automatic",
    value: "automatic",
  },
  {
    label: "Manual",
    value: "manual",
  },
  {
    label: "Disabled",
    value: "disabled",
  },
];
export default {
  name: "ServiceDetail",
  emits: [...useDialogPluginComponent.emits],
  props: {
    service: !Object,
    agent_id: !String,
  },
  setup(props) {
    // setup quasar dialog plugin
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // services detail
    const startupType = ref("");
    const loading = ref(false);

    const startupTypeEdited = computed(() => {
      if (props.service.start_type.toLowerCase() === "automatic" && props.service.autodelay)
        return startupType.value !== "autodelay";
      else return props.service.start_type.toLowerCase() !== startupType.value;
    });

    async function sendServiceAction(service, action) {
      loading.value = true;
      try {
        const result = await sendAgentServiceAction(props.agent_id, service.name, { sv_action: action });
        notifySuccess(result);
        onDialogOK();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    async function editServiceStartup() {
      const data = {
        startType: startupType.value === "automatic" ? "auto" : startupType.value,
      };

      loading.value = true;
      try {
        const result = await editAgentServiceStartType(props.agent_id, props.service.name, data);
        notifySuccess(result);
        onDialogOK();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    onMounted(() => {
      if (props.service.start_type.toLowerCase() === "automatic" && props.service.autodelay)
        startupType.value = "autodelay";
      else startupType.value = props.service.start_type.toLowerCase();
    });

    return {
      // reactive data
      startupType,
      loading,
      startupTypeEdited,

      // non-reactive data
      startupOptions,

      // methods
      sendServiceAction,
      editServiceStartup,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>
