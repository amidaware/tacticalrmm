package natsapi

import (
	"context"
	"errors"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/jmoiron/sqlx"
)

func newMockDB(t *testing.T) (*sqlx.DB, sqlmock.Sqlmock) {
	t.Helper()
	raw, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New: %v", err)
	}
	return sqlx.NewDb(raw, "postgres"), mock
}

func TestDBValidator_AgentApproved(t *testing.T) {
	t.Setenv("AUTH_TARGET_ACCOUNT", "TRMM")
	t.Setenv("NATS_ALLOW_RESPONSE_EXPIRATION", "30m")
	db, mock := newMockDB(t)
	defer db.Close()

	mock.ExpectQuery("SELECT EXISTS").
		WithArgs("agent-123", "tok-xyz").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(true))

	v, err := NewDBValidator(db)
	if err != nil {
		t.Fatalf("NewDBValidator: %v", err)
	}

	res, err := v.Validate(context.Background(), "agent-123", "tok-xyz")
	if err != nil {
		t.Fatalf("Validate: %v", err)
	}
	if res == nil {
		t.Fatal("expected approval")
	}
	if res.Account != "TRMM" {
		t.Errorf("Account=%q, want TRMM", res.Account)
	}
	if len(res.Pub.Allow) != 1 || res.Pub.Allow[0] != "agent-123" {
		t.Errorf("Pub.Allow=%v, want [agent-123]", res.Pub.Allow)
	}
	// _INBOX.*.* is required for any nc.Request() reply the agent might
	// receive. Removing it silently breaks future request/reply traffic.
	wantSub := []string{"agent-123", "_INBOX.*.*"}
	if got := []string(res.Sub.Allow); len(got) != len(wantSub) || got[0] != wantSub[0] || got[1] != wantSub[1] {
		t.Errorf("Sub.Allow=%v, want %v", got, wantSub)
	}
	if res.Resp == nil {
		t.Fatal("agents must get a Resp permission")
	}
	if res.Resp.Expires.String() != "30m0s" {
		t.Errorf("Resp.Expires=%s, want 30m0s", res.Resp.Expires)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unmet expectations: %v", err)
	}
}

func TestDBValidator_AgentNotFound(t *testing.T) {
	db, mock := newMockDB(t)
	defer db.Close()

	mock.ExpectQuery("SELECT EXISTS").
		WithArgs("ghost", "bad").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(false))

	v, _ := NewDBValidator(db)
	res, err := v.Validate(context.Background(), "ghost", "bad")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res != nil {
		t.Fatalf("expected nil AuthResult for unknown agent, got %+v", res)
	}
}

func TestDBValidator_QueryError(t *testing.T) {
	db, mock := newMockDB(t)
	defer db.Close()

	boom := errors.New("connection refused")
	mock.ExpectQuery("SELECT EXISTS").
		WithArgs("agent-1", "tok").
		WillReturnError(boom)

	v, _ := NewDBValidator(db)
	_, err := v.Validate(context.Background(), "agent-1", "tok")
	if err == nil {
		t.Fatal("expected DB error to propagate")
	}
}

func TestDBValidator_NoSuperuserBranch(t *testing.T) {
	// After the chain refactor, dbValidator should NOT handle the
	// tacticalrmm superuser — that lives in superuserValidator. A DB
	// lookup for "tacticalrmm" is fine because no row will match, but
	// this test guards against someone re-adding the SECRET_KEY
	// shortcut, which would create a divergent auth path.
	db, mock := newMockDB(t)
	defer db.Close()

	mock.ExpectQuery("SELECT EXISTS").
		WithArgs("tacticalrmm", "anything").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(false))

	v, _ := NewDBValidator(db)
	res, err := v.Validate(context.Background(), "tacticalrmm", "anything")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res != nil {
		t.Fatal("dbValidator must not approve the superuser — that's superuserValidator's job")
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("dbValidator should have issued a DB query for username=tacticalrmm: %v", err)
	}
}
