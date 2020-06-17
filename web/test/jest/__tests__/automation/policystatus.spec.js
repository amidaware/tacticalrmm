import { mount, createWrapper, createLocalVue } from "@vue/test-utils";
import Vuex from "vuex";
import flushpromises from "flush-promises";
import PolicyStatus from "@/components/automation/modals/PolicyStatus";
import "../../utils/quasar.js";

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

// test data
const item = {
  id: 1,
  readable_desc: "Check Description"
};

describe("PolicyStatus.vue viewing check status", () => {

  const data = [
    {
      hostname: "Agent 1",
      status: "pending",
      check_type: "ping",
      last_run: "Last Run"
    },
    {
      hostname: "Agent 2",
      status: "passing",
      check_type: "script",
      last_run: "Last Run"
    },
    {
      hostname: "Agent 3",
      status: "failing",
      check_type: "eventlog",
      last_run: "Last Run"
    },
  ];

  let wrapper, actions, store;
  // Runs before every test
  beforeEach(() => {

    actions = {
      loadCheckStatus: jest.fn(() => Promise.resolve({ data: data }))
    };

    store = new Vuex.Store({
      modules: {
        automation: {
          namespaced: true,
          actions,
        }
      }
    });

    wrapper = mount(PolicyStatus, {
        localVue,
        store,
        propsData: {
          item: item,
          type: "check"
        },
        stubs: [
          "ScriptOutput",
          "EventLogCheckOutput"
        ]
    });

  });

  it("calls correct check vuex action on mount", () => {

    expect(actions.loadCheckStatus).toHaveBeenCalledWith(expect.anything(), { checkpk: item.id });

  });

  it("renders correct number of rows in table", async () => {

    await flushpromises();
    await localVue.nextTick();
    const rows = wrapper.findAll(".q-table > tbody > .q-tr").wrappers;
    expect(rows).toHaveLength(3);
  });

  it("shows event log status on cell click", async () => {

    await flushpromises();
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);

    const row = wrapper.findAll(".eventlog-cell").wrappers[0];
    await row.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

    // Needs to be equal to eventlog check in test data array
    expect(wrapper.vm.evtLogData).toEqual(data[2]);
  });

  it("shows script status on cell click", async () => {

    await flushpromises();
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);

    const row = wrapper.findAll(".script-cell").wrappers[0];
    await row.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

    // Needs to be equal to script check in test data array
    expect(wrapper.vm.scriptInfo).toEqual(data[1]);
  });

  it("shows pingstatus on cell click", async () => {

    await flushpromises();
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(false);

    const row = wrapper.findAll(".ping-cell").wrappers[0];
    await row.trigger("click");
    expect(bodyWrapper.find(".q-dialog").exists()).toBe(true);

  });

});

describe("PolicyStatus.vue viewing task status", () => {

  const data = [];

  let wrapper, actions, store;
  // Runs before every test
  beforeEach(() => {

    actions = {
      loadAutomatedTaskStatus: jest.fn(() => Promise.resolve({ data: data })),
    };

    store = new Vuex.Store({
      modules: {
        automation: {
          namespaced: true,
          actions,
        }
      }
    });

    wrapper = mount(PolicyStatus, {
        localVue,
        store,
        propsData: {
          item: item,
          type: "task"
        },
        stubs: [
          "ScriptOutput",
          "EventLogCheckOutput"
        ]
    });

  });

  it("calls correct check vuex action on mount", () => {

      expect(actions.loadAutomatedTaskStatus).toHaveBeenCalledWith(expect.anything(), { taskpk: item.id });

  });

});
