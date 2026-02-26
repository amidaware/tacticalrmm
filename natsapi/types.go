package api

type Agent struct {
	ID      int    `db:"id"`
	AgentID string `db:"agent_id"`
}

type DjangoConfig struct {
	Key     string `json:"key"`
	NatsURL string `json:"natsurl"`
	User    string `json:"user"`
	Pass    string `json:"pass"`
	Host    string `json:"host"`
	Port    int    `json:"port"`
	DBName  string `json:"dbname"`
	SSLMode string `json:"sslmode"`
}

// agentTimezone is used to extract the IANA timezone from agent-agentinfo payloads
// without duplicating all fields of trmm.AgentInfoNats.
// Openframe mode
type agentTimezone struct {
	Agentid  string `json:"agent_id"`
	Timezone string `json:"timezone"`
}
