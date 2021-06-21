import axios from "axios"

const baseUrl = "/agents"

export async function fetchAgents() {
  try {
    const { data } = await axios.get(`${baseUrl}/listagentsnodetail/`)
    return data
  } catch (e) { }
}