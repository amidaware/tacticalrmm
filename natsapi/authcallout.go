package natsapi

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/nats-io/jwt/v2"
	nats "github.com/nats-io/nats.go"
	"github.com/nats-io/nkeys"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/sirupsen/logrus"
	callout "github.com/synadia-io/callout.go"
)

// jwtExpiry bounds how long an approved UserClaims JWT stays valid. Agents
// reconnect regularly, so a day-scale cap gives Postgres-side revocation a
// firm upper bound without churning auth callout on every session.
const jwtExpiry = 24 * time.Hour

// AuthResult is what a Validator returns on a successful credential check.
// It carries everything the authorizer needs to build the UserClaims JWT:
// the target account (JWT Audience), the pub/sub permissions, and the
// optional response permission.
//
// Reject vs. error semantics:
//   - (nil, nil)           → credentials did not match any known user.
//     Reject the connection, do not log an error.
//   - (nil, non-nil error) → the validator itself failed (DB error, etc.).
//     Reject AND log.
//   - (non-nil, nil)       → approve with the returned permissions.
type AuthResult struct {
	Account string
	Pub     jwt.Permission
	Sub     jwt.Permission
	Resp    *jwt.ResponsePermission
}

// Validator checks whether (username, password) is a valid credential pair
// and, if so, returns an AuthResult describing how the connection should be
// authorized. Implementations must be safe for concurrent use from multiple
// goroutines — the callout library dispatches requests concurrently.
type Validator interface {
	Validate(ctx context.Context, username, password string) (*AuthResult, error)
}

// dbValidator validates TacticalRMM agent credentials against Postgres.
// Agents authenticate with agent_id as username and authtoken_token.key as
// password. Approved agents land in trmmAccount with their agent_id as the
// only allowed pub/sub subject.
//
// The "tacticalrmm" superuser is handled by superuserValidator — kept out
// of this path so wrong-password attempts against the service account don't
// wake a DB connection.
type dbValidator struct {
	db              *sqlx.DB
	trmmAccount     string
	agentRespExpiry time.Duration
}

// NewDBValidator wires a dbValidator from env vars:
//
//	AUTH_TARGET_ACCOUNT            — account name for TRMM users (default "$G")
//	NATS_ALLOW_RESPONSE_EXPIRATION — Resp permission TTL for agents (default "1435m")
func NewDBValidator(db *sqlx.DB) (*dbValidator, error) {
	trmmAccount := envOrDefault("AUTH_TARGET_ACCOUNT", "$G")
	respStr := envOrDefault("NATS_ALLOW_RESPONSE_EXPIRATION", "1435m")
	respExpiry, err := time.ParseDuration(respStr)
	if err != nil {
		return nil, fmt.Errorf("parse NATS_ALLOW_RESPONSE_EXPIRATION %q: %w", respStr, err)
	}
	return &dbValidator{
		db:              db,
		trmmAccount:     trmmAccount,
		agentRespExpiry: respExpiry,
	}, nil
}

func (v *dbValidator) Validate(ctx context.Context, username, password string) (*AuthResult, error) {
	// Agent — (agent_id, auth_token.key) lookup against Postgres.
	var exists bool
	err := v.db.QueryRowContext(ctx, `
		SELECT EXISTS(
			SELECT 1
			FROM agents_agent a
			JOIN accounts_user u ON u.agent_id = a.id
			JOIN authtoken_token t ON t.user_id = u.id
			WHERE a.agent_id = $1 AND t.key = $2
		)`, username, password).Scan(&exists)
	if err != nil {
		return nil, fmt.Errorf("validate agent %s: %w", username, err)
	}
	if !exists {
		return nil, nil
	}
	return &AuthResult{
		Account: v.trmmAccount,
		Pub:     jwt.Permission{Allow: jwt.StringList{username}},
		// _INBOX.*.* lets the agent receive replies to its own
		// nc.Request() calls. Today's TRMM telemetry is fire-and-forget,
		// but omitting the inbox breaks any future request/reply path
		// silently (the request just times out).
		Sub: jwt.Permission{Allow: jwt.StringList{username, "_INBOX.*.*"}},
		Resp: &jwt.ResponsePermission{
			MaxMsgs: jwt.NoLimit,
			Expires: v.agentRespExpiry,
		},
	}, nil
}

// loadIssuerKey loads the Ed25519 NKey seed used to sign auth callout
// responses. The seed is read from AUTH_ISSUER_SEED (env var containing the
// raw seed string) or AUTH_ISSUER_SEED_FILE (path to a file containing it).
func loadIssuerKey() (nkeys.KeyPair, error) {
	seed := os.Getenv("AUTH_ISSUER_SEED")
	if seed == "" {
		path := os.Getenv("AUTH_ISSUER_SEED_FILE")
		if path == "" {
			return nil, fmt.Errorf("AUTH_ISSUER_SEED or AUTH_ISSUER_SEED_FILE must be set when auth callout is enabled")
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("read %s: %w", path, err)
		}
		seed = strings.TrimSpace(string(data))
	}
	kp, err := nkeys.FromSeed([]byte(seed))
	if err != nil {
		return nil, fmt.Errorf("parse NKey seed: %w", err)
	}
	// Both callout.ResponseSignerKey and jwt.UserClaims.Encode require an
	// account key pair (seed prefix "SA"). Fail early with a clear message
	// rather than letting the callout library reject it later.
	pub, err := kp.PublicKey()
	if err != nil {
		return nil, fmt.Errorf("extract public key from seed: %w", err)
	}
	if !nkeys.IsValidPublicAccountKey(pub) {
		return nil, fmt.Errorf("AUTH_ISSUER_SEED must be an account key (seed starting with SA), got public key %s", pub)
	}
	return kp, nil
}

