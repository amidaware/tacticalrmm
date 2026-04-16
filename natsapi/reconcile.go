package natsapi

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"sync"

	"github.com/jmoiron/sqlx"
)

var (
	hashMu         sync.Mutex
	lastConfigHash string
)

func setHash(h string) {
	hashMu.Lock()
	lastConfigHash = h
	hashMu.Unlock()
}

func getHash() string {
	hashMu.Lock()
	defer hashMu.Unlock()
	return lastConfigHash
}

// computeConfigHash queries Postgres for all (agent_id, token) pairs in
// deterministic order and streams them through MD5. The resulting hash
// changes if and only if the set of agent credentials changes. The ORDER BY
// is essential: without it the same set of agents could produce different
// hashes on different ticks, causing spurious drift detection.
func computeConfigHash(ctx context.Context, db *sqlx.DB) (string, int, error) {
	rows, err := db.QueryContext(ctx, `
		SELECT a.agent_id, t.key
		FROM agents_agent a
		JOIN accounts_user u ON u.agent_id = a.id
		JOIN authtoken_token t ON t.user_id = u.id
		ORDER BY a.agent_id ASC
	`)
	if err != nil {
		return "", 0, err
	}
	defer rows.Close()

	h := md5.New()
	count := 0
	for rows.Next() {
		var agentID, token string
		if err := rows.Scan(&agentID, &token); err != nil {
			return "", 0, err
		}
		count++
		fmt.Fprintf(h, "%s:%s;", agentID, token)
	}
	return hex.EncodeToString(h.Sum(nil)), count, rows.Err()
}
