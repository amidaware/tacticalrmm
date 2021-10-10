const routes = [
  {
    path: "/",
    name: "Dashboard",
    component: () => import("@/views/Dashboard"),
    meta: {
      requireAuth: true
    }
  },
  {
    path: "/setup",
    name: "InitialSetup",
    component: () => import("@/views/InitialSetup"),
    meta: {
      requireAuth: true
    }
  },
  {
    path: "/totp_setup",
    name: "TOTPSetup",
    component: () => import("@/views/TOTPSetup"),
    meta: {
      requireAuth: true
    }
  },
  {
    path: "/takecontrol/:agent_id",
    name: "TakeControl",
    component: () => import("@/views/TakeControl"),
    meta: {
      requireAuth: true
    }
  },
  {
    path: "/remotebackground/:agent_id",
    name: "RemoteBackground",
    component: () => import("@/views/RemoteBackground"),
    meta: {
      requireAuth: true
    }
  },
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login"),
    meta: {
      requiresVisitor: true
    }
  },
  {
    path: "/expired",
    name: "SessionExpired",
    component: () => import("@/views/SessionExpired")
  },
  { path: "/:catchAll(.*)*", component: () => import("@/views/NotFound") }
]

export default routes
