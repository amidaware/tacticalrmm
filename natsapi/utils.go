package natsapi

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"
	trmm "github.com/wh1te909/trmm-shared"
)

// GetConfig loads a DjangoConfig + opens a Postgres connection.
//
// Resolution order for the DjangoConfig:
//  1. If cfg is non-empty and the file exists, parse it as JSON.
//  2. Otherwise, if cfg is empty, try the legacy default path
//     /rmm/api/tacticalrmm/nats-api.conf (standalone installs).
//  3. Otherwise, build the config from environment variables
//     (POSTGRES_*, SECRET_KEY, NATS_CONNECT_HOST, NATS_STANDARD_PORT).
//     This is the path used by the tactical-nats container in Docker and K8s,
//     where we do not want the backend's PVC or Redis involved in passing a
//     config file across pods.
func GetConfig(cfg string) (db *sqlx.DB, r DjangoConfig, err error) {
	switch {
	case cfg != "" && trmm.FileExists(cfg):
		r, err = loadConfigFromFile(cfg)
	case cfg == "" && trmm.FileExists("/rmm/api/tacticalrmm/nats-api.conf"):
		r, err = loadConfigFromFile("/rmm/api/tacticalrmm/nats-api.conf")
	default:
		r, err = loadConfigFromEnv()
	}
	if err != nil {
		return
	}
	db, err = openDB(r, 20)
	return
}

// openDB opens a new *sqlx.DB using the given DjangoConfig with a tight
// per-handle pool cap. Svc() uses this to give every worker shard its own
// small connection pool so that a pile-up of slow queries on one shard
// cannot drain the pool that other shards depend on. SetConnMaxLifetime
// also keeps idle connections from going stale behind a load balancer.
func openDB(r DjangoConfig, maxOpen int) (*sqlx.DB, error) {
	psqlInfo := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
		r.Host, r.Port, r.User, r.Pass, r.DBName, r.SSLMode)
	db, err := sqlx.Connect("postgres", psqlInfo)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(maxOpen)
	db.SetMaxIdleConns(maxOpen)
	db.SetConnMaxLifetime(5 * time.Minute)
	return db, nil
}

func loadConfigFromFile(path string) (DjangoConfig, error) {
	var r DjangoConfig
	jret, err := os.ReadFile(path)
	if err != nil {
		return r, fmt.Errorf("read %s: %w", path, err)
	}
	if err := json.Unmarshal(jret, &r); err != nil {
		return r, fmt.Errorf("parse %s: %w", path, err)
	}
	return r, nil
}

// loadConfigFromEnv assembles a DjangoConfig from the same env vars the
// tactical-backend entrypoint exports. This is the no-file path for the
// tactical-nats container — bootstrap runs before supervisord, so we cannot
// rely on any config written by another pod/container being present on disk.
func loadConfigFromEnv() (DjangoConfig, error) {
	var r DjangoConfig

	port, err := strconv.Atoi(envOrDefault("POSTGRES_PORT", "5432"))
	if err != nil {
		return r, fmt.Errorf("invalid POSTGRES_PORT: %w", err)
	}

	// POSTGRES_PASSWORD takes priority if set (secrets-manager friendly),
	// otherwise fall back to POSTGRES_PASS (the historical name here).
	pass := os.Getenv("POSTGRES_PASSWORD")
	if pass == "" {
		pass = os.Getenv("POSTGRES_PASS")
	}

	secretKey := os.Getenv("SECRET_KEY")
	if secretKey == "" {
		return r, fmt.Errorf("SECRET_KEY is required when running without a config file")
	}

	natsHost := envOrDefault("NATS_CONNECT_HOST", "127.0.0.1")
	natsPort := envOrDefault("NATS_STANDARD_PORT", "4222")

	r = DjangoConfig{
		Key:     secretKey,
		NatsURL: fmt.Sprintf("nats://%s:%s", natsHost, natsPort),
		User:    envOrDefault("POSTGRES_USER", "tactical"),
		Pass:    pass,
		Host:    envOrDefault("POSTGRES_HOST", "tactical-postgres"),
		Port:    port,
		DBName:  envOrDefault("POSTGRES_DB", "tacticalrmm"),
		SSLMode: envOrDefault("DB_SSL", "disable"),
	}
	return r, nil
}

func envOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
