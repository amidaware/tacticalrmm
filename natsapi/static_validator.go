package natsapi

import (
	"context"
	"crypto/subtle"
	"os"

	"github.com/nats-io/jwt/v2"
)

// staticValidator handles non-TRMM users that the shared OpenFrame NATS
// broker serves: the SYS admin and the DEVICES machine/service users. Under
// centralized auth callout, every non-exempt user is routed through the
// callout, so these accounts cannot rely on their old nats-server-native
// static-config auth — this validator restores it.
//
// The permission sets embedded here MUST stay in sync with the wrapper
// chart's spec at:
//
//	openframe-saas-tenant/manifests/integrated-tools/nats/templates/configmap.yaml
//
// If the wrapper's configmap declares a new subject for one of these users,
// add it below. The configmap's user.password fields become advisory only —
// the actual credential check happens here.
//
// Environment contract:
//
//	DEVICES_ADMIN_USER   / DEVICES_ADMIN_PASS   → SYS account, full pub/sub
//	DEVICES_MACHINE_USER / (password always "") → DEVICES account, subject ACLs
//	DEVICES_SERVICE_USER / DEVICES_SERVICE_PASS → DEVICES account, full pub/sub
//
// If a `*_USER` is unset the validator simply does not match that username
// — the chain can fall through. This keeps the validator optional so
// standalone TacticalRMM installs (non-OpenFrame) aren't forced to wire it.
type staticValidator struct {
	adminUser, adminPass     string
	machineUser              string // password is always empty by design
	serviceUser, servicePass string
}

// NewStaticValidator reads the DEVICES_* env vars and returns a validator.
// It returns nil if no pass-through users are configured, so callers can
// cheaply omit it from the chain.
func NewStaticValidator() *staticValidator {
	v := &staticValidator{
		adminUser:   os.Getenv("DEVICES_ADMIN_USER"),
		adminPass:   os.Getenv("DEVICES_ADMIN_PASS"),
		machineUser: os.Getenv("DEVICES_MACHINE_USER"),
		serviceUser: os.Getenv("DEVICES_SERVICE_USER"),
		servicePass: os.Getenv("DEVICES_SERVICE_PASS"),
	}
	if v.adminUser == "" && v.machineUser == "" && v.serviceUser == "" {
		return nil
	}
	return v
}

// Subject permission sets for the DEVICES `machine` user. Copied verbatim
// from openframe-saas-tenant/manifests/integrated-tools/nats/templates/configmap.yaml:34-58.
// Keep in sync.
var (
	machinePubAllow = []string{
		"$JS.API.CONSUMER.CREATE.TOOL_INSTALLATION.*.machine.*.tool-installation",
		"$JS.ACK.TOOL_INSTALLATION.>",
		"$JS.API.CONSUMER.CREATE.CLIENT_UPDATE.*.machine.all.client-update",
		"$JS.ACK.CLIENT_UPDATE.>",
		"$JS.API.CONSUMER.CREATE.TOOL_UPDATE.*.machine.all.tool.*.update",
		"$JS.API.CONSUMER.CREATE.TOOL_UPDATE.>",
		"$JS.ACK.TOOL_UPDATE.>",
		"machine.*.tool-connection",
		"machine.*.heartbeat",
		"machine.*.installed-agent",
	}
	machineSubAllow = []string{
		"_INBOX.*.*",
		"machine.*.tool-installation.inbox",
		"machine.*.client-update.inbox",
		"machine.*.tool.update.inbox",
		"chat.*.message",
		"chat.*.admin-message",
	}
)

// constantTimeEqual avoids a timing side-channel on password comparison.
// Not strictly necessary for cached creds in a trusted cluster, but cheap
// insurance.
func constantTimeEqual(a, b string) bool {
	return subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1
}

func (v *staticValidator) Validate(_ context.Context, username, password string) (*AuthResult, error) {
	switch username {
	case v.adminUser:
		if v.adminUser == "" || !constantTimeEqual(password, v.adminPass) {
			return nil, nil
		}
		return &AuthResult{
			Account: "SYS",
			Pub:     jwt.Permission{Allow: jwt.StringList{">"}},
			Sub:     jwt.Permission{Allow: jwt.StringList{">"}},
		}, nil

	case v.machineUser:
		// Empty password by design — the configmap declares no password
		// for the machine user, relying entirely on subject ACLs.
		if v.machineUser == "" || password != "" {
			return nil, nil
		}
		return &AuthResult{
			Account: "DEVICES",
			Pub:     jwt.Permission{Allow: append(jwt.StringList(nil), machinePubAllow...)},
			Sub:     jwt.Permission{Allow: append(jwt.StringList(nil), machineSubAllow...)},
		}, nil

	case v.serviceUser:
		if v.serviceUser == "" || !constantTimeEqual(password, v.servicePass) {
			return nil, nil
		}
		return &AuthResult{
			Account: "DEVICES",
			Pub:     jwt.Permission{Allow: jwt.StringList{">"}},
			Sub:     jwt.Permission{Allow: jwt.StringList{">"}},
		}, nil
	}

	// Unknown username — let the next validator in the chain try.
	return nil, nil
}
