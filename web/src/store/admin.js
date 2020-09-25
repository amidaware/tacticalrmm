import axios from "axios";

export default {
  namespaced: true,
  state: {
    users: []
  },

  getters: {
    users(state) {
      return state.users;
    }
  },

  mutations: {
    setUsers(state, users) {
      state.users = users;
    }
  },

  actions: {
    loadUsers(context) {
      return axios.get("/accounts/users/").then(r => {
        context.commit("setUsers", r.data);
      })
    },
    loadUser(context, pk) {
      return axios.get(`/accounts/${pk}/users/`);
    },
    addUser(context, data) {
      return axios.post("/accounts/users/", data);
    },
    editUser(context, data) {
      return axios.put(`/accounts/${data.id}/users/`, data);
    },
    deleteUser(context, pk) {
      return axios.delete(`/accounts/${pk}/users/`).then(r => {
        context.dispatch("loadUsers");
      });
    },
    resetUserPassword(context, data) {
      return axios.post("/accounts/users/reset/", data);
    },
    resetUserTOTP(context, data) {
      return axios.put("/accounts/users/reset_totp/", data);
    },
    setupTOTP(context, data) {
      return axios.post("/accounts/users/setup_totp/", data);
    }
  }
}
