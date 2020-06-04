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
    path: "/takecontrol/:pk",
    name: "TakeControl",
    component: () => import("@/views/TakeControl"),
    meta: {
      requireAuth: true
    }
  },
  {
    path: "/remotebackground/:pk",
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
    path: "/logout",
    name: "Logout",
    component: () => import("@/views/Logout")
  },
  {
    path: "/expired",
    name: "SessionExpired",
    component: () => import("@/views/SessionExpired"),
    meta: {
      requireAuth: true
    }
  },
  { path: "*", component: () => import("@/views/NotFound") }
]

export default routes
