import Vue from "vue";
import Router from "vue-router";
import Dashboard from "@/components/Dashboard";
import Login from "@/components/Login";
import Logout from "@/components/Logout";
import SessionExpired from "@/components/SessionExpired";
import NotFound from "@/components/NotFound";
import TakeControl from "@/components/TakeControl";
import InitialSetup from "@/components/InitialSetup";
import RemoteBackground from "@/components/RemoteBackground";

Vue.use(Router);

export default new Router({
  mode: "history",
  base: process.env.BASE_URL,
  routes: [
    {
      path: "/",
      name: "Dashboard",
      component: Dashboard,
      meta: {
        requireAuth: true
      }
    },
    {
      path: "/setup",
      name: "InitialSetup",
      component: InitialSetup,
      meta: {
        requireAuth: true
      }
    },
    {
      path: "/takecontrol/:pk",
      name: "TakeControl",
      component: TakeControl,
      meta: {
        requireAuth: true
      }
    },
    {
      path: "/remotebackground/:pk",
      name: "RemoteBackground",
      component: RemoteBackground,
      meta: {
        requireAuth: true
      }
    },
    {
      path: "/login",
      name: "Login",
      component: Login,
      meta: {
        requiresVisitor: true
      }
    },
    {
      path: "/logout",
      name: "Logout",
      component: Logout
    },
    {
      path: "/expired",
      name: "SessionExpired",
      component: SessionExpired,
      meta: {
        requireAuth: true
      }
    },
    { path: "*", component: NotFound }
  ]
});
