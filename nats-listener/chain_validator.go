package natslistener

import (
	"context"

	"github.com/nats-io/jwt/v2"
)

// chainValidator tries each inner Validator in order and returns the first
// one that matches (non-nil AuthResult). A (nil, nil) return from an inner
// validator means "I don't own this user" — move on to the next one. A
// non-nil error short-circuits with that error (treated as validation
// failure by the authorizer, not as "try next").
//
// Ordering matters: put the fastest, cheapest validators first so common
// cases don't pay the cost of the expensive ones. For the current chain
// the order is:
//
//  1. superuserValidator — in-memory string compare, no I/O
//  2. staticValidator    — in-memory map compare, no I/O (optional; nil if DEVICES_* unset)
//  3. cachedValidator    — in-memory LRU hit OR DB query (wraps dbValidator)
type chainValidator struct {
	inner []Validator
}

// NewChainValidator returns a chain that ignores any nil entries so callers
// can pass optional validators (e.g. staticValidator) without branching.
func NewChainValidator(validators ...Validator) *chainValidator {
	nonNil := make([]Validator, 0, len(validators))
	for _, v := range validators {
		if v != nil {
			nonNil = append(nonNil, v)
		}
	}
	return &chainValidator{inner: nonNil}
}

func (c *chainValidator) Validate(ctx context.Context, username, password string) (*AuthResult, error) {
	for _, v := range c.inner {
		result, err := v.Validate(ctx, username, password)
		if err != nil {
			return nil, err
		}
		if result != nil {
			return result, nil
		}
	}
	return nil, nil
}

// superuserValidator handles only the "tacticalrmm" service account,
// authenticated via the Django SECRET_KEY. Extracted from dbValidator so
// bad-password attempts against the superuser don't pay a wasted DB trip
// at the dbValidator step of the chain.
type superuserValidator struct {
	secretKey   string
	trmmAccount string
}

// NewSuperuserValidator reads AUTH_TARGET_ACCOUNT from env (same knob that
// dbValidator uses) so both land in the same account.
func NewSuperuserValidator(secretKey string) *superuserValidator {
	return &superuserValidator{
		secretKey:   secretKey,
		trmmAccount: envOrDefault("AUTH_TARGET_ACCOUNT", "$G"),
	}
}

func (v *superuserValidator) Validate(_ context.Context, username, password string) (*AuthResult, error) {
	if username != "tacticalrmm" {
		return nil, nil
	}
	if !constantTimeEqual(password, v.secretKey) {
		// Known user, bad password. Fall through to let the rest of the
		// chain reject cleanly — a later validator might legitimately
		// handle a username==tacticalrmm match under a different
		// configuration (e.g. DEVICES_*_USER misconfigured). In practice
		// the chain ends with rejection.
		return nil, nil
	}
	return &AuthResult{
		Account: v.trmmAccount,
		Pub:     jwt.Permission{Allow: jwt.StringList{">"}},
		Sub:     jwt.Permission{Allow: jwt.StringList{">"}},
	}, nil
}
