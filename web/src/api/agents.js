import axios from "axios"

const baseUrl = "/agents"

export async function fetchAgents() {
  const { data } = await axios.get(`${baseUrl}/listagentsnodetail/`)

  return data
}