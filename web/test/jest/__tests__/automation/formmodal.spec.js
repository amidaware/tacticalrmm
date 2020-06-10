import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import Vuex from "vuex";
import PolicyForm from "@/components/automation/modals/PolicyForm";
import "../../utils/quasar.js";

const localVue = createLocalVue();
localVue.use(Vuex);

/***   TEST DATA   ***/
const policy = {
  id: 1,
  name: "Test Policy",
  desc: "Test Desc",
  enforced: false,
  active: true
};

let actions, rootActions, store;
beforeEach(() => {

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
})

/***   TEST SUITES   ***/
describe("PolicyForm.vue when editting", () => {

  let wrapper;
  beforeEach(() => {

    wrapper = mount(PolicyForm, {
      localVue,
      store,
      propsData: {
        pk: 1
      }
    });

  });

  /***   TESTS   ***/
  it("calls vuex actions on mount with pk prop set", () => {

    expect(actions.loadPolicy).toHaveBeenCalledWith(expect.anything(), 1);

  });

  it("sends the correct edit action on submit", async () => {

    await flushPromises();
    const form = wrapper.findComponent({ ref: "form" });
    form.vm.$emit("submit");
    await wrapper.vm.$nextTick();

    expect(actions.addPolicy).not.toHaveBeenCalled();
    expect(actions.editPolicy).toHaveBeenCalledWith(expect.anything(), policy);
    
  });

  it("Renders correct title on edit", () => {

    expect(wrapper.vm.title).toBe("Edit Policy");
  });

});
  
describe("PolicyForm.vue when adding", () => {

  let wrapper;
  beforeEach(() => {

    wrapper = mount(PolicyForm, {
      localVue,
      store
    });

  });

  /***   TESTS   ***/
  it("calls vuex actions on mount", () => {

    // Not called unless pk prop is set
    expect(actions.loadPolicy).not.toHaveBeenCalled();

  });

  it("sends the correct add action on submit", async () => {

    wrapper.setData({name: "Test Policy"});
    const form = wrapper.findComponent({ ref: "form" });
    form.vm.$emit("submit");
    await wrapper.vm.$nextTick();
    
    expect(actions.addPolicy).toHaveBeenCalled();
    expect(actions.editPolicy).not.toHaveBeenCalled();

  });

  it("sends error when name isn't set on submit", async () => {

    const form = wrapper.findComponent({ ref: "form" });
    form.vm.$emit("submit");
    await wrapper.vm.$nextTick();

    expect(actions.addPolicy).not.toHaveBeenCalled();
    expect(actions.editPolicy).not.toHaveBeenCalled();
  });

  it("Renders correct title on add", () => {

    expect(wrapper.vm.title).toBe("Add Policy");
  });

});