package natsapi

import (
	"context"
	"encoding/json"
	"fmt"
	"hash/maphash"
	"os"
	"os/signal"
	"reflect"
	"runtime/debug"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"
	nats "github.com/nats-io/nats.go"
	"github.com/sirupsen/logrus"
	"github.com/ugorji/go/codec"
	trmm "github.com/wh1te909/trmm-shared"
)

// natsReloadSubject is the NATS subject the backend publishes to when the set
// of agents changes (token rotation, agent delete). The subscriber purges
// the auth validator cache so the next connection re-checks Postgres.
// Kept short and namespaced so it doesn't collide with agent subjects.
const natsReloadSubject = "trmm.nats.reload"

// Sharded worker pool: dbShards independent queues, one worker per shard,
// each with its own *sqlx.DB so a slow-query pile-up on one shard can't
// drain the connection pool the others depend on. Jobs are routed by
// agentID. Full shards drop with a warning rather than block — a blocked
// handler on an async subscription stalls every other subscriber on the
// same connection, including the reload subscriber.
const (
	dbShards         = 10
	dbShardQueueSize = 32
	dbShardMaxConns  = 2
)

// dbJobTimeout caps one DB call so a stuck Postgres can't permanently
// pin a shard's only worker. natsDrainTimeout + workerShutdownGrace
// must fit inside the K8s SIGTERM grace window (30s).
const (
	dbJobTimeout        = 10 * time.Second
	natsDrainTimeout    = 10 * time.Second
	workerShutdownGrace = 15 * time.Second
)

// Randomized per process so a malicious agent can't craft IDs that all
// land on one shard.
var shardSeed = maphash.MakeSeed()

func shardFor(agentID string) int {
	if agentID == "" {
		return 0
	}
	return int(maphash.String(shardSeed, agentID) % uint64(dbShards))
}

type dbJob struct {
	name    string
	agentID string
	fn      func(ctx context.Context, db *sqlx.DB) error
}

// Panic recovery is load-bearing: without it, a single bad handler would
// permanently shrink the worker pool.
func runJob(parent context.Context, logger *logrus.Logger, db *sqlx.DB, j dbJob) {
	defer func() {
		if r := recover(); r != nil {
			jobsProcessedTotal.WithLabelValues(j.name, "panic").Inc()
			logger.Errorf("%s: panic: %v\n%s", j.name, r, debug.Stack())
		}
	}()
	ctx, cancel := context.WithTimeout(parent, dbJobTimeout)
	defer cancel()
	start := time.Now()
	err := j.fn(ctx, db)
	dbDurationSeconds.WithLabelValues(j.name).Observe(time.Since(start).Seconds())
	if err != nil {
		jobsProcessedTotal.WithLabelValues(j.name, "error").Inc()
		logger.Errorf("%s: %v", j.name, err)
		return
	}
	jobsProcessedTotal.WithLabelValues(j.name, "ok").Inc()
}

