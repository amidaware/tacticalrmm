import axios from "axios"

const baseUrl = "/accounts"

export async function fetchUsers(params = {}) {
  try {
    const { data } = await axios.get(`${baseUrl}/users/`, { params: params })
    return data
  } catch (e) { }
}