import axios from "axios";

const baseUrl = "/software";

export async function fetchChocosSoftware(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/chocos/`, { params: params });
    return data;
  } catch (e) {
    console.error(e);
  }
}

export async function fetchAgentSoftware(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/`, {
      params: params,
    });
    return data.software;
  } catch (e) {
    console.error(e);
  }
}

export async function installAgentSoftware(agent_id, payload) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/`, payload);
  return data;
}

export async function refreshAgentSoftware(agent_id) {
  try {
    const { data } = await axios.put(`${baseUrl}/${agent_id}/`);
    return data;
  } catch (e) {
    console.error(e);
  }
}
