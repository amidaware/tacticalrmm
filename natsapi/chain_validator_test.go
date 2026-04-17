package natsapi

import (
	"context"
	"errors"
	"testing"

	"github.com/nats-io/jwt/v2"
)

// fakeValidator is a test double whose behavior is driven by the test —
// return an approval, a rejection, or an error on demand.
type fakeValidator struct {
	name     string
	match    string // username this validator "owns"
	accept   bool
	err      error
	callsGot []string
}

func (f *fakeValidator) Validate(_ context.Context, username, _ string) (*AuthResult, error) {
	f.callsGot = append(f.callsGot, username)
	if f.err != nil {
		return nil, f.err
	}
	if username != f.match {
		return nil, nil
	}
	if !f.accept {
		return nil, nil
	}
	return &AuthResult{
		Account: "TEST-" + f.name,
		Pub:     jwt.Permission{Allow: jwt.StringList{username}},
		Sub:     jwt.Permission{Allow: jwt.StringList{username}},
	}, nil
}

func TestChainValidator_FirstMatchWins(t *testing.T) {
	v1 := &fakeValidator{name: "first", match: "alice", accept: true}
	v2 := &fakeValidator{name: "second", match: "alice", accept: true}
	c := NewChainValidator(v1, v2)

	res, err := c.Validate(context.Background(), "alice", "pw")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res == nil || res.Account != "TEST-first" {
		t.Fatalf("expected first validator to win, got %+v", res)
	}
	if len(v2.callsGot) != 0 {
		t.Fatalf("second validator should not have been called, got calls=%v", v2.callsGot)
	}
}

func TestChainValidator_FallThrough(t *testing.T) {
	v1 := &fakeValidator{name: "first", match: "nobody"}
	v2 := &fakeValidator{name: "second", match: "alice", accept: true}
	c := NewChainValidator(v1, v2)

	res, err := c.Validate(context.Background(), "alice", "pw")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res == nil || res.Account != "TEST-second" {
		t.Fatalf("expected second validator to match, got %+v", res)
	}
	if len(v1.callsGot) != 1 {
		t.Fatalf("first validator should have been tried, got calls=%v", v1.callsGot)
	}
}

func TestChainValidator_RejectionAllTheWay(t *testing.T) {
	v1 := &fakeValidator{name: "first", match: "nobody"}
	v2 := &fakeValidator{name: "second", match: "nobody"}
	c := NewChainValidator(v1, v2)

	res, err := c.Validate(context.Background(), "alice", "pw")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res != nil {
		t.Fatalf("expected rejection, got %+v", res)
	}
}

func TestChainValidator_ErrorShortCircuits(t *testing.T) {
	boom := errors.New("boom")
	v1 := &fakeValidator{name: "first", err: boom}
	v2 := &fakeValidator{name: "second", match: "alice", accept: true}
	c := NewChainValidator(v1, v2)

	_, err := c.Validate(context.Background(), "alice", "pw")
	if !errors.Is(err, boom) {
		t.Fatalf("expected boom error to propagate, got %v", err)
	}
	if len(v2.callsGot) != 0 {
		t.Fatalf("second validator should not have been called after error")
	}
}

func TestChainValidator_NilEntriesSkipped(t *testing.T) {
	v := &fakeValidator{name: "only", match: "alice", accept: true}
	c := NewChainValidator(nil, v, nil)

	res, err := c.Validate(context.Background(), "alice", "pw")
	if err != nil || res == nil || res.Account != "TEST-only" {
		t.Fatalf("nil entries should be skipped; got res=%+v err=%v", res, err)
	}
}

func TestSuperuserValidator_Approval(t *testing.T) {
	t.Setenv("AUTH_TARGET_ACCOUNT", "TRMM")
	v := NewSuperuserValidator("supersecret")
	res, err := v.Validate(context.Background(), "tacticalrmm", "supersecret")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res == nil {
		t.Fatal("expected approval for correct SECRET_KEY")
	}
	if res.Account != "TRMM" {
		t.Errorf("expected Account=TRMM, got %q", res.Account)
	}
	if len(res.Pub.Allow) != 1 || res.Pub.Allow[0] != ">" {
		t.Errorf("expected Pub.Allow=[\">\"], got %v", res.Pub.Allow)
	}
}

func TestSuperuserValidator_WrongPasswordFallsThrough(t *testing.T) {
	v := NewSuperuserValidator("supersecret")
	res, err := v.Validate(context.Background(), "tacticalrmm", "wrong")
	if err != nil || res != nil {
		t.Fatalf("expected nil,nil for bad superuser password; got res=%+v err=%v", res, err)
	}
}

func TestSuperuserValidator_OtherUserSkipped(t *testing.T) {
	v := NewSuperuserValidator("supersecret")
	res, err := v.Validate(context.Background(), "someagent", "whatever")
	if err != nil || res != nil {
		t.Fatalf("expected nil,nil for non-superuser; got res=%+v err=%v", res, err)
	}
}
