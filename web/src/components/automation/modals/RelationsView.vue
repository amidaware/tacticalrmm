<template>
  <q-card style="width: 60vw">
    <q-card-section class="row items-center">
      <div class="text-h6">{{ policy.name }} Relations</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
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
        <q-tab name="clients" label="Clients" ref="clients" />
        <q-tab name="sites" label="Sites" ref="sites" />
        <q-tab name="agents" label="Agents" ref="agents" />
      </q-tabs>

      <q-separator />

      <q-tab-panels v-model="tab" :animated="false">
        <q-tab-panel name="clients">
          <q-list separator padding>
            <q-item :key="item.id" v-for="item in related.clients">
              <q-item-section>
                <q-item-label>{{ item.client }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-tab-panel>

        <q-tab-panel name="sites">
          <q-list separator padding>
            <q-item :key="item.id" v-for="item in related.sites">
              <q-item-section>
                <q-item-label>{{ item.site }}</q-item-label>
                <q-item-label caption>{{ item.client_name }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-tab-panel>

        <q-tab-panel name="agents">
          <q-list separator padding>
            <q-item :key="item.pk" v-for="item in related.agents">
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
    </q-card-section>
  </q-card>
</template>

<script>
export default {
  name: "RelationsView",
  props: {
    policy: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      tab: "clients",
      related: {}
    };
  },
  mounted() {
    this.$q.loading.show();

    this.$store
      .dispatch("automation/getRelated", this.policy.id)
      .then(r => {
        this.$q.loading.hide();
        this.related = r.data;
      })
      .catch(e => {
        this.$q.loading.hide();
      });
  }
};
</script>