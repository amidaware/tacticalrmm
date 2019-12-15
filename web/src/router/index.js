import Vue from "vue";
import Router from "vue-router";
import Dashboard from "@/views/Dashboard";
import Login from "@/views/Login";
import Logout from "@/views/Logout";
import SessionExpired from "@/views/SessionExpired";
import NotFound from "@/views/NotFound";
import TakeControl from "@/views/TakeControl";
import InitialSetup from "@/views/InitialSetup";
import RemoteBackground from "@/views/RemoteBackground";

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
