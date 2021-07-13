import axios from "axios"

const baseUrl = "/scripts"

export async function fetchScripts(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/scripts/`, { params: params })
    return data
  } catch (e) { }
}

export async function testScript(payload) {
  try {
    const { data } = await axios.post(`${baseUrl}/testscript/`, payload)
    return data
  } catch (e) { }
}