// StartAuthCallout opens a dedicated NATS connection as the "auth-service"
// user and starts the auth callout service. It subscribes to
// $SYS.REQ.USER.AUTH and delegates every incoming credential check to the
// provided Validator, translating AuthResult into a signed UserClaims JWT.
//
// The returned *nats.Conn and *callout.AuthorizationService must be closed
// by the caller during shutdown.
func StartAuthCallout(
	ctx context.Context,
	logger *logrus.Logger,
	cfg DjangoConfig,
	validator Validator,
) (*nats.Conn, *callout.AuthorizationService, error) {
	// Fail-closed on a missing AUTH_TARGET_ACCOUNT. The validators default
	// to "$G" for standalone/test use, but in a real callout deployment the
	// target account must be set explicitly and must match an account
	// defined in the broker's nats.conf — silent routing to "$G" would
	// place agents in an account where the telemetry subscribers don't
	// live, and telemetry would vanish with no error.
	if os.Getenv("AUTH_TARGET_ACCOUNT") == "" {
		return nil, nil, fmt.Errorf("AUTH_TARGET_ACCOUNT must be set when auth callout is enabled; it must name an account defined in the broker's nats.conf")
	}

	issuerKP, err := loadIssuerKey()
	if err != nil {
		return nil, nil, err
	}
	pubKey, err := issuerKP.PublicKey()
	if err != nil {
		return nil, nil, fmt.Errorf("extract public key: %w", err)
	}
	logger.Infof("Auth callout issuer public key: %s", pubKey)

	// Connect as the static "auth-service" user in the AUTH account.
	// This user is defined in the NATS wrapper chart's config and must be
	// listed in the server's auth_callout.auth_users exemption so it does
	// not recurse through the callout itself.
	authUser := envOrDefault("AUTH_SERVICE_USER", "auth-service")
	authPass := os.Getenv("AUTH_SERVICE_PASS")
	if authPass == "" {
		return nil, nil, fmt.Errorf("AUTH_SERVICE_PASS must be set when auth callout is enabled")
	}
	if authPass == cfg.Key {
		logger.Warn("AUTH_SERVICE_PASS equals SECRET_KEY — compromising one compromises both; use distinct values")
	}

	authOpts := []nats.Option{
		nats.Name("trmm-auth-callout"),
		nats.UserInfo(authUser, authPass),
		nats.ReconnectWait(2 * time.Second),
		nats.RetryOnFailedConnect(true),
		nats.MaxReconnects(-1),
		nats.ReconnectBufSize(-1),
		nats.DisconnectErrHandler(func(_ *nats.Conn, nerr error) {
			logger.Warnf("Auth callout NATS disconnected: %v", nerr)
		}),
		nats.ReconnectHandler(func(_ *nats.Conn) {
			logger.Info("Auth callout NATS reconnected")
		}),
		nats.ErrorHandler(func(_ *nats.Conn, _ *nats.Subscription, nerr error) {
			logger.Errorf("Auth callout NATS error: %v", nerr)
		}),
	}
	authNc, err := nats.Connect(cfg.NatsURL, authOpts...)
	if err != nil {
		return nil, nil, fmt.Errorf("connect auth callout: %w", err)
	}

	authorizer := func(req *jwt.AuthorizationRequest) (string, error) {
		timer := prometheus.NewTimer(authCalloutDurationSeconds)
		defer timer.ObserveDuration()

		username := req.ConnectOptions.Username
		password := req.ConnectOptions.Password

		if username == "" {
			authCalloutTotal.WithLabelValues("rejected").Inc()
			return "", fmt.Errorf("empty username")
		}

		reqCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
		defer cancel()

		result, err := validator.Validate(reqCtx, username, password)
		if err != nil {
			authCalloutTotal.WithLabelValues("error").Inc()
			logger.Errorf("auth callout validate %s: %v", username, err)
			return "", fmt.Errorf("validation error")
		}
		if result == nil {
			authCalloutTotal.WithLabelValues("rejected").Inc()
			logger.Debugf("auth callout rejected: %s", username)
			return "", fmt.Errorf("invalid credentials for %s", username)
		}

		// Audience selects the nats-server account in centralized
		// (non-operator) auth callout mode. IssuerAccount must NOT be set
		// in this mode — the server rejects it.
		uc := jwt.NewUserClaims(req.UserNkey)
		uc.Name = username
		uc.Audience = result.Account
		uc.Expires = time.Now().Add(jwtExpiry).Unix()
		uc.Pub = result.Pub
		uc.Sub = result.Sub
		uc.Resp = result.Resp

		token, err := uc.Encode(issuerKP)
		if err != nil {
			authCalloutTotal.WithLabelValues("error").Inc()
			return "", fmt.Errorf("encode user JWT: %w", err)
		}

		authCalloutTotal.WithLabelValues("approved").Inc()
		logger.Debugf("auth callout approved: %s", username)
		return token, nil
	}

	svc, err := callout.NewAuthorizationService(authNc,
		callout.Authorizer(authorizer),
		callout.ResponseSignerKey(issuerKP),
	)
	if err != nil {
		authNc.Close()
		return nil, nil, fmt.Errorf("create auth callout service: %w", err)
	}

	logger.Info("Auth callout service started")
	return authNc, svc, nil
}
