import axios from "axios"

const baseUrl = "/clients"

export async function fetchClients() {
  try {
    const { data } = await axios.get(`${baseUrl}/`)
    return data
  } catch (e) { console.error(e) }
}

export async function fetchClient(id) {
  try {
    const { data } = await axios.get(`${baseUrl}/${id}/`)
    return data
  } catch (e) { console.error(e) }
}

export async function saveClient(payload) {
  const { data } = await axios.post(`${baseUrl}/`, payload)
  return data
}

export async function editClient(id, payload) {
  const { data } = await axios.put(`${baseUrl}/${id}/`, payload)
  return data
}

export async function removeClient(id, params = {}) {
  const { data } = await axios.delete(`${baseUrl}/${id}/`, { params: params })
  return data
}

export async function fetchSites() {
  try {
    const { data } = await axios.get(`${baseUrl}/sites/`)
    return data
  } catch (e) { console.error(e) }
}

export async function fetchSite(id) {
  try {
    const { data } = await axios.get(`${baseUrl}/sites/${id}/`)
    return data
  } catch (e) { console.error(e) }
}

export async function saveSite(payload) {
  const { data } = await axios.post(`${baseUrl}/sites/`, payload)
  return data
}

export async function editSite(id, payload) {
  const { data } = await axios.put(`${baseUrl}/sites/${id}/`, payload)
  return data
}

export async function removeSite(id, params = {}) {
  const { data } = await axios.delete(`${baseUrl}/sites/${id}/`, { params: params })
  return data
}