func Svc(logger *logrus.Logger, cfg string) {
	logger.Debugln("Starting Svc()")
	db, r, err := GetConfig(cfg)
	if err != nil {
		logger.Fatalln(err)
	}
	// Main db is only used by verifySchema at startup; the auth-callout path
	// owns its own pool, and the check-in path owns one pool per shard.
	db.SetMaxOpenConns(4)
	db.SetMaxIdleConns(4)

	openframeMode := strings.EqualFold(os.Getenv("OPENFRAME_MODE"), "true")

	if err := verifySchema(logger, db, openframeMode); err != nil {
		logger.Fatalf("schema verification failed: %v", err)
	}

	metricsEnabled := StartMetricsServer(logger)
	if metricsEnabled {
		queueCapacity.Set(float64(dbShards * dbShardQueueSize))
	}

	// Cancelled on shutdown to cut every in-flight db.ExecContext at once.
	rootCtx, rootCancel := context.WithCancel(context.Background())
	defer rootCancel()

	shards := make([]chan dbJob, dbShards)
	shardDBs := make([]*sqlx.DB, dbShards)
	var workers sync.WaitGroup
	for i := range shards {
		sdb, err := openDB(r, dbShardMaxConns)
		if err != nil {
			logger.Fatalf("open shard db %d: %v", i, err)
		}
		shardDBs[i] = sdb
		shards[i] = make(chan dbJob, dbShardQueueSize)
		workers.Add(1)
		go func(idx int) {
			defer workers.Done()
			for j := range shards[idx] {
				runJob(rootCtx, logger, shardDBs[idx], j)
			}
		}(i)
	}

	if metricsEnabled {
		go func() {
			t := time.NewTicker(time.Second)
			defer t.Stop()
			for {
				select {
				case <-rootCtx.Done():
					return
				case <-t.C:
					for i, ch := range shards {
						shardQueueDepth.WithLabelValues(shardLabels[i]).Set(float64(len(ch)))
					}
				}
			}
		}()
	}

	enqueue := func(job dbJob) {
		idx := shardFor(job.agentID)
		select {
		case shards[idx] <- job:
		default:
			jobsDroppedTotal.WithLabelValues(job.name).Inc()
			logger.Warnf("shard %d queue full (cap=%d), dropping %s agent=%s", idx, dbShardQueueSize, job.name, job.agentID)
		}
	}

	// Auth callout: validate agent credentials against Postgres on each
	// new NATS connection. Uses a separate NATS connection (auth-service
	// user in AUTH account) and a separate DB pool to isolate from the
	// telemetry path.
	//
	// Started BEFORE the main "tacticalrmm" connection because the main
	// connection is itself authenticated by this service. If we connected
	// main first, it would get auth-rejected repeatedly until the callout
	// subscription is ready.
	authDB, err := openDB(r, envIntOrDefault("AUTH_CALLOUT_DB_MAX_CONNS", 16))
	if err != nil {
		logger.Fatalf("open auth callout db: %v", err)
	}
	dbV, err := NewDBValidator(authDB)
	if err != nil {
		authDB.Close()
		logger.Fatalf("construct auth callout db validator: %v", err)
	}
	authCache, err := NewCacheValidator(dbV)
	if err != nil {
		authDB.Close()
		logger.Fatalf("construct auth callout cache: %v", err)
	}
	// Chain order: cheapest in-memory checks first, DB last.
	// NewStaticValidator returns nil when no DEVICES_* env vars are set,
	// and NewChainValidator skips nil entries — so standalone TRMM installs
	// (non-OpenFrame) get a two-link chain.
	validator := NewChainValidator(
		NewSuperuserValidator(r.Key),
		NewStaticValidator(),
		authCache,
	)
	authNc, authSvc, err := StartAuthCallout(rootCtx, logger, r, validator)
	if err != nil {
		authDB.Close()
		logger.Fatalf("start auth callout: %v", err)
	}
	authCleanup := func() {
		if err := authSvc.Stop(); err != nil {
			logger.Errorf("shutdown: stop auth callout: %v", err)
		}
		authNc.Close()
		authDB.Close()
	}

	// Sample sqlx.DB.Stats() into gauges every 10s. Saturation of this
	// pool == new agent connections stalling, so surfacing it as a
	// series is worth the cost of a ticker.
	go func() {
		t := time.NewTicker(10 * time.Second)
		defer t.Stop()
		var lastWait uint64
		for {
			select {
			case <-rootCtx.Done():
				return
			case <-t.C:
				s := authDB.Stats()
				authDBOpenConnections.Set(float64(s.OpenConnections))
				authDBInUseConnections.Set(float64(s.InUse))
				if wc := uint64(s.WaitCount); wc > lastWait {
					authDBWaitCountTotal.Add(float64(wc - lastWait))
					lastWait = wc
				}
			}
		}
	}()

	// Closed by nats.ClosedHandler after Drain() completes, so we can
	// safely close shard channels afterwards without racing a still-
	// running subscriber callback.
	natsClosed := make(chan struct{})

	opts := []nats.Option{
		nats.Name("trmm-nats-api"),
		nats.UserInfo("tacticalrmm", r.Key),
		nats.ReconnectWait(time.Second * 2),
		nats.RetryOnFailedConnect(true),
		nats.IgnoreAuthErrorAbort(),
		nats.MaxReconnects(-1),
		nats.ReconnectBufSize(-1),
		nats.DrainTimeout(natsDrainTimeout),
		nats.DisconnectErrHandler(func(nc *nats.Conn, nerr error) {
			logger.Debugln("NATS disconnected:", nerr)
			logger.Debugf("%+v\n", nc.Statistics)
		}),
		nats.ReconnectHandler(func(nc *nats.Conn) {
			logger.Debugln("NATS reconnected")
			logger.Debugf("%+v\n", nc.Statistics)
		}),
		nats.ErrorHandler(func(nc *nats.Conn, sub *nats.Subscription, nerr error) {
			logger.Errorln("NATS error:", nerr)
			logger.Errorf("%+v\n", sub)
		}),
		nats.ClosedHandler(func(_ *nats.Conn) {
			close(natsClosed)
		}),
	}
	nc, err := nats.Connect(r.NatsURL, opts...)
	if err != nil {
		logger.Fatalln(err)
	}

	if _, err := nc.Subscribe("*", func(msg *nats.Msg) {
		subj := subjectLabel(msg.Reply)
		messagesTotal.WithLabelValues(subj).Inc()
		if subj == "other" {
			return
		}

		var mh codec.MsgpackHandle
		mh.MapType = reflect.TypeOf(map[string]interface{}(nil))
		mh.RawToString = true
		dec := codec.NewDecoderBytes(msg.Data, &mh)

		switch msg.Reply {
		case "agent-hello":
			var p trmm.CheckInNats
			if err := dec.Decode(&p); err != nil {
				decodeErrorsTotal.WithLabelValues("agent-hello").Inc()
				logger.Warnf("decode agent-hello: %v", err)
				return
			}
			now := time.Now().UTC()
			logger.Debugln("Hello", p, now)
			enqueue(dbJob{name: "agent-hello", agentID: p.Agentid, fn: func(ctx context.Context, db *sqlx.DB) error {
				_, err := db.ExecContext(ctx, `
					UPDATE agents_agent
					SET last_seen=$1, version=$2
					WHERE agents_agent.agent_id=$3;`,
					now, p.Version, p.Agentid)
				return err
			}})

		case "agent-publicip":
			var p trmm.PublicIPNats
			if err := dec.Decode(&p); err != nil {
				decodeErrorsTotal.WithLabelValues("agent-publicip").Inc()
				logger.Warnf("decode agent-publicip: %v", err)
				return
			}
			logger.Debugln("Public IP", p)
			enqueue(dbJob{name: "agent-publicip", agentID: p.Agentid, fn: func(ctx context.Context, db *sqlx.DB) error {
				_, err := db.ExecContext(ctx, `
					UPDATE agents_agent SET public_ip=$1 WHERE agents_agent.agent_id=$2;`,
					p.PublicIP, p.Agentid)
				return err
			}})

		case "agent-agentinfo":
			var info trmm.AgentInfoNats
			if err := dec.Decode(&info); err != nil {
				decodeErrorsTotal.WithLabelValues("agent-agentinfo").Inc()
				logger.Warnf("decode agent-agentinfo: %v", err)
				return
			}
			logger.Debugln("Info", info)
			enqueue(dbJob{name: "agent-agentinfo", agentID: info.Agentid, fn: func(ctx context.Context, db *sqlx.DB) error {
				_, err := db.ExecContext(ctx, `
					UPDATE agents_agent
					SET hostname=$1, operating_system=$2,
					plat=$3, total_ram=$4, boot_time=$5, needs_reboot=$6, logged_in_username=$7, goarch=$8
					WHERE agents_agent.agent_id=$9;`,
					info.Hostname, info.OS, info.Platform, info.TotalRAM, info.BootTime, info.RebootNeeded, info.Username, info.GoArch, info.Agentid)
				return err
			}})

			if info.Username != "None" {
				logger.Debugln("Updating last logged in user:", info.Username)
				enqueue(dbJob{name: "agent-agentinfo/last_user", agentID: info.Agentid, fn: func(ctx context.Context, db *sqlx.DB) error {
					_, err := db.ExecContext(ctx,
						`UPDATE agents_agent SET last_logged_in_user=$1 WHERE agents_agent.agent_id=$2;`,
						info.Username, info.Agentid)
					return err
				}})
			}

			if openframeMode {
				var tz agentTimezone
				tzDec := codec.NewDecoderBytes(msg.Data, &mh)
				if tzDec.Decode(&tz) == nil && tz.Timezone != "" {
					logger.Debugln("Updating timezone agent=", tz.Agentid, "timezone=", tz.Timezone)
					enqueue(dbJob{name: "agent-agentinfo/timezone", agentID: tz.Agentid, fn: func(ctx context.Context, db *sqlx.DB) error {
						_, err := db.ExecContext(ctx, `
							UPDATE agents_agent SET time_zone=$1
							WHERE agents_agent.agent_id=$2;`, tz.Timezone, tz.Agentid)
						return err
					}})
				}
			}

		case "agent-disks":
			var p trmm.WinDisksNats
			if err := dec.Decode(&p); err != nil {
				decodeErrorsTotal.WithLabelValues("agent-disks").Inc()
				logger.Warnf("decode agent-disks: %v", err)
				return
			}
			logger.Debugln("Disks", p)
			b, err := json.Marshal(p.Disks)
			if err != nil {
				logger.Errorln(err)
				return
			}
			agentID := p.Agentid
			enqueue(dbJob{name: "agent-disks", agentID: agentID, fn: func(ctx context.Context, db *sqlx.DB) error {
				_, err := db.ExecContext(ctx, `
					UPDATE agents_agent SET disks=$1 WHERE agents_agent.agent_id=$2;`,
					b, agentID)
				return err
			}})

		case "agent-winsvc":
			var p trmm.WinSvcNats
			if err := dec.Decode(&p); err != nil {
				decodeErrorsTotal.WithLabelValues("agent-winsvc").Inc()
				logger.Warnf("decode agent-winsvc: %v", err)
				return
			}
			logger.Debugln("WinSvc", p)
			b, err := json.Marshal(p.WinSvcs)
			if err != nil {
				logger.Errorln(err)
				return
			}
			agentID := p.Agentid
			enqueue(dbJob{name: "agent-winsvc", agentID: agentID, fn: func(ctx context.Context, db *sqlx.DB) error {
				_, err := db.ExecContext(ctx, `
					UPDATE agents_agent SET services=$1 WHERE agents_agent.agent_id=$2;`,
					b, agentID)
				return err
			}})

		case "agent-wmi":
			var p trmm.WinWMINats
			if err := dec.Decode(&p); err != nil {
				decodeErrorsTotal.WithLabelValues("agent-wmi").Inc()
				logger.Warnf("decode agent-wmi: %v", err)
				return
			}
			logger.Debugln("WMI", p)
			b, err := json.Marshal(p.WMI)
			if err != nil {
				logger.Errorln(err)
				return
			}
			agentID := p.Agentid
			enqueue(dbJob{name: "agent-wmi", agentID: agentID, fn: func(ctx context.Context, db *sqlx.DB) error {
				_, err := db.ExecContext(ctx, `
					UPDATE agents_agent SET wmi_detail=$1 WHERE agents_agent.agent_id=$2;`,
					b, agentID)
				return err
			}})
		}
	}); err != nil {
		logger.Fatalf("subscribe *: %v", err)
	}

	// Reload: the backend publishes trmm.nats.reload after an agent delete
	// or token rotation. Purging the validator cache makes the change take
	// effect on the next agent connection instead of waiting for TTL.
	// Non-fatal: a failed subscribe is logged but does not take down the
	// service — the TTL expiry is the backstop.
	if _, err := nc.Subscribe(natsReloadSubject, func(msg *nats.Msg) {
		logger.Infof("Received reload signal on %s", msg.Subject)
		authCache.InvalidateAll()
		reloadsTotal.Inc()
		logger.Debug("invalidated validator cache")
	}); err != nil {
		logger.Errorf("subscribe %s: %v", natsReloadSubject, err)
	}

	if err := nc.Flush(); err != nil {
		logger.Errorf("nats flush: %v", err)
	}
	if err := nc.LastError(); err != nil {
		logger.Fatalln(err)
	}

	// Liveness: pod is healthy only while both NATS connections are up.
	// A dead connection means no check-ins land and no auth callouts are
	// served, and nats-api can't recover that on its own, so surfacing it
	// as a 503 lets kubelet restart the pod. IsConnected is false during
	// RECONNECTING, so brief blips will fail /healthz; the livenessProbe's
	// failureThreshold provides the grace window.
	SetHealthChecker(func() error {
		if !authNc.IsConnected() {
			return fmt.Errorf("auth nats: %s", authNc.Status())
		}
		if !nc.IsConnected() {
			return fmt.Errorf("main nats: %s", nc.Status())
		}
		return nil
	})

	sigCtx, sigStop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	<-sigCtx.Done()
	sigStop() // restore default handlers so a second signal force-quits
	logger.Info("shutdown: signal received, draining NATS")

	if err := nc.Drain(); err != nil {
		logger.Errorf("shutdown: drain nats: %v", err)
	}
	<-natsClosed
	logger.Info("shutdown: nats drained, closing shard queues")

	// Safe now: Drain has returned, no more subscriber callbacks run.
	for _, ch := range shards {
		close(ch)
	}

	workersDone := make(chan struct{})
	go func() {
		workers.Wait()
		close(workersDone)
	}()
	select {
	case <-workersDone:
		logger.Info("shutdown: workers finished cleanly")
	case <-time.After(workerShutdownGrace):
		logger.Warn("shutdown: worker grace expired, cancelling in-flight jobs")
		rootCancel()
		<-workersDone
	}

	authCleanup()
	logger.Info("shutdown: auth callout stopped")

	for i, sdb := range shardDBs {
		if err := sdb.Close(); err != nil {
			logger.Errorf("shutdown: close shard db %d: %v", i, err)
		}
	}
	if err := db.Close(); err != nil {
		logger.Errorf("shutdown: close main db: %v", err)
	}
	logger.Info("shutdown: done")
}
