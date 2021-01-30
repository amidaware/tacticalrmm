package api

type NatsInfo struct {
	User     string `json:"user"`
	Password string `json:"password"`
}

type AgentIDS struct {
	IDs []string `json:"agent_ids"`
}

type Recovery struct {
	Func string            `json:"func"`
	Data map[string]string `json:"payload"`
}
