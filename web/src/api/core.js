import axios from "axios"

const baseUrl = "/core"

export async function fetchCustomFields(params) {
  try {
    const { data } = await axios.get(`${baseUrl}/customfields/`, { params: params })
    return data
  } catch (e) { }
}