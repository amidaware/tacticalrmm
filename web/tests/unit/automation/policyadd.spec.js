import { mount, createLocalVue, createWrapper } from "@vue/test-utils";
import Vuex from "vuex";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import "@/quasar.js";

const localVue = createLocalVue();
localVue.use(Vuex);

const related = [
  {
    id: 1,
    name: "Test Policy"
  },
  {
    id: 2,
    name: "Test Policy 2"
  }
];

let state, actions, getters, store;
beforeEach(() => {

  state = {
    policies: [
      ...related,
      {
        id: 3,
        name: "TestPolicy 3"
      }
    ]
  };

  actions = {
    updateRelatedPolicies: jest.fn(),
    loadPolicies: jest.fn(),
    getRelatedPolicies: jest.fn(() => new Promise(res => res({ data: related }))),
  };

  getters = {
    policies: (state) => {
      return state.policies
    }
  };

  store = new Vuex.Store({
    modules: {
      automation: {
        namespaced: true,
        state,
        getters,
        actions
      }
    }
  });

})

describe.each([
  [1, "client"],
  [2, "site"],
  [3, "agent"]
])("PolicyAdd.vue with pk:%i and %s type", (pk, type) => {

  let wrapper;
  beforeEach(() => {
    wrapper = mount(PolicyAdd, {
      localVue,
      store,
      propsData: {
        pk: pk,
        type: type
      }
    });
  });

  it("calls vuex actions on mount", () => {

    expect(actions.loadPolicies).toHaveBeenCalled();
    expect(actions.getRelatedPolicies).toHaveBeenCalledWith(expect.anything(),
      {pk: pk, type: type}
    );

  });

  it("renders title correctly", () => {
    
    expect(wrapper.find(".text-h6").text()).toBe(`Edit policies assigned to ${type}`);
  });

  it("renders correct amount of policies in dropdown", () => {
    
    expect(wrapper.vm.options).toHaveLength(3);
  });

  it("renders correct amount of related policies in selected", () => {
    
    expect(wrapper.vm.selected).toHaveLength(2);
  });

  it("sends correct data on form submit", async () => {
    
    const form = wrapper.findComponent({ ref: "form" });

    await form.vm.$emit("submit");

    expect(actions.updateRelatedPolicies).toHaveBeenCalledWith(expect.anything(),
      { pk: pk, type: type, policies: [1,2] }
    );

  });
});