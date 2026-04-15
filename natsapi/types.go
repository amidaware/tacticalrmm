package natsapi

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

// NatsUser is one entry under authorization.users in nats-rmm.conf.
// Permissions is left as a free-form map because NATS accepts either a string
// ("publish": ">") or an object ("publish": {"allow": "<agent-id>"}) for the
// same key, and nats-server is strict about the shape.
type NatsUser struct {
	User        string                 `json:"user"`
	Password    string                 `json:"password"`
	Permissions map[string]interface{} `json:"permissions"`
}

type NatsAuthorization struct {
	Users   []NatsUser `json:"users"`
	Timeout int        `json:"timeout"`
}

type NatsWebsocket struct {
	Host        string `json:"host"`
	Port        int    `json:"port"`
	NoTLS       bool   `json:"no_tls"`
	Compression bool   `json:"compression,omitempty"`
}

type NatsTLS struct {
	CertFile string `json:"cert_file"`
	KeyFile  string `json:"key_file"`
}

// NatsRmmConfig is the full shape of nats-rmm.conf. HttpPort and TLS are
// optional — zero values are omitted from the JSON so nats-server doesn't
// try to bind an http port or enable TLS when they weren't requested.
type NatsRmmConfig struct {
	Authorization NatsAuthorization `json:"authorization"`
	MaxPayload    int               `json:"max_payload"`
	Host          string            `json:"host"`
	Port          int               `json:"port"`
	Websocket     NatsWebsocket     `json:"websocket"`
	HttpPort      int               `json:"http_port,omitempty"`
	TLS           *NatsTLS          `json:"tls,omitempty"`
}
