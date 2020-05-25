import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import Vuex from "vuex";
import PolicyForm from "@/components/automation/modals/PolicyForm";
import "@/quasar.js";

const localVue = createLocalVue();
localVue.use(Vuex);

describe("PolicyForm.vue", () => {

  const clients = [ 
    {
      id: 1, 
      client: "Test Client"
    }, 
    {
      id: 2, 
      client: "Test Client2"
    },
    {
      id: 3, 
      client: "Test Client3"
    } 
  ];
  const sites = [ 
    {
      id: 1, 
      site: "Site Name", 
      client_name: "Test Client"
    }, 
    {
      id: 2, 
      site: "Site Name2", 
      client_name: "Test Client2"
    } 
  ];

  const policy = {
    id: 1,
    name: "Test Policy",
    desc: "Test Desc",
    active: true,
    clients: [],
    sites: []
  };

  let actions, rootActions, store;

  // Runs before every test
  beforeEach(() => {

    rootActions = {
      loadClients: jest.fn(() => new Promise(res => res({ data: clients }))),
      loadSites: jest.fn(() => new Promise(res => res({ data: sites }))),
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
      store
    });

    expect(rootActions.loadClients).toHaveBeenCalled();
    expect(rootActions.loadSites).toHaveBeenCalled();

    // Not called unless pk prop is set
    expect(actions.loadPolicy).not.toHaveBeenCalled();

  });

  it("calls vuex actions on mount with pk prop set", () => {

    mount(PolicyForm, {
      localVue,
      store,
      propsData: {
        pk: 1
      }
    });

    expect(rootActions.loadClients).toHaveBeenCalled();
    expect(rootActions.loadSites).toHaveBeenCalled();
    expect(actions.loadPolicy).toHaveBeenCalledWith(expect.anything(), 1);

  });

  it("Sets client and site options correctly", async () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store
    });

    // Make sure the promises are resolved
    await flushPromises();

    expect(wrapper.vm.clientOptions).toHaveLength(3);
    expect(wrapper.vm.siteOptions).toHaveLength(2);

  });
  
  it("sends the correct add action on submit", async () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store
    });

    wrapper.setData({name: "Test Policy"});
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
      }
    });

    await flushPromises();
    const form = wrapper.findComponent({ ref: "form" });
    form.vm.$emit("submit");
    await wrapper.vm.$nextTick();

    expect(actions.addPolicy).not.toHaveBeenCalled();
    expect(actions.editPolicy).toHaveBeenCalledWith(expect.anything(), policy);
    
  });
  
  it("sends error when name isn't set on submit", async () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store
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
  
