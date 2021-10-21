import axios from "axios"

const baseUrl = "/agents"

export async function fetchAgents(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/`, { params: params })
    return data
  } catch (e) {
    console.error(e)
  }
}

export async function fetchAgent(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/`, { params: params })
    return data
  } catch (e) { console.error(e) }
}

export async function fetchAgentHistory(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/history/`, { params: params })
    return data
  } catch (e) { console.error(e) }
}

export async function fetchAgentChecks(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/checks/`, { params: params })
    return data
  } catch (e) { console.error(e) }
}

export async function fetchAgentTasks(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/tasks/`, { params: params })
    return data
  } catch (e) { console.error(e) }
}

export async function sendAgentCommand(agent_id, payload) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/cmd/`, payload)
  return data
}

export async function refreshAgentWMI(agent_id) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/wmi/`)
  return data
}

export async function runScript(agent_id, payload) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/runscript/`, payload)
  return data
}

export async function runBulkAction(payload) {
  const { data } = await axios.post(`${baseUrl}/bulk/`, payload)
  return data
}

export async function fetchAgentProcesses(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/processes/`, { params: params })
    return data
  } catch (e) {
    console.error(e)
  }
}

export async function killAgentProcess(agent_id, pid, params = {}) {
  const { data } = await axios.delete(`${baseUrl}/${agent_id}/processes/${pid}/`, { params: params })
  return data
}

export async function fetchAgentEventLog(agent_id, logType, days, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/eventlog/${logType}/${days}/`, { params: params })
    return data
  } catch (e) {
    console.error(e)
  }
}

export async function fetchAgentMeshCentralURLs(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/meshcentral/`, { params: params })
    return data
  } catch (e) {
    console.error(e)
  }
}

export async function sendAgentRecoverMesh(agent_id, params = {}) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/meshcentral/recover/`, { params: params })
  return data
}

// agent notes
export async function fetchAgentNotes(agent_id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/${agent_id}/notes/`, { params: params })
    return data
  } catch (e) { console.error(e) }
}

export async function saveAgentNote(payload) {
  const { data } = await axios.post(`${baseUrl}/notes/`, payload)
  return data
}

export async function editAgentNote(pk, payload) {
  const { data } = await axios.put(`${baseUrl}/notes/${pk}/`, payload)
  return data
}

export async function removeAgentNote(pk) {
  const { data } = await axios.delete(`${baseUrl}/notes/${pk}/`)
  return data
}
