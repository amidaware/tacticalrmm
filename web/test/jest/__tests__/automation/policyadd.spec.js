import { mount, createLocalVue } from "test-utils";
import flushpromises from "flush-promises";
import Vuex from "vuex";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import "../../utils/quasar.js";

const localVue = createLocalVue();
localVue.use(Vuex);

const related = {
  server_policy: {
    id: 1,
    name: "Test Policy"
  },
  workstation_policy: {
    id: 1,
    name: "Test Policy"
  }
};

const agentRelated = {
  policy: {
    id: 1,
    name: "Test Policy"
  }
};

let state, actions, getters, store;
beforeEach(() => {

  state = {
    policies: [
      {
        id: 1,
        name: "Test Policy"
      },
      {
        id: 2,
        name: "Test Policy 2"
      },
      {
        id: 3,
        name: "TestPolicy 3"
      }
    ]
  };

  actions = {
    updateRelatedPolicies: jest.fn(),
    loadPolicies: jest.fn(),
    getRelatedPolicies: jest.fn(() => Promise.resolve({ data: related })),
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

  it("calls vuex actions on mount", async () => {

    await flushpromises();
    expect(actions.loadPolicies).toHaveBeenCalled();
    expect(actions.getRelatedPolicies).toHaveBeenCalledWith(expect.anything(),
      { pk: pk, type: type }
    );

  });

  it("renders title correctly", () => {

    expect(wrapper.find(".text-h6").text()).toBe(`Edit policies assigned to ${type}`);
  });

  it("renders correct amount of policies in dropdown", async () => {

    await flushpromises();
    expect(wrapper.vm.options).toHaveLength(3);
  });

  it("renders correct policy in selected", async () => {

    await flushpromises();
    if (type === "client" || type === "site") {
      expect(wrapper.vm.selectedServerPolicy).toStrictEqual({ label: related.server_policy.name, value: related.server_policy.id });
      expect(wrapper.vm.selectedWorkstationPolicy).toStrictEqual({ label: related.workstation_policy.name, value: related.workstation_policy.id });
    }

    // not testing agent
  });

  it("sends correct data on form submit", async () => {

    await flushpromises();
    const form = wrapper.findComponent({ ref: "form" });

    await form.vm.$emit("submit");

    if (type === "client" || type === "site") {
      expect(actions.updateRelatedPolicies).toHaveBeenCalledWith(expect.anything(),
        { pk: pk, type: type, server_policy: 1, workstation_policy: 1 }
      );
    }

    // not testing agent actions

  });
});
