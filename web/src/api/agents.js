import axios from "axios"

const baseUrl = "/agents"

export async function fetchAgents() {
  try {
    const { data } = await axios.get(`${baseUrl}/listagentsnodetail/`)
    return data
  } catch (e) { }
}

export async function fetchAgentHistory(pk) {
  try {
    const { data } = await axios.get(`${baseUrl}/history/${pk}`)
    return data
  } catch (e) { }
}

export async function runScript(payload) {
  try {
    const { data } = await axios.post(`${baseUrl}/runscript/`, payload)
    return data
  } catch (e) { }
}
