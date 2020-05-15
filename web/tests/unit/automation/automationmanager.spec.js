import { mount, createLocalVue, createWrapper } from "@vue/test-utils";
import Vuex from "vuex";
import AutomationManager from "@/components/automation/AutomationManager";
import "@/quasar.js"

const localVue = createLocalVue();
localVue.use(Vuex);

describe("AutomationManager.vue", () => {

  const policiesData = [
    {
      id: 1,
      name: "Test Policy",
      desc: "Description",
      active: true,
      clients: [],
      sites: [{}, {}],
      agents: [{}]
    },
    {
      id: 2,
      name: "Test Policy 2",
      desc: "Description 2",
      active: false,
      clients: [],
      sites: [{}, {}],
      agents: [{}]
    }
  ];

  const bodyWrapper = createWrapper(document.body);
  let wrapper;
  let state, mutations, actions, store;

  // Runs before every test
  beforeEach(() => {

    // Create the Test store
    state = {
      selectedPolicy: null,
      checks: {},
      automatedTasks: {},
      policies: policiesData,
    };

    mutations = {
      setSelectedPolicy: jest.fn((state, key) => { state.selectedPolicy = key }),
      setPolicyChecks: jest.fn(),
      setPolicyAutomatedTasks: jest.fn(),

    };

    actions = {
      loadPolicies: jest.fn(),
      loadPolicyChecks: jest.fn(),
      loadPolicyAutomatedTasks: jest.fn(),
      deletePolicy: jest.fn()
    };

    store = new Vuex.Store({
      modules: {
        automation: {
          namespaced: true,
          state,
          mutations,
          actions
        }
      }
    });

    // Mount all sub components except the ones specified
    wrapper = mount(AutomationManager, {
      store,
      localVue,
      stubs: [
        "PolicySubTableTabs",
        "PolicyForm"
      ],
    });

  });


  // Runs after every test
  // This is needed to remove q-dialogs since body doesn't rerender
  afterEach(() => {
    const dialogs = document.querySelectorAll(".q-dialog");
    dialogs.forEach(x => x.remove());
  });


  // The Tests
  it("calls vuex loadPolicies action on mount", () => {

    expect(actions.loadPolicies).toHaveBeenCalled();

  });

  it("renders table when policies is set from store computed", () => {

    const rows = wrapper.findAll("tbody > tr.q-tr").wrappers;
    expect(rows).toHaveLength(2);

  });

  it("sends vuex mutations and actions when policy is selected", () => {

    const row = wrapper.findAll("tbody > tr.q-tr").wrappers[1];

    row.trigger("click");

    expect(mutations.setSelectedPolicy).toHaveBeenCalledWith(expect.anything(), 2);
    expect(actions.loadPolicyChecks).toHaveBeenCalledWith(expect.anything(), 2);
    expect(actions.loadPolicyAutomatedTasks).toHaveBeenCalledWith(expect.anything(), 2);

  });

  it("shows edit policy modal on edit button press", async () => {

    const button = wrapper.findComponent({ ref: "edit" });

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    await button.trigger("click")
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);

    //Select Row
    await wrapper.find("tbody > tr.q-tr").trigger("click");
    await button.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

  });

  it("shows add policy modal on button press", async () => {

    const button = wrapper.findComponent({ ref: "new" });

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    await button.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

  });

  it("deletes selected policy", async () => {

    const button = wrapper.findComponent({ ref: "delete" });

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    // Select Row
    await wrapper.find("tbody > tr.q-tr").trigger("click");
    await button.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

    //Get OK button and click it
    bodyWrapper.findAll(".q-btn").wrappers[1].trigger("click");

    expect(actions.deletePolicy).toHaveBeenCalledWith(expect.anything(), 1);

  });

  it("shows overview modal when button clicked", async () => {

    const button = wrapper.findComponent({ ref: "overview" });

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    await button.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);
  });

  it("calls vuex loadPolicies action when refresh button clicked and clears selected", () => {

    const button = wrapper.findComponent({ ref: "refresh" });

    button.trigger("click");
    expect(actions.loadPolicies).toHaveBeenCalled();
    expect(mutations.setSelectedPolicy).toHaveBeenCalledWith(expect.anything(), null);
    expect(mutations.setPolicyChecks).toHaveBeenCalledWith(expect.anything(), {});
    expect(mutations.setPolicyAutomatedTasks).toHaveBeenCalledWith(expect.anything(), {});

  });

});
