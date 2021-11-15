import axios from "axios"

const baseUrl = "/scripts"

// script operations
export async function fetchScripts(params = {}) {
  const { data } = await axios.get(`${baseUrl}/`, { params: params })
  return data
}

export async function testScript(agent_id, payload) {
  const { data } = await axios.post(`${baseUrl}/${agent_id}/test/`, payload)
  return data
}

export async function saveScript(payload) {
  const { data } = await axios.post(`${baseUrl}/`, payload)
  return data
}

export async function editScript(payload) {
  const { data } = await axios.put(`${baseUrl}/${payload.id}/`, payload)
  return data
}

export async function removeScript(id) {
  const { data } = await axios.delete(`${baseUrl}/${id}/`)
  return data
}

export async function downloadScript(id, params = {}) {
  const { data } = await axios.get(`${baseUrl}/${id}/download/`, { params: params })
  return data
}


// script snippet operations
export async function fetchScriptSnippets(params = {}) {
  const { data } = await axios.get(`${baseUrl}/snippets/`, { params: params })
  return data

}

export async function saveScriptSnippet(payload) {
  const { data } = await axios.post(`${baseUrl}/snippets/`, payload)
  return data
}

export async function fetchScriptSnippet(id, params = {}) {
  const { data } = await axios.get(`${baseUrl}/snippets/${id}/`, { params: params })
  return data
}

export async function editScriptSnippet(payload) {
  const { data } = await axios.put(`${baseUrl}/snippets/${payload.id}/`, payload)
  return data
}

export async function removeScriptSnippet(id) {
  const { data } = await axios.delete(`${baseUrl}/snippets/${id}/`)
  return data
}