import { mount, createWrapper, createLocalVue } from "@vue/test-utils";
import PolicyChecksTab from "@/components/automation/PolicyChecksTab";
import Vuex from "vuex";
import "../../utils/quasar.js"

// Import Test Data
import {
  diskcheck,
  cpuloadcheck,
  memcheck,
  scriptcheck,
  winservicecheck,
  pingcheck,
  eventlogcheck
} from "./data.js";

const localVue = createLocalVue()
localVue.use(Vuex);

const bodyWrapper = createWrapper(document.body);

// This is needed to remove q-dialogs since body doesn't rerender
afterEach(() => {
  const dialogs = document.querySelectorAll(".q-dialog");
  const menus = document.querySelectorAll(".q-menu");
  dialogs.forEach(x => x.remove());
  menus.forEach(x => x.remove());
});

/***   TEST SUITES   ***/
describe("PolicyChecksTab.vue with no policy selected", () => {

  let wrapper, state, getters, store;
  // Runs before every test
  beforeEach(() => {

    // Create the Test store
    state = {
      checks: [],
      selectedPolicy: null
    };

    getters = {
      checks(state) {
        return state.checks
      },
      selectedPolicyPk(state) {
        return state.selectedPolicy
      }
    };

    store = new Vuex.Store({
      modules: {
        automation: {
          namespaced: true,
          state,
          getters
        }
      }
    });

    wrapper = mount(PolicyChecksTab, {
      store,
      localVue
    });
  
  });

  /***   TESTS   ***/
  it("renders text when policy is selected with no checks", () => {

    expect(wrapper.html()).toContain("Click on a policy to see the checks");
  });

  it("doesn't show refresh or add button when no policy selected", () => {

    expect(wrapper.findComponent({ ref: "refresh" }).exists()).toBe(false)
    expect(wrapper.findComponent({ ref: "add" }).exists()).toBe(false)
  });

});

describe("PolicyChecksTab.vue with policy selected and no checks", () => {

  // Used for the add check test loop
  const addChecksMenu = [
    { name: "DiskSpaceCheck", index: 0 },
    { name: "PingCheck", index: 1},
    { name: "CpuLoadCheck", index: 2},
    { name: "MemCheck", index: 3},
    { name: "WinSvcCheck", index: 4},
    { name: "ScriptCheck", index: 5},
    { name: "EventLogCheck", index: 6}
  ];

  let wrapper, store, state, actions, getters;
  // Runs before every test
  beforeEach(() => {

    // Create the Test store
    state = {
      checks: [],
      selectedPolicy: 1
    };

    getters = {
      checks(state) {
        return state.checks
      },
      selectedPolicyPk(state) {
        return state.selectedPolicy
      }
    };

    actions = {
      loadPolicyChecks: jest.fn()
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

    // Mount all sub components except the ones specified
    wrapper = mount(PolicyChecksTab, {
      store,
      localVue,
      stubs: [
        "DiskSpaceCheck",
        "PingCheck",
        "CpuLoadCheck",
        "MemCheck",
        "WinSvcCheck",
        "ScriptCheck",
        "EventLogCheck"
      ]
    });
  
  });

  it("renders text when policy is selected with no checks", () => {

    expect(wrapper.html()).toContain("There are no checks added to this policy");
  });

  it("sends vuex actions on refresh button click", () => {

    wrapper.findComponent({ ref: "refresh" }).trigger("click");
    expect(actions.loadPolicyChecks).toHaveBeenCalledWith(expect.anything(), 1);
  });

  // Create a test for each Add modal
  addChecksMenu.forEach(item => {
    it(`opens ${item.name} Dialog`, async () => {

      const addButton = wrapper.findComponent({ ref: "add" });

      expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
      expect(bodyWrapper.find(".q-menu").exists()).toBe(false);

      await addButton.trigger("click");
      await localVue.nextTick();
      expect(bodyWrapper.find(".q-menu").exists()).toBe(true);

      // Selects correct menu item
      await bodyWrapper.findAll(".q-item").wrappers[item.index].trigger("click");
      expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);
      expect(wrapper.vm.showDialog).toBe(true);
      expect(wrapper.vm.dialogComponent).toBe(item.name);
    });
  
  });

});

