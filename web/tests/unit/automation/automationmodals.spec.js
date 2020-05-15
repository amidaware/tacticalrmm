import { mount, createLocalVue } from "@vue/test-utils";
import Vuex from "vuex";
import PolicyForm from "@/components/automation/modals/PolicyForm";
import "@/quasar.js"

const localVue = createLocalVue();
localVue.use(Vuex);

describe("PolicyForm.vue", () => {

  const clients = [];
  const sites = [];
  const agents = [];

  const policy = {
    id: 1,
    name: "Test Policy",
    active: true,
    clients: [{id: 1, client: "Test Name"}],
    sites: [{id: 1, site: "Test Name"}],
    agents: [{pk: 1, hostname: "Test Name"}]
  };

  let methods;
  let actions, rootActions, store;

  // Runs before every test
  beforeEach(() => {

    methods = {
      notifyError: () => jest.fn()
    };

    rootActions = {
      loadClients: jest.fn(() => new Promise(res => res({ data: clients }))),
      loadSites: jest.fn(() => new Promise(res => res({ data: sites }))),
      loadAgents: jest.fn(() => new Promise(res => res({ data: agents }))),
    };

    actions = {
      loadPolicy: jest.fn(() => new Promise(res => res({ data: policy }))),
      addPolicy: jest.fn(() => new Promise(res => res())),
      editPolicy: jest.fn(() => new Promise(res => res())),
    };

    store = new Vuex.Store({
      actions: rootActions,
      modules: {
        automation: {
          namespaced: true,
          actions,
        }
      }
    });

  });

  // The Tests
  it("calls vuex actions on mount", () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
    });

    expect(rootActions.loadClients).toHaveBeenCalled();
    expect(rootActions.loadSites).toHaveBeenCalled();
    expect(rootActions.loadAgents).toHaveBeenCalled();

    // Not called unless pk prop is set
    expect(actions.loadPolicy).not.toHaveBeenCalled();

  });

  it("calls vuex actions on mount with pk prop set", () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
      propsData: {
        pk: 1
      }
    });

    expect(rootActions.loadClients).toHaveBeenCalled();
    expect(rootActions.loadSites).toHaveBeenCalled();
    expect(rootActions.loadAgents).toHaveBeenCalled();
    expect(actions.loadPolicy).toHaveBeenCalled();

  });

  /*it("renders the client, site, and agent dropdowns correctly", async () => {

  })*/
  
  it("sends the correct add action on submit", async () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
      methods: methods
    });

    wrapper.setData({name: "Test Name"});
    const form = wrapper.findComponent({ ref: "form" });
    form.vm.$emit("submit");
    await wrapper.vm.$nextTick();
    
    expect(actions.addPolicy).toHaveBeenCalled();
    expect(actions.editPolicy).not.toHaveBeenCalled();

  });

  it("sends the correct edit action on submit", async () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
      propsData: {
        pk: 1
      },
      methods: methods
    });

    wrapper.setData({name: "TestName"})
    const form = wrapper.findComponent({ ref: "form" });
    form.vm.$emit("submit");
    await wrapper.vm.$nextTick();

    expect(actions.addPolicy).not.toHaveBeenCalled();
    expect(actions.editPolicy).toHaveBeenCalled();
    
  });
  
  it("sends error when name isn't set on submit", async () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
      methods: methods
    });

    const form = wrapper.findComponent({ ref: "form" });
    form.vm.$emit("submit");
    await wrapper.vm.$nextTick();

    expect(actions.addPolicy).not.toHaveBeenCalled();
    expect(actions.editPolicy).not.toHaveBeenCalled();
  });

  it("Renders correct title on edit", () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
      propsData: {
        pk: 1
      }
    });

    expect(wrapper.vm.title).toBe("Edit Policy");
  });

  it("Renders correct title on add", () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
    });

    expect(wrapper.vm.title).toBe("Add Policy");
  });

});
  
