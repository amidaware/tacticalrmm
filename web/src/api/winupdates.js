import axios from "axios";

const baseUrl = "/winupdate";

// win updates api functions
export async function fetchAgentUpdates(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/`, {
      params: params,
    });
    return data;
  } catch (e) {
    console.error(e);
  }
}

export async function runAgentUpdateScan(agent_id) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/scan/`);
  return data;
}

export async function runAgentUpdateInstall(agent_id) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/install/`);
  return data;
}

export async function editAgentUpdate(id, payload) {
  const { data } = await axios.put(`${baseUrl}/${id}/`, payload);
  return data;
}
