package natsapi

import (
	"fmt"

	"github.com/jmoiron/sqlx"
	"github.com/sirupsen/logrus"
)

// verifySchema is a startup sanity check that fails fast if the Django side
// has renamed or dropped any column nats-api writes to.
//
// Without it, a schema drift turns every agent check-in into a silent
// UPDATE error: the service looks healthy (subscribed, no panics, steady
// message rate, metrics scraping) while dropping data for the entire fleet.
// The only signal would be nats_api_jobs_processed_total{result="error"}
// climbing — which is exactly the kind of slow-burn failure that sits
// unnoticed for hours.
//
// Each probe is a single `SELECT ... WHERE FALSE` round-trip. Postgres
// parses and validates every referenced column before execution, so a
// single missing column fails the whole query with an error that names
// the offender directly ("column X does not exist"). No per-column loop,
// no information_schema introspection, no generated migration metadata.
//
// This is column-existence only. Column type drift (CharField → Integer)
// is deliberately out of scope: the per-row UPDATE already surfaces a
// clear "invalid input syntax for type …" error, and that failure is
// visible on the {result="error"} counter with the offending handler
// label attached.
func verifySchema(logger *logrus.Logger, db *sqlx.DB, openframeMode bool) error {
	probes := []struct {
		name string
		sql  string
	}{
		{
			// Every column referenced by Svc()'s handler UPDATEs, plus
			// agent_id which anchors every WHERE clause. Keep this list
			// in sync with svc.go — it is the schema contract for the
			// check-in path.
			name: "agents_agent (check-in columns)",
			sql: `SELECT agent_id, last_seen, version, public_ip, hostname,
			             operating_system, plat, total_ram, boot_time,
			             needs_reboot, logged_in_username, goarch,
			             last_logged_in_user, disks, services, wmi_detail
			      FROM agents_agent WHERE FALSE`,
		},
		{
			// The auth callout path: dbValidator.Validate runs this exact
			// join on every agent connection (authcallout.go). A dropped
			// join column would silently cause every agent to fail auth.
			name: "agents_agent JOIN accounts_user JOIN authtoken_token (auth callout query)",
			sql: `SELECT a.agent_id, a.id, u.agent_id, u.id, t.user_id, t.key
			      FROM agents_agent a
			      JOIN accounts_user u ON u.agent_id = a.id
			      JOIN authtoken_token t ON t.user_id = u.id
			      WHERE FALSE`,
		},
	}

	// time_zone is only written in OPENFRAME_MODE=true, so we only
	// require it to exist on installs that have opted in. Checking it
	// unconditionally would crashloop vanilla tactical deployments that
	// have never carried the column.
	if openframeMode {
		probes = append(probes, struct {
			name string
			sql  string
		}{
			name: "agents_agent.time_zone (openframe mode)",
			sql:  `SELECT time_zone FROM agents_agent WHERE FALSE`,
		})
	}

	for _, p := range probes {
		if _, err := db.Exec(p.sql); err != nil {
			return fmt.Errorf("%s: %w", p.name, err)
		}
	}
	logger.Infof("schema verification ok (%d probes)", len(probes))
	return nil
}
