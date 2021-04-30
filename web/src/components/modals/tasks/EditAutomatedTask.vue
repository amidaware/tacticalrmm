<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        Edit {{ task.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="submit">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            dense
            options-dense
            outlined
            v-model="autotask.script"
            :options="scriptOptions"
            label="Select script"
            map-options
            emit-value
            @input="setScriptDefaults"
          >
            <template v-slot:option="scope">
              <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" v-on="scope.itemEvents" class="q-pl-lg">
                <q-item-section>
                  <q-item-label v-html="scope.opt.label"></q-item-label>
                </q-item-section>
              </q-item>
              <q-item-label v-if="scope.opt.category" v-bind="scope.itemProps" header class="q-pa-sm">{{
                scope.opt.category
              }}</q-item-label>
            </template>
          </q-select>
        </q-card-section>
        <q-card-section>
          <q-select
            dense
            label="Script Arguments (press Enter after typing each argument)"
            filled
            v-model="autotask.script_args"
            use-input
            use-chips
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            dense
            v-model="autotask.name"
            label="Descriptive name of task"
            class="q-pb-none"
          />
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="autotask.alert_severity"
            :options="severityOptions"
            dense
            label="Alert Severity"
            outlined
            map-options
            emit-value
            options-dense
          />
        </q-card-section>
        <q-card-section>
          <q-checkbox
            dense
            label="Collector Task"
            v-model="collector"
            class="q-pb-sm"
            @input="autotask.custom_field = null"
          />
          <q-select
            v-if="collector"
            v-model="autotask.custom_field"
            :options="customFieldOptions"
            dense
            label="Custom Field to update"
            outlined
            map-options
            emit-value
            options-dense
            hint="The return value of script will be saved to custom field selected"
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            dense
            v-model.number="autotask.timeout"
            type="number"
            label="Maximum permitted execution time (seconds)"
            class="q-pb-none"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn flat label="Submit" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";

export default {
  name: "EditAutomatedTask",
  mixins: [mixins],
  props: {
    task: !Object,
  },
  data() {
    return {
      autotask: {
        id: null,
        name: "",
        script: null,
        script_args: [],
        alert_severity: null,
        timeout: 120,
        custom_field: null,
      },
      collector: false,
      customFieldOptions: [],
      scriptOptions: [],
      severityOptions: [
        { label: "Informational", value: "info" },
        { label: "Warning", value: "warning" },
        { label: "Error", value: "error" },
      ],
    };
  },
  computed: {
    ...mapGetters(["showCommunityScripts"]),
  },
  methods: {
    setScriptDefaults() {
      const script = this.scriptOptions.find(i => i.value === this.autotask.script);

      this.autotask.timeout = script.timeout;
      this.autotask.script_args = script.args;
    },
    submit() {
      this.$q.loading.show();

      this.$axios
        .put(`/tasks/${this.autotask.id}/automatedtasks/`, this.autotask)
        .then(r => {
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess("Task was edited successfully");
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
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
  mounted() {
    this.scriptOptions = this.getScriptOptions(this.showCommunityScripts);

    this.getCustomFields("agent").then(r => {
      this.customFieldOptions = r.data.map(field => ({ label: field.name, value: field.id }));
    });

    this.collector = !!this.task.custom_field;

    // copy only certain task props locally
    this.autotask.id = this.task.id;
    this.autotask.name = this.task.name;
    this.autotask.script = this.task.script;
    this.autotask.script_args = this.task.script_args;
    this.autotask.alert_severity = this.task.alert_severity;
    this.autotask.timeout = this.task.timeout;
    this.autotask.custom_field = this.task.custom_field;
  },
};
</script>