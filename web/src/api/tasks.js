import axios from "axios"

const baseUrl = "/tasks"

export async function fetchTasks(params = {}) {
    try {
        const { data } = await axios.get(`${baseUrl}/`, { params: params })
        return data
    } catch (e) {
        console.error(e)
    }
}

export async function saveTasks(payload) {
    const { data } = await axios.post(`${baseUrl}/`, payload)
    return data
}

export async function updateTask(id, payload) {
    const { data } = await axios.put(`${baseUrl}/${id}/`, payload)
    return data
}

export async function removeTask(id) {
    const { data } = await axios.delete(`${baseUrl}/${id}/`)
    return data
}

export async function runTask(id) {
    const { data } = await axios.post(`${baseUrl}/${id}/run/`)
    return data
}