import axios from "axios";

const baseUrl = "/services";

export async function getAgentServices(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/`, {
      params: params,
    });
    return data;
  } catch (e) {
    console.error(e);
  }
}

export async function getAgentServiceDetails(agent_id, svcname, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/${svcname}/`, {
      params: params,
    });
    return data;
  } catch (e) {
    console.error(e);
  }
}

export async function editAgentServiceStartType(agent_id, svcname, payload) {
  const { data } = await axios.put(
    `${baseUrl}/${agent_id}/${svcname}/`,
    payload
  );
  return data;
}

export async function sendAgentServiceAction(agent_id, svcname, payload) {
  const { data } = await axios.post(
    `${baseUrl}/${agent_id}/${svcname}/`,
    payload
  );
  return data;
}
