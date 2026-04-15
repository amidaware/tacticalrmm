package natsapi

import (
	"github.com/sirupsen/logrus"
)

// Bootstrap runs the one-shot "generate nats-rmm.conf from the database and
// exit" path used by the tactical-nats container entrypoint before
// supervisord starts nats-server. It is intentionally separate from Svc():
//  1. Svc() connects to NATS as a client, but at bootstrap time nats-server
//     does not exist yet. Mixing the two would deadlock.
//  2. Bootstrap failures should cause the container to crashloop so we
//     notice the problem — Svc()'s subscriber path is expected to tolerate
//     transient errors without exiting.
//
// cfgPath is the path to nats-api.conf. In the Docker/K8s deployment it will
// usually be empty, and GetConfig falls back to environment variables. In
// standalone installs it points to /rmm/api/tacticalrmm/nats-api.conf.
// outPath is where nats-rmm.conf will be written (must be readable by
// nats-server at startup).
func Bootstrap(logger *logrus.Logger, cfgPath string, outPath string) {
	logger.Infof("Bootstrap: loading config (cfgPath=%q)", cfgPath)
	db, r, err := GetConfig(cfgPath)
	if err != nil {
		logger.Fatalf("Bootstrap: load config: %v", err)
	}
	defer db.Close()

	if err := GenerateNatsRmmConfig(logger, db, r.Key, outPath); err != nil {
		logger.Fatalf("Bootstrap: generate nats-rmm.conf: %v", err)
	}
	logger.Info("Bootstrap: done")
}
