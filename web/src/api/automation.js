import axios from "axios"

const baseUrl = "/automation"

export async function sendPatchPolicyReset(payload) {
    const { data } = await axios.post(`${baseUrl}/patchpolicy/reset/`, payload)
    return data
}