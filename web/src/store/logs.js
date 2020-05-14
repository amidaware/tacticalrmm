export default {
    namespaced: true,
    state: {
        toggleLogModal: false
    },
    mutations: {
        TOGGLE_LOG_MODAL(state, action) {
            state.toggleLogModal = action;
        }
    }
}