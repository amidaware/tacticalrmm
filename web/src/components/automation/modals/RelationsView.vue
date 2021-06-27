<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 60vw">
      <q-bar>
        {{ policy.name }} Relations
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section
        class="row items-center"
        v-if="related.default_server_policy || related.default_workstation_policy"
      >
        <div v-if="related.default_server_policy" class="text-body">
          <q-icon name="error_outline" color="info" size="1.5em" />This policy is set as the Default Server Policy.
        </div>
        <div v-if="related.default_workstation_policy" class="text-body">
          <q-icon name="error_outline" color="info" size="1.5em" />This policy is set as the Default Workstation Policy.
        </div>
      </q-card-section>
      <q-card-section>
        <q-tabs
          v-model="tab"
          dense
          inline-label
          class="text-grey"
          active-color="primary"
          indicator-color="primary"
          align="left"
          narrow-indicator
          no-caps
        >
          <q-tab name="clients" label="Clients" />
          <q-tab name="sites" label="Sites" />
          <q-tab name="agents" label="Agents" />
        </q-tabs>

        <q-separator />
        <q-scroll-area :thumb-style="thumbStyle" style="height: 50vh">
          <q-tab-panels v-model="tab" :animated="false">
            <q-tab-panel name="clients">
              <q-list separator padding>
                <q-item v-for="item in related.server_clients" :key="item.id + 'servers'">
                  <q-item-section>
                    <q-item-label>{{ item.name }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-item-label>
                      <i>Applied to Servers</i>
                    </q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-for="item in related.workstation_clients" :key="item.id + 'workstations'">
                  <q-item-section>
                    <q-item-label>{{ item.name }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-item-label>
                      <i>Applied to Workstations</i>
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-tab-panel>

            <q-tab-panel name="sites">
              <q-list separator padding>
                <q-item v-for="item in related.server_sites" :key="item.id + 'servers'">
                  <q-item-section>
                    <q-item-label>{{ item.name }}</q-item-label>
                    <q-item-label caption>{{ item.client_name }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-item-label>
                      <i>Applied to Servers</i>
                    </q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-for="item in related.workstation_sites" :key="item.id + 'workstations'">
                  <q-item-section>
                    <q-item-label>{{ item.name }}</q-item-label>
                    <q-item-label caption>{{ item.client_name }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-item-label>
                      <i>Applied to Workstations</i>
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-tab-panel>

            <q-tab-panel name="agents">
              <q-list separator padding>
                <q-item v-for="item in related.agents" :key="item.pk">
                  <q-item-section>
                    <q-item-label>{{ item.hostname }}</q-item-label>
                    <q-item-label caption>
                      <b>{{ item.client }}</b>
                      {{ item.site }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-tab-panel>
          </q-tab-panels>
        </q-scroll-area>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
export default {
  name: "RelationsView",
  emits: ["hide", "ok", "cancel"],
  props: {
    policy: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      tab: "clients",
      related: {},
      thumbStyle: {
        right: "2px",
        borderRadius: "5px",
        backgroundColor: "#027be3",
        width: "5px",
        opacity: 0.75,
      },
    };
  },
  methods: {
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
    this.$q.loading.show();

    this.$axios
      .get(`/automation/policies/${this.policy.id}/related/`)
      .then(r => {
        this.$q.loading.hide();
        this.related = r.data;
      })
      .catch(e => {
        this.$q.loading.hide();
      });
  },
};
</script>