import axios from "axios"

const baseUrl = "/accounts"

// user api functions
export async function fetchUsers(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/users/`, { params: params })
    return data
  } catch (e) { }
}


// api key api functions
export async function fetchAPIKeys(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/apikeys/`, { params: params })
    return data
  } catch (e) { }
}

export async function saveAPIKey(payload) {
  const { data } = await axios.post(`${baseUrl}/apikeys/`, payload)
  return data
}

export async function editAPIKey(payload) {
  const { data } = await axios.put(`${baseUrl}/apikeys/${payload.id}/`, payload)
  return data
}

export async function removeAPIKey(id) {
  const { data } = await axios.delete(`${baseUrl}/apikeys/${id}/`)
  return data
}
