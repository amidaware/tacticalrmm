import { mount, shallowMount, createWrapper, createLocalVue } from "@vue/test-utils";
import PolicyAutomatedTasksTab from "@/components/automation/PolicyAutomatedTasksTab";
import Vuex from "vuex";
import "../../utils/quasar.js";

// Import Test Data
import {
  tasks
} from "./data.js";

const localVue = createLocalVue();
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
describe("PolicyAutomatedTasksTab.vue with no policy selected", () => {

  let wrapper, state, getters, store;
  // Runs before every test
  beforeEach(() => {

    // Create the Test store
    state = {
      automatedTasks: {},
      selectedPolicy: null
    };

    getters = {
      tasks(state) {
        return state.automatedTasks.autotasks;
      },
      selectedPolicyPk(state) {
        return state.selectedPolicy;
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

    wrapper = shallowMount(PolicyAutomatedTasksTab, {
      store,
      localVue
    });
  
  });

  /***   TESTS   ***/
  it("renders text when policy is selected with no tasks", () => {

    expect(wrapper.html()).toContain("No Policy Selected");
  });

});

describe("PolicyAutomatedTasksTab.vue with policy selected and no tasks", () => {

  let wrapper, store, state, actions, getters;
  // Runs before every test
  beforeEach(() => {

    // Create the Test store
    state = {
      automatedTasks: {
        autotasks: []
      },
      selectedPolicy: 1
    };

    getters = {
      tasks(state) {
        return state.automatedTasks.autotasks;
      },
      selectedPolicyPk(state) {
        return state.selectedPolicy;
      }
    };

    actions = {
      loadPolicyAutomatedTasks: jest.fn()
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
    wrapper = mount(PolicyAutomatedTasksTab, {
      store,
      localVue,
      stubs: [
        "AddAutomatedTask",
        "PolicyStatus"
      ]
    });
  
  });

  it("renders text when policy is selected with no tasks", () => {

    expect(wrapper.html()).toContain("No Tasks");
  });

  it("sends vuex actions on refresh button click", () => {

    wrapper.findComponent({ ref: "refresh" }).trigger("click");
    expect(actions.loadPolicyAutomatedTasks).toHaveBeenCalledWith(expect.anything(), 1);
  });

  it(`opens AddAutomatedTask Dialog`, async () => {

    const addButton = wrapper.findComponent({ ref: "add" });

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    expect(bodyWrapper.find(".q-menu").exists()).toBe(false);

    await addButton.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

  });

});

describe("PolicyChecksTab.vue with policy selected and checks", () => {

  let state, rootActions, actions, getters, store, wrapper;
  // Runs before every test
  beforeEach(() => {

    // Create the Test store
    state = {
      automatedTasks: {
        autotasks: tasks
      },
      selectedPolicy: 1
    };

    getters = {
      tasks(state) {
        return state.automatedTasks.autotasks;
      },
      selectedPolicyPk(state) {
        return state.selectedPolicy;
      }
    };

    actions = {
      loadPolicyAutomatedTasks: jest.fn(),
      runPolicyTask: jest.fn()
    };

    rootActions = {
      editAutoTask: jest.fn(),
      deleteAutoTask: jest.fn()
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
    wrapper = mount(PolicyAutomatedTasksTab, {
      store,
      localVue,
      stubs: [
        "AddAutomatedTask",
        "PolicyStatus"
      ]
    });

  });

  /***   TESTS   ***/
  it("renders the correct number of rows based on tasks", () => {

    const rows = wrapper.findAll(".q-table > tbody > .q-tr").wrappers;
    expect(rows).toHaveLength(3);
  });

  // Edit Modal
  /*it(`show EditAutomatedTask Dialog`, async () => {

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);
    expect(bodyWrapper.find(".q-menu").exists()).toBe(false);

    const row = wrapper.findAll(".q-table > tbody > .q-tr").wrappers[1];
    await row.trigger("contextmenu");
    expect(bodyWrapper.find(".q-menu").exists()).toBe(true);
    
    await bodyWrapper.find("#context-edit").trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);
  });*/

  it("shows policy status modal on cell click", async () => {

    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);

    const row = wrapper.findAll(".status-cell").wrappers[1];
    await row.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);
    expect(wrapper.vm.statusTask).toEqual(tasks[1]);
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
    expect(wrapper.vm.statusTask).toEqual(tasks[0]);
  });

  it("deletes task", async () => {

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

    expect(rootActions.deleteAutoTask).toHaveBeenCalledWith(expect.anything(), 1);
    expect(actions.loadPolicyAutomatedTasks).toHaveBeenCalled();

  });

  it("enables and disables task", async () => {

    //Get first checkbox in first row
    const row = wrapper.findAll(".q-checkbox").wrappers[0];

    //Disable Task
    await row.trigger("click");

    expect(rootActions.editAutoTask).toHaveBeenCalledWith(
      expect.anything(), 
      { id: 1, enableordisable: false }
      );

    //Enable Task
    await row.trigger("click");

    expect(rootActions.editAutoTask).toHaveBeenCalledWith(     
      expect.anything(), 
      { id: 1, enableordisable: true }
    );

  });

  /* TODO: test @close and @hide events */
});
