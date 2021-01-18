<template>
  <q-dialog ref="dialog" @hide="onHide">
    <div style="width: 900px; max-width: 90vw">
      <q-card>
        <q-bar>
          <q-btn ref="refresh" @click="refresh" class="q-mr-sm" dense flat push icon="refresh" />Alerts Manager
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-md">
          <div class="q-gutter-sm">
            <q-btn ref="new" label="New" dense flat push unelevated no-caps icon="add" @click="showAddTemplateModal" />
            <q-btn
              ref="edit"
              label="Edit"
              :disable="selected.length === 0"
              dense
              flat
              push
              unelevated
              no-caps
              icon="edit"
              @click="showEditTemplateModal(selected[0])"
            />
            <q-btn
              ref="delete"
              label="Delete"
              :disable="selected.length === 0"
              dense
              flat
              push
              unelevated
              no-caps
              icon="delete"
              @click="deleteTemplate(selected[0])"
            />
          </div>
          <q-table
            dense
            :data="templates"
            :columns="columns"
            :pagination.sync="pagination"
            :selected.sync="selected"
            selection="single"
            row-key="id"
            binary-state-sort
            hide-pagination
            :hide-bottom="!!selected"
          >
            <!-- header slots -->
            <template v-slot:header="props">
              <q-tr :props="props">
                <template v-for="col in props.cols">
                  <q-th v-if="col.name === 'active'" auto-width :key="col.name">
                    <q-icon name="power_settings_new" size="1.5em">
                      <q-tooltip>Enable Template</q-tooltip>
                    </q-icon>
                  </q-th>

                  <q-th v-else :key="col.name" :props="props">{{ col.label }}</q-th>
                </template>
              </q-tr>
            </template>
            <!-- No data Slot -->
            <template v-slot:no-data>
              <div class="full-width row flex-center q-gutter-sm">
                <span v-if="templates.length === 0">No Templates</span>
              </div>
            </template>
            <!-- body slots -->
            <template v-slot:body="props">
              <q-tr
                :props="props"
                class="cursor-pointer"
                :class="rowSelectedClass(props.row.id, selected)"
                @click="
                  editTemplateId = props.row.id;
                  props.selected = true;
                "
                @contextmenu="
                  editTemplateId = props.row.id;
                  props.selected = true;
                "
              >
                <!-- context menu -->
                <q-menu context-menu>
                  <q-list dense style="min-width: 200px">
                    <q-item clickable v-close-popup @click="showEditTemplateModal(props.row)" id="context-edit">
                      <q-item-section side>
                        <q-icon name="edit" />
                      </q-item-section>
                      <q-item-section>Edit</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="deleteTemplate(props.row)" id="context-delete">
                      <q-item-section side>
                        <q-icon name="delete" />
                      </q-item-section>
                      <q-item-section>Delete</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup @click="ResetPassword(props.row)" id="context-reset">
                      <q-item-section side>
                        <q-icon name="autorenew" />
                      </q-item-section>
                      <q-item-section>Reset Password</q-item-section>
                    </q-item>

                    <q-item clickable v-close-popup @click="reset2FA(props.row)" id="context-reset">
                      <q-item-section side>
                        <q-icon name="autorenew" />
                      </q-item-section>
                      <q-item-section>Reset Two-Factor Auth</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup>
                      <q-item-section>Close</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
                <!-- enabled checkbox -->
                <q-td>
                  <q-checkbox dense @input="toggleEnabled(props.row)" v-model="props.row.is_active" />
                </q-td>
                <q-td>{{ props.row.name }}</q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
      </q-card>
    </div>
  </q-dialog>
</template>

<script>
import mixins, { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";
import AlertTemplateForm from "@/components/modals/alerts/AlertTemplateForm";

export default {
  name: "AlertsManager",
  mixins: [mixins],
  data() {
    return {
      selected: [],
      templates: [],
      columns: [
        { name: "is_active", label: "Active", field: "is_active", align: "left" },
        { name: "name", label: "Name", field: "name", align: "left" },
        {
          name: "email_severity",
          label: "Email Severity",
          field: "email_severity",
          align: "left",
        },
        {
          name: "text_severity",
          label: "Text Severity",
          field: "text_severity",
          align: "left",
        },
        {
          name: "last_login",
          label: "Last Login",
          field: "last_login",
          align: "left",
        },
      ],
      pagination: {
        rowsPerPage: 9999,
      },
    };
  },
  methods: {
    getTemplates() {
      this.$q.loading.show();
      this.$axios
        .get("alerts/alerttemplates/")
        .then(r => {
          this.templates = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Unable to pull Alert Templates.");
        });
    },
    clearRow() {
      this.selected = [];
    },
    refresh() {
      this.getTemplates();
      this.clearRow();
    },
    deleteTemplate(data) {
      this.$q
        .dialog({
          title: `Delete template ${data.name}?`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$store
            .dispatch("admin/deleteTemplate", data.id)
            .then(response => {
              this.$q.notify(notifySuccessConfig(`Template ${data.name} was deleted!`));
            })
            .catch(error => {
              this.$q.notify(notifyErrorConfig(`An Error occured while deleting template ${data.name}`));
            });
        });
    },
    showEditTemplateModal(data) {
      this.$q.dialog({
        component: AlertTemplateForm,
        parent: this,
        alertTemplate: data,
      });
    },
    showAddTemplateModal() {
      this.clearRow();
      this.$q.dialog({
        component: AlertTemplateForm,
        parent: this,
      });
    },
    toggleEnabled(template) {
      let text = template.is_active ? "Template enabled successfully" : "Template disabled successfully";

      const data = {
        id: template.id,
        is_active: template.is_active,
      };

      this.$axios
        .put("alerts/alerttemplates", data)
        .then(r => {
          this.$q.notifySuccess(text);
        })
        .catch(error => {
          this.$q.notifyError("An Error occured while editing the template");
        });
    },
    rowSelectedClass(id, selected) {
      if (selected.length !== 0 && selected[0].id === id) return this.$q.dark.isActive ? "highlight-dark" : "highlight";
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
  },
  mounted() {
    this.refresh();
  },
};
</script>