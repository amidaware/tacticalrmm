import axios from "axios"

const baseUrl = "/checks"

export async function fetchChecks(params = {}) {
    try {
        const { data } = await axios.get(`${baseUrl}/`, { params: params })
        return data
    } catch (e) {
        console.error(e)
    }
}

export async function saveCheck(payload) {
    const { data } = await axios.post(`${baseUrl}/`, payload)
    return data
}

export async function updateCheck(id, payload) {
    const { data } = await axios.put(`${baseUrl}/${id}/`, payload)
    return data
}

export async function removeCheck(id) {
    const { data } = await axios.delete(`${baseUrl}/${id}/`)
    return data
}

export async function resetCheck(id) {
    const { data } = await axios.post(`${baseUrl}/${id}/reset/`)
    return data
}

export async function runAgentChecks(agent_id) {
    const { data } = await axios.post(`${baseUrl}/${agent_id}/run/`)
    return data
}