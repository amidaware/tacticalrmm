package natsapi

import (
	"context"
	"testing"
)

func TestNewStaticValidator_NoEnv_ReturnsNil(t *testing.T) {
	// All DEVICES_* vars unset — validator must be nil so standalone
	// installs aren't forced to wire pass-through credentials.
	v := NewStaticValidator()
	if v != nil {
		t.Fatal("expected nil validator when no DEVICES_* env set")
	}
}

func TestStaticValidator_AdminApproved(t *testing.T) {
	t.Setenv("DEVICES_ADMIN_USER", "admin")
	t.Setenv("DEVICES_ADMIN_PASS", "admin_password")
	v := NewStaticValidator()

	res, err := v.Validate(context.Background(), "admin", "admin_password")
	if err != nil || res == nil {
		t.Fatalf("expected approval; got res=%+v err=%v", res, err)
	}
	if res.Account != "SYS" {
		t.Errorf("admin should land in SYS account, got %q", res.Account)
	}
	if len(res.Pub.Allow) != 1 || res.Pub.Allow[0] != ">" {
		t.Errorf("admin Pub.Allow=[\">\"], got %v", res.Pub.Allow)
	}
}

func TestStaticValidator_AdminBadPassword(t *testing.T) {
	t.Setenv("DEVICES_ADMIN_USER", "admin")
	t.Setenv("DEVICES_ADMIN_PASS", "admin_password")
	v := NewStaticValidator()

	res, err := v.Validate(context.Background(), "admin", "wrong")
	if err != nil || res != nil {
		t.Fatalf("expected nil,nil; got res=%+v err=%v", res, err)
	}
}

func TestStaticValidator_MachineEmptyPasswordApproved(t *testing.T) {
	// The wrapper configmap declares an empty password for the machine
	// user — this behavior must be preserved exactly under callout.
	t.Setenv("DEVICES_MACHINE_USER", "machine")
	v := NewStaticValidator()

	res, err := v.Validate(context.Background(), "machine", "")
	if err != nil || res == nil {
		t.Fatalf("expected approval for empty-password machine user; got res=%+v err=%v", res, err)
	}
	if res.Account != "DEVICES" {
		t.Errorf("machine should land in DEVICES account, got %q", res.Account)
	}
}

func TestStaticValidator_MachineNonEmptyPasswordRejected(t *testing.T) {
	t.Setenv("DEVICES_MACHINE_USER", "machine")
	v := NewStaticValidator()

	res, err := v.Validate(context.Background(), "machine", "oops")
	if err != nil || res != nil {
		t.Fatalf("non-empty password for machine should be rejected; got res=%+v err=%v", res, err)
	}
}

func TestStaticValidator_ServiceApproved(t *testing.T) {
	t.Setenv("DEVICES_SERVICE_USER", "service")
	t.Setenv("DEVICES_SERVICE_PASS", "service_pass")
	v := NewStaticValidator()

	res, err := v.Validate(context.Background(), "service", "service_pass")
	if err != nil || res == nil {
		t.Fatalf("expected approval; got res=%+v err=%v", res, err)
	}
	if res.Account != "DEVICES" {
		t.Errorf("service should land in DEVICES account, got %q", res.Account)
	}
}

func TestStaticValidator_UnknownUserFallsThrough(t *testing.T) {
	t.Setenv("DEVICES_ADMIN_USER", "admin")
	t.Setenv("DEVICES_ADMIN_PASS", "admin_password")
	v := NewStaticValidator()

	res, err := v.Validate(context.Background(), "notadmin", "whatever")
	if err != nil || res != nil {
		t.Fatalf("unknown user should yield nil,nil; got res=%+v err=%v", res, err)
	}
}

// TestStaticValidator_MachinePermissionsMatchConfigmap is the
// permission-drift canary. If someone edits
// openframe-saas-tenant/manifests/integrated-tools/nats/templates/configmap.yaml
// to add a subject for the machine user, this test should fail until
// machinePubAllow / machineSubAllow are updated.
func TestStaticValidator_MachinePermissionsMatchConfigmap(t *testing.T) {
	t.Setenv("DEVICES_MACHINE_USER", "machine")
	v := NewStaticValidator()
	res, _ := v.Validate(context.Background(), "machine", "")
	if res == nil {
		t.Fatal("unexpected rejection")
	}

	expectedPub := []string{
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
	expectedSub := []string{
		"_INBOX.*.*",
		"machine.*.tool-installation.inbox",
		"machine.*.client-update.inbox",
		"machine.*.tool.update.inbox",
		"chat.*.message",
		"chat.*.admin-message",
	}

	if got := []string(res.Pub.Allow); !stringSlicesEqual(got, expectedPub) {
		t.Errorf("machine Pub.Allow drift:\n got  %v\n want %v", got, expectedPub)
	}
	if got := []string(res.Sub.Allow); !stringSlicesEqual(got, expectedSub) {
		t.Errorf("machine Sub.Allow drift:\n got  %v\n want %v", got, expectedSub)
	}
}

func stringSlicesEqual(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
