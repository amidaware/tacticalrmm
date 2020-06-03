import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import Vuex from "vuex";
import PolicyOverview from "@/components/automation/PolicyOverview";
import "@/quasar.js";

const localVue = createLocalVue();
localVue.use(Vuex);

describe("PolicyOverview.vue", () => {

  const policyTreeData = { 
    // node 0
    "Client Name 1": {
      policies: [
        {
          id: 1,
          name: "Policy Name 1",
          active: true
        }
      ],
      sites: {
        // node -1
        "Site Name 1": { policies: []}
      }
    },
    // node -2
    "Client Name 2": {
      policies: [
        {
          id: 2,
          name: "Policy Name 2",
          active: true
        }
      ],
      sites: {
      // node -3
        "Site Name 2": { 
          policies: [
            {
              id: 3,
              name: "Policy Name 3",
              active: false
            }
          ]
        }
      }
    }
  };
   
  let wrapper, actions, mutations, store;

  // Runs before every test
  beforeEach(() => {

    actions = {
      loadPolicyTreeData: jest.fn(() => new Promise(res => res({ data: policyTreeData }))),
      loadPolicyChecks: jest.fn(),
      loadPolicyAutomatedTasks: jest.fn()
    };

    mutations = {
      setSelectedPolicy: jest.fn()
    };

    store = new Vuex.Store({
      modules: {
        automation: {
          namespaced: true,
          mutations,
          actions
        }
      }
    });

    wrapper = mount(PolicyOverview, {
      localVue,
      store,
      stubs: [
        "PolicyChecksTab",
        "PolicyAutomatedTasksTab"
      ]
    });

  });

  // The Tests
  it("calls vuex actions on mount", () => {

    expect(actions.loadPolicyTreeData).toHaveBeenCalled();

  });

  it("renders tree data", () => {

    const tree = wrapper.findComponent({ ref: "tree" });

    const policy1 = tree.vm.getNodeByKey(1);
    const policy2 = tree.vm.getNodeByKey(2);
    const client1 = tree.vm.getNodeByKey(0);
    const client2 = tree.vm.getNodeByKey(-2);
    const site1 = tree.vm.getNodeByKey(-1);
    const site2 = tree.vm.getNodeByKey(-3);

    expect(policy1.label).toBe("Policy Name 1");
    expect(policy2.label).toBe("Policy Name 2");
    expect(client1.label).toBe("Client Name 1");
    expect(client2.label).toBe("Client Name 2");
    expect(site1.label).toBe("Site Name 1");
    expect(site2.label).toBe("Site Name 2");
  });

  it("selects tree node and updates data property with policy",() => {

    // Expected rendered policy node data
    const returnData = {
      icon: "policy",
      id: 1,
      label: "Policy Name 1"
    };

    // Get second tree node which should be the first policy
    wrapper.findAll(".q-tree__node-header").wrappers[1].trigger("click");

    expect(wrapper.vm.selectedPolicy).toStrictEqual(returnData);
    expect(actions.loadPolicyChecks).toHaveBeenCalledWith(expect.anything(), 1);
    expect(mutations.setSelectedPolicy).toHaveBeenCalledWith(expect.anything(), 1);
    expect(actions.loadPolicyAutomatedTasks).toHaveBeenCalledWith(expect.anything(), 1);

  });

});
  
