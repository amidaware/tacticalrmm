import { mount, createLocalVue } from '@vue/test-utils';
import Vuex from 'vuex';
import PolicyForm from '@/components/automation/modals/PolicyForm';
import "@/quasar.js"

const localVue = createLocalVue();
localVue.use(Vuex);

describe('PolicyForm.vue', () => {

  const clients = [];
  const sites = [];
  const agents = [];

  const policy = {};

  let actions, rootActions, store;

  // Runs before every test
  beforeEach(() => {

    rootActions = {
      loadClients: jest.fn(() => clients),
      loadSites: jest.fn(() => sites),
      loadAgents: jest.fn(() => agents),
    };

    actions = {
      loadPolicy: jest.fn(() => policy),
      addPolicy: jest.fn(),
      editPolicy: jest.fn(),
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

  });

  // The Tests
  it("calls vuex actions on mount", () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
    });

    expect(rootActions.loadClients).toHaveBeenCalled();
    expect(rootActions.loadSites).toHaveBeenCalled();
    expect(rootActions.loadAgents).toHaveBeenCalled();

    // Not called unless pk prop is set
    expect(actions.loadPolicy).not.toHaveBeenCalled();

  });

  it("calls vuex actions on mount with pk prop set", () => {

    const wrapper = mount(PolicyForm, {
      localVue,
      store,
      propsData: {
        pk: 1
      }
    });

    expect(rootActions.loadClients).toHaveBeenCalled();
    expect(rootActions.loadSites).toHaveBeenCalled();
    expect(rootActions.loadAgents).toHaveBeenCalled();
    expect(actions.loadPolicy).toHaveBeenCalled();

  })

  /*it("renders the client, site, and agent dropdowns correctly", async () => {

  })*/

})
