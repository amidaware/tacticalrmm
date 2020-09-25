import { mount, createLocalVue } from "@vue/test-utils";
import Vuex from "vuex";
import PolicyOverview from "@/components/automation/PolicyOverview";
import "../../utils/quasar.js";

const localVue = createLocalVue();
localVue.use(Vuex);

describe("PolicyOverview.vue", () => {

  const policyTreeData = [
    {
      // node 0
      client: "Client Name 1",
      workstation_policy: {
        id: 1,
        name: "Policy Name 1",
        active: true
      },
      server_policy: null,
      // node -1
      sites: [
        {
          site: "Site Name 1",
          server_policy: null,
          workstation_policy: null
        }
      ]
    },
    {
      // node -2
      client: "Client Name 2",
      server_policy: {
        id: 2,
        name: "Policy Name 2",
        active: true
      },
      workstation_policy: null,
      sites: [
        {
          // node -3
          site: "Site Name 2",
          workstation_policy: {
            id: 3,
            name: "Policy Name 3",
            active: false
          },
          server_policy: {
            id: 3,
            name: "Policy Name 3",
            active: false
          }
        }
      ]
    }
  ];

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

  it("renders tree data", async () => {

    await localVue.nextTick();

    const tree = wrapper.findComponent({ ref: "tree" });

    const policy1 = tree.vm.getNodeByKey(1);
    const policy2 = tree.vm.getNodeByKey(2);
    const policy3 = tree.vm.getNodeByKey(3);
    const client1 = tree.vm.getNodeByKey(0);
    const client2 = tree.vm.getNodeByKey(-2);
    const site1 = tree.vm.getNodeByKey(-1);
    const site2 = tree.vm.getNodeByKey(-3);

    expect(policy1.label).toBe("Policy Name 1 (Workstations)");
    expect(policy2.label).toBe("Policy Name 2 (Servers)");
    expect(policy3.label).toBe("Policy Name 3 (Workstations) (disabled)");
    expect(client1.label).toBe("Client Name 1");
    expect(client2.label).toBe("Client Name 2");
    expect(site1.label).toBe("Site Name 1");
    expect(site2.label).toBe("Site Name 2");
  });

  it("selects tree node and updates data property with policy", async () => {

    // Expected rendered policy node data
    const returnData = {
      icon: "policy",
      id: 1,
      label: "Policy Name 1 (Workstations)"
    };

    await localVue.nextTick();

    // Get second tree node which should be the first policy
    wrapper.findAll(".q-tree__node-header").wrappers[1].trigger("click");

    expect(wrapper.vm.selectedPolicy).toStrictEqual(returnData);
    expect(actions.loadPolicyChecks).toHaveBeenCalledWith(expect.anything(), 1);
    expect(mutations.setSelectedPolicy).toHaveBeenCalledWith(expect.anything(), 1);
    expect(actions.loadPolicyAutomatedTasks).toHaveBeenCalledWith(expect.anything(), 1);

  });

});

