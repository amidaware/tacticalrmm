import axios from "axios"

const baseUrl = "/logs"

export async function downloadDebugLog() {

	const { data } = await axios.get(`${baseUrl}/downloadlog/`, { responseType: "blob" })

	const blob = new Blob([data], { type: "text/plain" });
	let link = document.createElement("a");
	link.href = window.URL.createObjectURL(blob);
	link.download = "debug.log";
	link.click();

}

export async function fetchDebugLog(level, agent, order) {
	const { data } = await axios.get(`${baseUrl}/debuglog/${level}/${agent}/${order}/`)
	return data
}