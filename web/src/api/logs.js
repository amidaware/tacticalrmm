import axios from "axios"

const baseUrl = "/logs"

export async function fetchDebugLog(payload) {
  try {
    const { data } = await axios.patch(`${baseUrl}/debug/`, payload)
    return data
  } catch (e) { }
}

export async function fetchAuditLog(payload) {
  try {
    const { data } = await axios.patch(`${baseUrl}/audit/`, payload)
    return data
  } catch (e) { }
}
