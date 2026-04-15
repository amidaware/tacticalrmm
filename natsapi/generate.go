package natsapi

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"

	"github.com/jmoiron/sqlx"
	"github.com/sirupsen/logrus"
)

// GenerateNatsRmmConfig queries Postgres for the current set of agent users
// and writes a fresh nats-rmm.conf to outPath. It mirrors the shape produced
// by the Python reload_nats() function in api/tacticalrmm/tacticalrmm/utils.py
// so a standalone install and a container install both get byte-identical
// configs for the same DB state.
//
// secretKey is the NATS "tacticalrmm" superuser password (Django SECRET_KEY).
// Agent users are built by joining agents_agent → accounts_user → authtoken_token,
// which matches `agent.user.auth_token.key` on the Python side.
func GenerateNatsRmmConfig(
	logger *logrus.Logger,
	db *sqlx.DB,
	secretKey string,
	outPath string,
) error {
	users := []NatsUser{{
		User:     "tacticalrmm",
		Password: secretKey,
		Permissions: map[string]interface{}{
			"publish":   ">",
			"subscribe": ">",
		},
	}}

	rows, err := db.Query(`
		SELECT a.agent_id, t.key
		FROM agents_agent a
		JOIN accounts_user u ON u.agent_id = a.id
		JOIN authtoken_token t ON t.user_id = u.id
	`)
	if err != nil {
		return fmt.Errorf("query agent users: %w", err)
	}
	defer rows.Close()

	allowResponseExpires := envOrDefault("NATS_ALLOW_RESPONSE_EXPIRATION", "1435m")

	agentCount := 0
	for rows.Next() {
		var agentID, token string
		if err := rows.Scan(&agentID, &token); err != nil {
			logger.Warnf("scan agent row: %v", err)
			continue
		}
		agentCount++
		users = append(users, NatsUser{
			User:     agentID,
			Password: token,
			Permissions: map[string]interface{}{
				"publish":   map[string]string{"allow": agentID},
				"subscribe": map[string]string{"allow": agentID},
				"allow_responses": map[string]string{
					"expires": allowResponseExpires,
				},
			},
		})
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterate agent rows: %w", err)
	}

	stdBindHost := envOrDefault("NATS_STD_BIND_HOST", "0.0.0.0")
	wsBindHost := envOrDefault("NATS_WS_BIND_HOST", "0.0.0.0")
	stdPort, err := strconv.Atoi(envOrDefault("NATS_STANDARD_PORT", "4222"))
	if err != nil {
		return fmt.Errorf("invalid NATS_STANDARD_PORT: %w", err)
	}
	wsPort, err := strconv.Atoi(envOrDefault("NATS_WEBSOCKET_PORT", "9235"))
	if err != nil {
		return fmt.Errorf("invalid NATS_WEBSOCKET_PORT: %w", err)
	}

	cfg := NatsRmmConfig{
		Authorization: NatsAuthorization{Users: users, Timeout: 30},
		MaxPayload:    67108864,
		Host:          stdBindHost,
		Port:          stdPort,
		Websocket: NatsWebsocket{
			Host:  wsBindHost,
			Port:  wsPort,
			NoTLS: true,
		},
	}

	if v := os.Getenv("NATS_HTTP_PORT"); v != "" {
		p, err := strconv.Atoi(v)
		if err != nil {
			return fmt.Errorf("invalid NATS_HTTP_PORT: %w", err)
		}
		cfg.HttpPort = p
	}
	if os.Getenv("NATS_WS_COMPRESSION") != "" {
		cfg.Websocket.Compression = true
	}

	data, err := json.Marshal(cfg)
	if err != nil {
		return fmt.Errorf("marshal nats-rmm.conf: %w", err)
	}

	// Atomic write: drop a sibling tmp file then rename. Prevents nats-server
	// from reading a half-written config if it happens to be inspecting the
	// file when we update it.
	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		return fmt.Errorf("create parent dir: %w", err)
	}
	tmp, err := os.CreateTemp(filepath.Dir(outPath), ".nats-rmm.conf.*")
	if err != nil {
		return fmt.Errorf("create tmp file: %w", err)
	}
	tmpName := tmp.Name()
	defer os.Remove(tmpName)

	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		return fmt.Errorf("write tmp file: %w", err)
	}
	if err := tmp.Chmod(0o660); err != nil {
		tmp.Close()
		return fmt.Errorf("chmod tmp file: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close tmp file: %w", err)
	}
	if err := os.Rename(tmpName, outPath); err != nil {
		return fmt.Errorf("rename %s → %s: %w", tmpName, outPath, err)
	}

	logger.Infof("Wrote nats-rmm.conf with %d agent users to %s", agentCount, outPath)
	return nil
}

// SignalNatsServerReload finds the nats-server process running in this
// container and sends it SIGHUP, which nats-server interprets as "reload
// config from disk." Because nats-api runs alongside nats-server under the
// same supervisord, both are in the same PID namespace and /proc walk is
// enough — we do not need `nats-server --signal reload` or a pidfile.
//
// Returns ErrNatsServerNotFound if the process isn't running yet. Callers
// should log and continue rather than exit: on first boot the subscriber may
// race startup, and a missed SIGHUP is harmless because the fresh config was
// already written to disk by the bootstrap.
func SignalNatsServerReload(logger *logrus.Logger) error {
	pid, err := findNatsServerPID()
	if err != nil {
		return err
	}
	if err := syscall.Kill(pid, syscall.SIGHUP); err != nil {
		return fmt.Errorf("SIGHUP to nats-server (pid=%d): %w", pid, err)
	}
	logger.Infof("Sent SIGHUP to nats-server (pid=%d)", pid)
	return nil
}

// ErrNatsServerNotFound is returned when no nats-server process is visible
// in /proc. Kept as a sentinel so the reload subscriber can treat "not yet
// running" as non-fatal.
var ErrNatsServerNotFound = fmt.Errorf("nats-server process not found")

func findNatsServerPID() (int, error) {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return 0, fmt.Errorf("read /proc: %w", err)
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(e.Name())
		if err != nil {
			continue
		}
		comm, err := os.ReadFile(fmt.Sprintf("/proc/%d/comm", pid))
		if err != nil {
			// Process may have exited between readdir and read.
			continue
		}
		if strings.TrimSpace(string(comm)) == "nats-server" {
			return pid, nil
		}
	}
	return 0, ErrNatsServerNotFound
}
