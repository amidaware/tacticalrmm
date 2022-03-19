import axios from "axios"
import { openURL } from "quasar";

const baseUrl = "/core"

export async function fetchCustomFields(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/customfields/`, { params: params })
    return data
  } catch (e) { console.error(e) }
}

export async function fetchDashboardInfo(params = {}) {
  const { data } = await axios.get(`${baseUrl}/dashinfo/`, { params: params })
  return data
}

export async function fetchURLActions(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/urlaction/`, { params: params })
    return data
  } catch (e) { console.error(e) }
}

export async function runURLAction(payload) {
  try {
    const { data } = await axios.patch(`${baseUrl}/urlaction/run/`, payload)
    openURL(data)
  } catch (e) { console.error(e) }
}