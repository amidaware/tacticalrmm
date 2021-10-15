import axios from "axios"

const baseUrl = "/clients"

export async function fetchClients() {
  try {
    const { data } = await axios.get(`${baseUrl}/`)
    return data
  } catch (e) { console.error(e) }
}

export async function fetchSites() {
  try {
    const { data } = await axios.get(`${baseUrl}/sites/`)
    return data
  } catch (e) { console.error(e) }
}