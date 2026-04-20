package natslistener

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/nats-io/jwt/v2"
)

// countingValidator counts how many times its inner Validate is called.
// Used to assert cache hits vs misses.
type countingValidator struct {
	calls  int
	result *AuthResult
	err    error
}

func (c *countingValidator) Validate(_ context.Context, _, _ string) (*AuthResult, error) {
	c.calls++
	return c.result, c.err
}

func newTestCache(t *testing.T, inner Validator, ttl time.Duration, size int) *cacheValidator {
	t.Helper()
	t.Setenv("AUTH_CACHE_SIZE", "10")
	t.Setenv("AUTH_CACHE_TTL", ttl.String())
	c, err := NewCacheValidator(inner)
	if err != nil {
		t.Fatalf("NewCacheValidator: %v", err)
	}
	return c
}

func TestCache_HitServedFromCache(t *testing.T) {
	inner := &countingValidator{result: &AuthResult{
		Account: "TRMM",
		Pub:     jwt.Permission{Allow: jwt.StringList{"alice"}},
	}}
	c := newTestCache(t, inner, 1*time.Minute, 10)

	for i := 0; i < 5; i++ {
		res, err := c.Validate(context.Background(), "alice", "pw")
		if err != nil {
			t.Fatalf("iter %d: %v", i, err)
		}
		if res == nil || res.Account != "TRMM" {
			t.Fatalf("iter %d: unexpected result %+v", i, res)
		}
	}
	if inner.calls != 1 {
		t.Errorf("expected 1 inner call (cache should serve the rest), got %d", inner.calls)
	}
}

func TestCache_NegativeResultCached(t *testing.T) {
	inner := &countingValidator{result: nil, err: nil}
	c := newTestCache(t, inner, 1*time.Minute, 10)

	for i := 0; i < 3; i++ {
		res, err := c.Validate(context.Background(), "alice", "bad")
		if err != nil {
			t.Fatalf("iter %d: %v", i, err)
		}
		if res != nil {
			t.Fatalf("iter %d: expected rejection, got %+v", i, res)
		}
	}
	if inner.calls != 1 {
		t.Errorf("negative results must be cached to blunt brute-force; got %d inner calls", inner.calls)
	}
}

func TestCache_ErrorNotCached(t *testing.T) {
	inner := &countingValidator{err: errors.New("db hiccup")}
	c := newTestCache(t, inner, 1*time.Minute, 10)

	for i := 0; i < 3; i++ {
		_, err := c.Validate(context.Background(), "alice", "pw")
		if err == nil {
			t.Fatalf("iter %d: expected error", i)
		}
	}
	if inner.calls != 3 {
		t.Errorf("errors must NOT be cached; got %d inner calls, expected 3", inner.calls)
	}
}

func TestCache_TTLExpires(t *testing.T) {
	inner := &countingValidator{result: &AuthResult{Account: "TRMM"}}
	c := newTestCache(t, inner, 20*time.Millisecond, 10)

	if _, err := c.Validate(context.Background(), "alice", "pw"); err != nil {
		t.Fatalf("first call: %v", err)
	}
	time.Sleep(40 * time.Millisecond)
	if _, err := c.Validate(context.Background(), "alice", "pw"); err != nil {
		t.Fatalf("post-TTL call: %v", err)
	}
	if inner.calls != 2 {
		t.Errorf("TTL-expired entry should re-hit inner; got %d calls", inner.calls)
	}
}

func TestCache_InvalidateAll(t *testing.T) {
	inner := &countingValidator{result: &AuthResult{Account: "TRMM"}}
	c := newTestCache(t, inner, 1*time.Minute, 10)

	// Seed the cache.
	for _, u := range []string{"alice", "bob", "carol"} {
		if _, err := c.Validate(context.Background(), u, "pw"); err != nil {
			t.Fatalf("seed %s: %v", u, err)
		}
	}
	if inner.calls != 3 {
		t.Fatalf("seed should miss 3 times, got %d", inner.calls)
	}

	c.InvalidateAll()

	// All three users must re-hit the inner validator.
	for _, u := range []string{"alice", "bob", "carol"} {
		if _, err := c.Validate(context.Background(), u, "pw"); err != nil {
			t.Fatalf("post-invalidate %s: %v", u, err)
		}
	}
	if inner.calls != 6 {
		t.Errorf("after InvalidateAll, all entries should re-miss; got %d calls (expected 6)", inner.calls)
	}
}

func TestCache_KeysDistinctPerCredentialPair(t *testing.T) {
	// ("ab", "c") must not collide with ("a", "bc"). The null-byte
	// separator in cacheKey is what prevents this.
	k1 := cacheKey("ab", "c")
	k2 := cacheKey("a", "bc")
	if k1 == k2 {
		t.Fatalf("cacheKey collision between (ab,c) and (a,bc): both hash to %s", k1)
	}
}

func TestCache_SameUserDifferentPasswordMissesSeparately(t *testing.T) {
	inner := &countingValidator{result: nil} // always rejects
	c := newTestCache(t, inner, 1*time.Minute, 10)

	_, _ = c.Validate(context.Background(), "alice", "pw1")
	_, _ = c.Validate(context.Background(), "alice", "pw2")
	if inner.calls != 2 {
		t.Errorf("different passwords should cache independently; got %d calls", inner.calls)
	}
}
