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

// Validator checks whether (username, password) is a valid credential pair
// and returns the username on success. Implementations must be safe for
// concurrent use from multiple goroutines.
//
// The interface is deliberately narrow so a caching layer can wrap a
// dbValidator without touching any other code.
type Validator interface {
	Validate(ctx context.Context, username, password string) (bool, error)
}

// dbValidator validates credentials against Postgres using the same join
// that GenerateNatsRmmConfig uses to build the static config file.
type dbValidator struct {
	db        *sqlx.DB
	secretKey string
}

func (v *dbValidator) Validate(ctx context.Context, username, password string) (bool, error) {
	// The "tacticalrmm" superuser authenticates with SECRET_KEY.
	// No DB round-trip needed — this is the Django backend's service account.
	if username == "tacticalrmm" {
		return password == v.secretKey, nil
	}

	// Agent credentials: agent_id as username, auth_token.key as password.
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
		return false, fmt.Errorf("validate agent %s: %w", username, err)
	}
	return exists, nil
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
// $SYS.REQ.USER.AUTH and validates every incoming connection against the
// provided Validator.
//
// The returned *nats.Conn and *callout.AuthorizationService must be closed
// by the caller during shutdown.
func StartAuthCallout(
	logger *logrus.Logger,
	cfg DjangoConfig,
	validator Validator,
) (*nats.Conn, *callout.AuthorizationService, error) {
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
	// This user is defined in the NATS wrapper chart's config and has
	// permission to subscribe to $SYS.REQ.USER.AUTH.
	authUser := envOrDefault("AUTH_SERVICE_USER", "auth-service")
	authPass := envOrDefault("AUTH_SERVICE_PASS", cfg.Key)

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

	// The account name that authenticated users are placed into. In
	// centralized (non-operator) auth callout mode, the nats-server uses
	// UserClaims.Audience to resolve the target account by name. Must
	// match an account defined in the nats-server config. Defaults to
	// "$G" (the global account).
	targetAccount := envOrDefault("AUTH_TARGET_ACCOUNT", "$G")

	allowResponseExpires := envOrDefault("NATS_ALLOW_RESPONSE_EXPIRATION", "1435m")
	respExpiry, err := time.ParseDuration(allowResponseExpires)
	if err != nil {
		authNc.Close()
		return nil, nil, fmt.Errorf("parse NATS_ALLOW_RESPONSE_EXPIRATION %q: %w", allowResponseExpires, err)
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

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		ok, err := validator.Validate(ctx, username, password)
		if err != nil {
			authCalloutTotal.WithLabelValues("error").Inc()
			logger.Errorf("auth callout validate %s: %v", username, err)
			return "", fmt.Errorf("validation error")
		}
		if !ok {
			authCalloutTotal.WithLabelValues("rejected").Inc()
			logger.Debugf("auth callout rejected: %s", username)
			return "", fmt.Errorf("invalid credentials for %s", username)
		}

		// Build user claims with appropriate permissions.
		// Audience determines which nats-server account the user is placed
		// into (centralized/non-operator mode). IssuerAccount must NOT be
		// set in this mode — the server rejects it.
		uc := jwt.NewUserClaims(req.UserNkey)
		uc.Audience = targetAccount

		if username == "tacticalrmm" {
			// Superuser: full pub/sub access.
			uc.Pub.Allow.Add(">")
			uc.Sub.Allow.Add(">")
		} else {
			// Agent: restricted to own agent_id subject.
			uc.Pub.Allow.Add(username)
			uc.Sub.Allow.Add(username)
			uc.Resp = &jwt.ResponsePermission{
				MaxMsgs: jwt.NoLimit,
				Expires: respExpiry,
			}
		}

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
