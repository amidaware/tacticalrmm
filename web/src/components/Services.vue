<template>
  <div class="q-pa-md">
    <q-table
      dense
      class="remote-bg-tbl-sticky"
      :data="servicesData"
      :columns="columns"
      :pagination.sync="pagination"
      :filter="filter"
      row-key="display_name"
      binary-state-sort
      hide-bottom
    >
      <template v-slot:top>
        <q-btn dense flat push @click="refreshServices" icon="refresh" />
        <q-space />
        <q-input v-model="filter" outlined label="Search" dense clearable>
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>
      <template slot="body" slot-scope="props" :props="props">
        <q-tr :props="props">
          <q-menu context-menu>
            <q-list dense style="min-width: 200px">
              <q-item
                clickable
                v-close-popup
                @click="serviceAction(props.row.name, 'start', props.row.display_name)"
              >
                <q-item-section>Start</q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="serviceAction(props.row.name, 'stop', props.row.display_name)"
              >
                <q-item-section>Stop</q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="serviceAction(props.row.name, 'restart', props.row.display_name)"
              >
                <q-item-section>Restart</q-item-section>
              </q-item>
              <q-separator />
              <q-item clickable v-close-popup @click="editService(props.row.name)">
                <q-item-section>Service Details</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <q-td key="display_name" :props="props">
            <q-icon name="fas fa-cogs" />
            &nbsp;&nbsp;&nbsp;{{ props.row.display_name }}
          </q-td>
          <q-td key="start_type" :props="props">{{ props.row.start_type }}</q-td>
          <q-td key="pid" :props="props">{{ props.row.pid }}</q-td>
          <q-td key="status" :props="props">{{ props.row.status }}</q-td>
          <q-td key="username" :props="props">{{ props.row.username }}</q-td>
        </q-tr>
      </template>
    </q-table>

    <q-dialog v-model="serviceDetailsModal">
      <q-card style="width: 600px; max-width: 80vw;">
        <q-card-section>
          <div class="text-h6">Service Details - {{ serviceData.DisplayName }}</div>
        </q-card-section>

        <q-card-section>
          <div class="row">
            <div class="col-3">Service name:</div>
            <div class="col-9">{{ serviceData.svc_name }}</div>
          </div>
          <br />
          <div class="row">
            <div class="col-3">Display name:</div>
            <div class="col-9">{{ serviceData.DisplayName }}</div>
          </div>
          <br />
          <div class="row">
            <div class="col-3">Description:</div>
            <div class="col-9">
              <q-field outlined color="black">{{ serviceData.Description }}</q-field>
            </div>
          </div>
          <br />
          <div class="row">
            <div class="col-3">Path:</div>
            <div class="col-9">
              <code>{{ serviceData.BinaryPath }}</code>
            </div>
          </div>
          <br />
          <br />
          <div class="row">
            <div class="col-3">Startup type:</div>
            <div class="col-5">
              <q-select
                @input="startupTypeChanged"
                dense
                outlined
                v-model="startupType"
                :options="startupOptions"
              />
            </div>
          </div>
        </q-card-section>
        <hr />
        <q-card-section>
          <div class="row">
            <div class="col-3">Service status:</div>
            <div class="col-9">{{ serviceData.Status }}</div>
          </div>
          <br />
          <div class="row">
            <q-btn-group push>
              <q-btn
                color="gray"
                glossy
                text-color="black"
                push
                label="Start"
                @click="serviceAction(serviceData.svc_name, 'start', serviceData.DisplayName)"
              />
              <q-btn
                color="gray"
                glossy
                text-color="black"
                push
                label="Stop"
                @click="serviceAction(serviceData.svc_name, 'stop', serviceData.DisplayName)"
              />
              <q-btn
                color="gray"
                glossy
                text-color="black"
                push
                label="Restart"
                @click="serviceAction(serviceData.svc_name, 'restart', serviceData.DisplayName)"
              />
            </q-btn-group>
          </div>
        </q-card-section>
        <hr />
        <q-card-actions align="left" class="bg-white text-teal">
          <q-btn
            :disable="saveServiceDetailButton"
            dense
            label="Save"
            color="positive"
            @click="changeStartupType(startupType, serviceData.svc_name)"
          />
          <q-btn dense label="Cancel" color="grey" v-close-popup />
        </q-card-actions>
        <q-inner-loading :showing="serviceDetailVisible" />
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "Services",
  props: ["pk"],
  mixins: [mixins],
  data() {
    return {
      servicesData: [],
      serviceDetailsModal: false,
      serviceDetailVisible: false,
      saveServiceDetailButton: true,
      serviceData: {},
      startupType: "",
      startupOptions: ["Automatic (Delayed Start)", "Automatic", "Manual", "Disabled"],
      filter: "",
      pagination: {
        rowsPerPage: 9999,
        sortBy: "display_name",
        descending: false
      },
      columns: [
        {
          name: "display_name",
          label: "Name",
          field: "display_name",
          align: "left",
          sortable: true
        },
        {
          name: "start_type",
          label: "Startup",
          field: "start_type",
          align: "left",
          sortable: true
        },
        {
          name: "pid",
          label: "PID",
          field: "pid",
          align: "left",
          sortable: true
        },
        {
          name: "status",
          label: "Status",
          field: "status",
          align: "left",
          sortable: true
        },
        {
          name: "username",
          label: "Log On As",
          field: "username",
          align: "left",
          sortable: true
        }
      ]
    };
  },
  methods: {
    changeStartupType(startuptype, name) {
      let changed;
      switch (startuptype) {
        case "Automatic (Delayed Start)":
          changed = "autodelay";
          break;
        case "Automatic":
          changed = "auto";
          break;
        case "Manual":
          changed = "manual";
          break;
        case "Disabled":
          changed = "disabled";
          break;
        default:
          changed = "nothing";
      }
      const data = {
        pk: this.pk,
        sv_name: name,
        edit_action: changed
      };
      this.serviceDetailVisible = true;
      axios
        .post("/services/editservice/", data)
        .then(r => {
          this.serviceDetailVisible = false;
          this.serviceDetailsModal = false;
          this.refreshServices();
          this.notifySuccess(`Service ${name} was edited!`);
        })
        .catch(e => {
          this.serviceDetailVisible = false;
          this.notifyError(e.response.data);
        });
    },
    startupTypeChanged() {
      this.saveServiceDetailButton = false;
    },
    editService(name) {
      this.saveServiceDetailButton = true;
      this.serviceDetailsModal = true;
      this.serviceDetailVisible = true;
      axios
        .get(`/services/${this.pk}/${name}/servicedetail/`)
        .then(r => {
          this.serviceData = r.data;
          this.serviceData.svc_name = name;
          this.startupType = this.serviceData.StartType;
          if (this.serviceData.StartType === "Auto" && this.serviceData.StartTypeDelayed === true) {
            this.startupType = "Automatic (Delayed Start)";
          } else if (this.serviceData.StartType === "Auto" && this.serviceData.StartTypeDelayed === false) {
            this.startupType = "Automatic";
          }
          this.serviceDetailVisible = false;
        })
        .catch(e => {
          this.serviceDetailVisible = false;
          this.serviceDetailsModal = false;
          this.notifyError(e.response.data);
        });
    },
    serviceAction(name, action, fullname) {
      let msg, status;
      switch (action) {
        case "start":
          msg = "Starting";
          status = "started";
          break;
        case "stop":
          msg = "Stopping";
          status = "stopped";
          break;
        case "restart":
          msg = "Restarting";
          status = "restarted";
          break;
        default:
          msg = "error";
      }
      this.$q.loading.show({ message: `${msg} service ${fullname}` });
      const data = {
        pk: this.pk,
        sv_name: name,
        sv_action: action
      };
      axios
        .post("/services/serviceaction/", data)
        .then(r => {
          this.refreshServices();
          this.serviceDetailsModal = false;
          this.notifySuccess(`Service ${fullname} was ${status}!`);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
    async getServices() {
      try {
        let r = await axios.get(`/services/${this.pk}/services/`);
        this.servicesData = [r.data][0].services;
      } catch (e) {
        console.log(`ERROR!: ${e}`);
      }
    },
    refreshServices() {
      this.$q.loading.show({ message: "Reloading services..." });
      axios
        .get(`/services/${this.pk}/refreshedservices/`)
        .then(r => {
          this.servicesData = [r.data][0].services;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    }
  },
  created() {
    this.getServices();
  }
};
</script>