<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 60vw">
      <q-bar>
        Assigned to {{ template.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
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
          <q-tab name="policies" label="Policies" />
          <q-tab name="clients" label="Clients" />
          <q-tab name="sites" label="Sites" />
        </q-tabs>

        <q-separator />
        <q-scroll-area :thumb-style="thumbStyle" style="height: 50vh">
          <q-tab-panels v-model="tab" :animated="false">
            <q-tab-panel name="policies">
              <q-list separator padding>
                <q-item :key="policy.id" v-for="policy in related.policies">
                  <q-item-section>
                    <q-item-label>{{ policy.name }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-tab-panel>

            <q-tab-panel name="clients">
              <q-list separator padding>
                <q-item :key="client.id" v-for="client in related.clients">
                  <q-item-section>
                    <q-item-label>{{ client.name }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-tab-panel>

            <q-tab-panel name="sites">
              <q-list separator padding>
                <q-item :key="site.id" v-for="site in related.sites">
                  <q-item-section>
                    <q-item-label>{{ site.name }}</q-item-label>
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
  name: "AlertTemplateRelated",
  props: {
    template: !Object,
  },
  data() {
    return {
      tab: "policies",
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
      .get(`/alerts/alerttemplates/${this.template.id}/related/`)
      .then(r => {
        this.$q.loading.hide();
        this.related = r.data;
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError("There was an error getting related templates");
      });
  },
};
</script>