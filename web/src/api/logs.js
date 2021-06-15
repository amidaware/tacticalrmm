import axios from "axios"

const baseUrl = "/logs/debuglog/"

export async function fetchDebugLog(payload) {
  const { data } = await axios.patch(`${baseUrl}`, payload)

  return data
}