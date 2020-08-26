import { mount, createLocalVue } from "@vue/test-utils";
import Vuex from "vuex";
import RelationsView from "@/components/automation/modals/RelationsView";
import "../../utils/quasar.js";

const localVue = createLocalVue();
localVue.use(Vuex);

describe("Relations.vue", () => {

  const policy = {
    id: 1,
    name: "Test Policy",
    active: true,
    clients: [{ id: 1, client: "Test Name" }],
    sites: [{ id: 1, site: "Test Name" }],
    agents: []
  };

  const related = {
    agents: [
      {
        pk: 1,
        hostname: "Test Name",
        site: "Test Site",
        client: "Test Client"
      },
      {
        pk: 2,
        site: "Test Site",
        hostname: "Test Name2",
        site: "Test Site",
        client: "Test Client"
      }
    ],
    server_sites: [
      {
        id: 1,
        client_name: "Test Name",
        site: "Test Name"
      }
    ],
    workstation_sites: [
      {
        id: 2,
        client_name: "Test Name",
        site: "Test Name"
      }
    ],
    server_clients: [
      {
        id: 1,
        client: "Test Name"
      },
      {
        id: 2,
        client: "Test Name2"
      },
      {
        id: 3,
        client: "Test Name3"
      }
    ],
    workstation_clients: [
      {
        id: 4,
        client: "Test Name"
      },
      {
        id: 5,
        client: "Test Name2"
      },
      {
        id: 6,
        client: "Test Name3"
      }
    ]
  };

  let wrapper, actions, store;

  // Runs before every test
  beforeEach(() => {

    actions = {
      getRelated: jest.fn(() => new Promise(res => res({ data: related }))),
    };

    store = new Vuex.Store({
      modules: {
        automation: {
          namespaced: true,
          actions,
        }
      }
    });

    wrapper = mount(RelationsView, {
      localVue,
      store,
      propsData: {
        policy: policy
      }
    });

  });

  // The Tests
  it("calls vuex actions on mount", () => {

    expect(actions.getRelated).toHaveBeenCalledWith(expect.anything(), policy.id);

  });

  it("Checks the correct number of list items are rendered in clients tab", async () => {

    await wrapper.findComponent({ ref: "clients" }).trigger("click");

    const list = wrapper.findAll(".q-item");
    expect(list.length).toBeGreaterThanOrEqual(related.server_clients.length + related.workstation_clients.length);

  });

  it("Checks the correct number of list items are rendered in sites tab", async () => {

    await wrapper.findComponent({ ref: "sites" }).trigger("click");

    const list = wrapper.findAll(".q-item");
    expect(list.length).toBeGreaterThanOrEqual(related.server_sites.length + related.workstation_sites.length);

  });

  it("Checks the correct number of list items are rendered in agents tab", async () => {

    await wrapper.findComponent({ ref: "agents" }).trigger("click");

    const list = wrapper.findAll(".q-item");
    expect(list.length).toBeGreaterThanOrEqual(related.agents.length);

  });

});