describe("PolicyChecksTab.vue with policy selected and checks", () => {

  // Used for the edit check test loop
  const editChecksModals = [
    {name: "DiskSpaceCheck", index: 0, id: 1},
    {name: "CpuLoadCheck", index: 1, id: 2},
    {name: "MemCheck", index: 2, id: 3},
    {name: "ScriptCheck", index: 3, id: 4},
    {name: "WinSvcCheck", index: 4, id: 5},
    {name: "PingCheck", index: 5, id: 6},
    {name: "EventLogCheck", index: 6, id: 7}
  ];

  let state, rootActions, actions, getters, store, wrapper;
  // Runs before every test
  beforeEach(() => {

    // Create the Test store
    state = {
      checks: [
        diskcheck,
        cpuloadcheck,
        memcheck,
        scriptcheck,
        winservicecheck,
        pingcheck,
        eventlogcheck
      ],
      selectedPolicy: 1
    };

    getters = {
      checks(state) {
        return state.checks
      },
      selectedPolicyPk(state) {
        return state.selectedPolicy
      }
    };

    actions = {
      loadPolicyChecks: jest.fn()
    };

    rootActions = {
      editCheckAlert: jest.fn(),
      deleteCheck: jest.fn()
    };

    store = new Vuex.Store({
      actions: rootActions,
      modules: {
        automation: {
          namespaced: true,
          state,
          getters,
          actions
        }
      }
    });

    // Mount all sub components except the ones specified
    wrapper = mount(PolicyChecksTab, {
      store,
      localVue,
      stubs: [
        "DiskSpaceCheck",
        "PingCheck",
        "CpuLoadCheck",
        "MemCheck",
        "WinSvcCheck",
        "ScriptCheck",
        "EventLogCheck",
        "PolicyStatus"
      ]
    });

  });

  /***   TESTS   ***/
  it("renders the correct number of rows based on checks", () => {

    const rows = wrapper.findAll(".q-table > tbody > .q-tr").wrappers;
    expect(rows).toHaveLength(7);
  });

  // Create a test for each Edit modal
  editChecksModals.forEach(item => {
    it(`show ${item.name} Dialog`, async () => {

      expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
      expect(bodyWrapper.find(".q-menu").exists()).toBe(false);

      const row = wrapper.findAll(".q-table > tbody > .q-tr").wrappers[item.index];
      await row.trigger("contextmenu");
      await localVue.nextTick();
      expect(bodyWrapper.find(".q-menu").exists()).toBe(true);
      
      await bodyWrapper.find("#context-edit").trigger("click");
      expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);
      expect(wrapper.vm.showDialog).toBe(true);
      expect(wrapper.vm.dialogComponent).toBe(item.name);
      expect(wrapper.vm.editCheckPK).toBe(item.id);
    });

  });

  it("shows policy status modal on cell click", async () => {

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);

    const row = wrapper.findAll(".status-cell").wrappers[0];
    await row.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);
    expect(wrapper.vm.statusCheck).toEqual(diskcheck);
  });

  it("shows policy status modal on context menu item click", async () => {

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    expect(bodyWrapper.find(".q-menu").exists()).toBe(false);

    const row = wrapper.findAll(".q-table > tbody > .q-tr").wrappers[0];
    await row.trigger("contextmenu");
    await localVue.nextTick();
    expect(bodyWrapper.find(".q-menu").exists()).toBe(true);

    await bodyWrapper.find("#context-status").trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);
    expect(wrapper.vm.statusCheck).toEqual(diskcheck);
  });

  it("deletes check", async () => {

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    expect(bodyWrapper.find(".q-menu").exists()).toBe(false);

    const row = wrapper.findAll(".q-table > tbody > .q-tr").wrappers[0];
    await row.trigger("contextmenu");
    await localVue.nextTick();
    expect(bodyWrapper.find(".q-menu").exists()).toBe(true);

    await bodyWrapper.find("#context-delete").trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

    //Get OK button on confirmation dialog and click it
    await bodyWrapper.findAll(".q-btn").wrappers[1].trigger("click");

    expect(rootActions.deleteCheck).toHaveBeenCalledWith(expect.anything(), 1);
    expect(actions.loadPolicyChecks).toHaveBeenCalled();

  });

  it("enables and disables text alerts for check", async () => {

    //Get first checkbox in first row
    const row = wrapper.findAll(".q-checkbox").wrappers[0];

    //Enable Text Alert
    await row.trigger("click");

    expect(rootActions.editCheckAlert).toHaveBeenCalledWith(
      expect.anything(), 
      { 
        pk: 1,
          data: {
            text_alert: true,
            check_alert: true
          }
      }
      );

    //Disable Text Alert
    await row.trigger("click");

    expect(rootActions.editCheckAlert).toHaveBeenCalledWith(     
      expect.anything(), 
      { 
        pk: 1,
          data: {
            text_alert: false,
            check_alert: true
          }
      }
    );

  });

  it("enables and disables email alerts for check", async () => {

    //Get second checkbox in first row
    const row = wrapper.findAll(".q-checkbox").wrappers[1];

    //Enable Text Alert
    await row.trigger("click");

    expect(rootActions.editCheckAlert).toHaveBeenCalledWith(
      expect.anything(), 
      { 
        pk: 1,
          data: {
            email_alert: true,
            check_alert: true
          }
      }
    );

    //Disable Text Alert
    await row.trigger("click");

    expect(rootActions.editCheckAlert).toHaveBeenCalledWith(
      expect.anything(), 
      { 
        pk: 1,
          data: {
            email_alert: false,
            check_alert: true
          }
      }
    );
  });

  /* TODO: test @close and @hide events */
});
