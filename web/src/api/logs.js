import axios from "axios"

const baseUrl = "/logs"

export async function fetchDebugLog(payload) {
  try {
    const { data } = await axios.patch(`${baseUrl}/debuglog/`, payload)
    return data
  } catch (e) { }
}

export async function fetchAuditLog(payload) {
  try {
    const { data } = await axios.patch(`${baseUrl}/auditlogs/`, payload)
    return data
  } catch (e) { }
}
