package natsapi

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"sync/atomic"
	"time"

	lru "github.com/hashicorp/golang-lru/v2"
)

// cacheValidator wraps an inner Validator with a time-bounded LRU cache.
// Designed for the DB-backed agent auth path, where a 10K-agent reconnect
// storm otherwise pounds Postgres with identical queries.
//
// Key construction: sha256(username | 0x00 | password). We never store
// cleartext credentials in the cache, and the separator prevents
// ("ab", "c") colliding with ("a", "bc").
//
// Negative caching: a rejection (nil AuthResult, nil error) is cached
// alongside approvals. Without it, a wrong-password brute-force cycles the
// DB on every attempt. Errors are NOT cached — transient DB failures
// shouldn't poison the cache.
//
// Invalidation: InvalidateAll is called from the trmm.nats.reload subject
// handler (see svc.go). This restores the subject's original meaning after
// Layer 3 — it used to force nats-rmm.conf regeneration; now it forces
// the validator to re-check against Postgres on the next connection.
type cacheValidator struct {
	inner    Validator
	cache    *lru.Cache[string, cacheEntry]
	ttl      time.Duration
	hits     atomic.Uint64
	misses   atomic.Uint64
	curSize  atomic.Int64
}

type cacheEntry struct {
	result    *AuthResult // may be nil to cache a negative result
	expiresAt time.Time
}

// NewCacheValidator wraps inner with an LRU + TTL cache. Size and TTL are
// read from env:
//
//	AUTH_CACHE_SIZE — max entries (default 10000)
//	AUTH_CACHE_TTL  — per-entry TTL (default 5m)
func NewCacheValidator(inner Validator) (*cacheValidator, error) {
	size := envIntOrDefault("AUTH_CACHE_SIZE", 10000)
	ttl := parseDurationEnv("AUTH_CACHE_TTL", 5*time.Minute)
	c, err := lru.New[string, cacheEntry](size)
	if err != nil {
		return nil, err
	}
	return &cacheValidator{inner: inner, cache: c, ttl: ttl}, nil
}

func cacheKey(username, password string) string {
	h := sha256.New()
	h.Write([]byte(username))
	h.Write([]byte{0})
	h.Write([]byte(password))
	return hex.EncodeToString(h.Sum(nil))
}

func (c *cacheValidator) Validate(ctx context.Context, username, password string) (*AuthResult, error) {
	k := cacheKey(username, password)
	now := time.Now()

	if entry, ok := c.cache.Get(k); ok {
		if now.Before(entry.expiresAt) {
			c.hits.Add(1)
			authCacheHitsTotal.Inc()
			return entry.result, nil
		}
		// Expired — drop it so size gauge reflects reality.
		c.cache.Remove(k)
	}
	c.misses.Add(1)
	authCacheMissesTotal.Inc()

	result, err := c.inner.Validate(ctx, username, password)
	if err != nil {
		// Don't cache errors — a transient DB hiccup shouldn't poison
		// the entry for the full TTL.
		return nil, err
	}
	evicted := c.cache.Add(k, cacheEntry{result: result, expiresAt: now.Add(c.ttl)})
	if evicted {
		// Size held at max; no net change.
	} else {
		c.curSize.Add(1)
	}
	authCacheSize.Set(float64(c.cache.Len()))
	return result, nil
}

// InvalidateAll drops every cached entry. Called on trmm.nats.reload so a
// token rotation or agent deletion takes effect within one NATS round-trip
// instead of waiting for the TTL.
func (c *cacheValidator) InvalidateAll() {
	c.cache.Purge()
	c.curSize.Store(0)
	authCacheSize.Set(0)
}
