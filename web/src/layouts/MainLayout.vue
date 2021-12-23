<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-grey-9 text-white">
      <q-banner v-if="needRefresh" inline-actions class="bg-red text-white text-center">
        You are viewing an outdated version of this page.
        <q-btn color="dark" icon="refresh" label="Refresh" @click="$store.dispatch('reload')" />
      </q-banner>
      <q-toolbar>
        <q-btn
          dense
          flat
          @click="$store.dispatch('refreshDashboard')"
          icon="refresh"
          v-if="$route.name === 'Dashboard'"
        />
        <q-btn v-else dense flat @click="$router.push({ name: 'Dashboard' })" icon="dashboard">
          <q-tooltip>Back to Dashboard</q-tooltip>
        </q-btn>
        <q-toolbar-title>
          Tactical RMM<span class="text-overline q-ml-sm">v{{ currentTRMMVersion }}</span>
          <span class="text-overline q-ml-md" v-if="latestTRMMVersion && currentTRMMVersion !== latestTRMMVersion"
            ><q-badge color="warning"
              ><a :href="latestReleaseURL" target="_blank">v{{ latestTRMMVersion }} available</a></q-badge
            ></span
          >
        </q-toolbar-title>

        <!-- temp dark mode toggle -->
        <q-toggle v-model="darkMode" class="q-mr-sm" checked-icon="nights_stay" unchecked-icon="wb_sunny" />

        <!-- Devices Chip -->
        <q-chip class="cursor-pointer">
          <q-avatar size="md" icon="devices" color="primary" />
          <q-tooltip :delay="600" anchor="top middle" self="top middle">Agent Count</q-tooltip>
          {{ serverCount + workstationCount }}
          <q-menu>
            <q-list dense>
              <q-item-label header>Servers</q-item-label>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="fa fa-server" size="sm" color="primary" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Total: {{ serverCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="power_off" size="sm" color="negative" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Offline: {{ serverOfflineCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item-label header>Workstations</q-item-label>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="computer" size="sm" color="primary" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Total: {{ workstationCount }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="power_off" size="sm" color="negative" />
                </q-item-section>

                <q-item-section no-wrap>
                  <q-item-label>Offline: {{ workstationOfflineCount }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <AlertsIcon />

        <q-btn-dropdown flat no-caps stretch :label="user">
          <q-list>
            <q-item clickable v-ripple @click="showUserPreferences" v-close-popup>
              <q-item-section>
                <q-item-label>Preferences</q-item-label>
              </q-item-section>
            </q-item>
            <q-item to="/expired" exact>
              <q-item-section>
                <q-item-label>Logout</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </q-toolbar>
    </q-header>
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>
<script>
// composition imports
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useQuasar } from "quasar";
import { useStore } from "vuex";
import axios from "axios";
import { getBaseUrl } from "@/boot/axios";

// ui imports
import AlertsIcon from "@/components/AlertsIcon";
import UserPreferences from "@/components/modals/coresettings/UserPreferences";

export default {
  name: "MainLayout",
  components: { AlertsIcon },
  setup(props) {
    const store = useStore();
    const $q = useQuasar();

    const darkMode = computed({
      get: () => {
        return $q.dark.isActive;
      },
      set: value => {
        axios.patch("/accounts/users/ui/", { dark_mode: value }).catch(e => {});
        $q.dark.set(value);
      },
    });

    const currentTRMMVersion = computed(() => store.state.currentTRMMVersion);
    const latestTRMMVersion = computed(() => store.state.latestTRMMVersion);
    const needRefresh = computed(() => store.state.needRefresh);
    const user = computed(() => store.state.username);
    const token = computed(() => store.state.token);

    const latestReleaseURL = computed(() => {
      return latestTRMMVersion.value
        ? `https://github.com/wh1te909/tacticalrmm/releases/tag/v${latestTRMMVersion.value}`
        : "";
    });

    function showUserPreferences() {
      $q.dialog({
        component: UserPreferences,
      }).onOk(() => store.dispatch("getDashInfo"));
    }

    function wsUrl() {
      return getBaseUrl().split("://")[1];
    }

    const serverCount = ref(0);
    const serverOfflineCount = ref(0);
    const workstationCount = ref(0);
    const workstationOfflineCount = ref(0);

    const ws = ref(null);

    function setupWS() {
      console.log("Starting websocket");
      const proto = process.env.NODE_ENV === "production" || process.env.DOCKER_BUILD ? "wss" : "ws";
      ws.value = new WebSocket(`${proto}://${wsUrl()}/ws/dashinfo/?access_token=${token.value}`);
      ws.value.onopen = e => {
        console.log("Connected to ws");
      };
      ws.value.onmessage = e => {
        const data = JSON.parse(e.data);
        serverCount.value = data.total_server_count;
        serverOfflineCount.value = data.total_server_offline_count;
        workstationCount.value = data.total_workstation_count;
        workstationOfflineCount.value = data.total_workstation_offline_count;
      };
      ws.value.onclose = e => {
        try {
          console.log(`Closed code: ${e.code}`);
          if (e.code !== 1000 && e.code) {
            console.log("Retrying websocket connection...");
            setTimeout(() => {
              setupWS();
            }, 2 * 1000);
          }
        } catch (e) {
          console.log("Websocket connection closed");
        }
      };
      ws.value.onerror = err => {
        console.log("There was an error");
        ws.value.onclose();
      };
    }

    const poll = ref(null);
    function livePoll() {
      poll.value = setInterval(() => {
        store.dispatch("checkVer");
        store.dispatch("getDashInfo", false);
      }, 60 * 5 * 1000);
    }

    onMounted(() => {
      setupWS();
      store.dispatch("getDashInfo");
      store.dispatch("checkVer");

      livePoll();
    });

    onBeforeUnmount(() => {
      ws.value.close();
      clearInterval(poll.value);
    });

    return {
      // reactive data
      serverCount,
      serverOfflineCount,
      workstationCount,
      workstationOfflineCount,
      latestReleaseURL,
      currentTRMMVersion,
      latestTRMMVersion,
      user,
      needRefresh,
      darkMode,

      // methods
      showUserPreferences,
    };
  },
};
</script>