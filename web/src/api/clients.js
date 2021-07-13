import axios from "axios"

const baseUrl = "/clients"

export async function fetchClients() {
  try {
    const { data } = await axios.get(`${baseUrl}/clients/`)
    return data
  } catch (e) { }
}