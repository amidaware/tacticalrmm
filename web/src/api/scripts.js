import axios from "axios"

const baseUrl = "/scripts"

// script operations
export async function fetchScripts(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/`, { params: params })
    return data
  } catch (e) { }
}

export async function testScript(payload) {
  try {
    const { data } = await axios.post(`${baseUrl}/testscript/`, payload)
    return data
  } catch (e) { }
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
  try {
    const { data } = await axios.get(`${baseUrl}/download/${id}/`, { params: params })
    return data
  } catch (e) { }
}


// script snippet operations
export async function fetchScriptSnippets(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/snippets/`, { params: params })
    return data
  } catch (e) { }
}

export async function saveScriptSnippet(payload) {
  try {
    const { data } = await axios.post(`${baseUrl}/snippets/`, payload)
    return data
  } catch (e) { }
}

export async function fetchScriptSnippet(id, params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/snippets/${id}/`, { params: params })
    return data
  } catch (e) { }
}

export async function editScriptSnippet(payload) {
  try {
    const { data } = await axios.put(`${baseUrl}/snippets/${payload.id}/`, payload)
    return data
  } catch (e) { }
}

export async function removeScriptSnippet(id) {
  try {
    const { data } = await axios.delete(`${baseUrl}/snippets/${id}/`)
    return data
  } catch (e) { }
}