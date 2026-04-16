package natsapi

import (
	"errors"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/sirupsen/logrus"
)

// Prometheus metrics for nats-api. Intentionally narrow: enough to answer
// "is the worker pool healthy, are we dropping jobs, is Postgres slow, are
// reloads succeeding?" without trying to be a full observability suite.
//
// Label cardinality is bounded on purpose — "subject" is restricted to the
// set of known handlers plus "other", and "handler" comes from the fixed
// dbJob.name values set inside svc.go. There are no per-agent labels.
var (
	messagesTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "nats_api_messages_total",
		Help: "NATS messages received, labeled by handler subject.",
	}, []string{"subject"})

	decodeErrorsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "nats_api_decode_errors_total",
		Help: "Messages that failed msgpack decode, labeled by handler subject.",
	}, []string{"subject"})

	jobsDroppedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "nats_api_jobs_dropped_total",
		Help: "Jobs dropped because the db worker queue was full, labeled by handler.",
	}, []string{"handler"})

	jobsProcessedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "nats_api_jobs_processed_total",
		Help: "Jobs processed by a db worker, labeled by handler and result (ok|error|panic).",
	}, []string{"handler", "result"})

	// shardQueueDepth is per-shard so a single hot shard — the signature
	// of one noisy agent being correctly isolated — is visible as a spike
	// on one series while the others stay flat. Label cardinality is
	// bounded at dbShards.
	shardQueueDepth = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "nats_api_shard_queue_depth",
		Help: "Current length of each sharded db worker queue, labeled by shard index.",
	}, []string{"shard"})

	queueCapacity = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "nats_api_queue_capacity",
		Help: "Total capacity of the db worker queue across all shards.",
	})

	dbDurationSeconds = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "nats_api_db_duration_seconds",
		Help: "Duration of database writes, labeled by handler.",
		// 1ms .. ~2s (12 buckets, x2 each). A db write taking >2s is
		// already a firm alert threshold, so the +Inf bucket is the
		// right place for the tail.
		Buckets: prometheus.ExponentialBuckets(0.001, 2, 12),
	}, []string{"handler"})

	reloadsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "nats_api_reloads_total",
		Help: "nats-rmm.conf reload outcomes (ok|config_only|signal_error|generate_error).",
	}, []string{"result"})

	reconcileTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "nats_api_reconcile_total",
		Help: "Config reconciliation outcomes.",
	}, []string{"result"})

	reconcileDurationSeconds = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "nats_api_reconcile_duration_seconds",
		Help:    "Wall-clock time of one reconciliation tick (hash query + optional regen + signal).",
		Buckets: prometheus.ExponentialBuckets(0.001, 2, 12),
	})
)

// knownSubjectList is the allow-list of handler subjects we attach as
// labels. Anything else is counted as "other" to keep label cardinality
// bounded. Kept as a slice (not a map) so initMetrics can iterate it and
// pre-register label combinations at startup.
var knownSubjectList = []string{
	"agent-hello",
	"agent-publicip",
	"agent-agentinfo",
	"agent-disks",
	"agent-winsvc",
	"agent-wmi",
}

// knownHandlers is every dbJob.name value that appears in svc.go. It is a
// superset of knownSubjectList because agent-agentinfo fans out to two
// auxiliary jobs (last_user and timezone) that don't map 1:1 to a subject.
var knownHandlers = []string{
	"agent-hello",
	"agent-publicip",
	"agent-agentinfo",
	"agent-agentinfo/last_user",
	"agent-agentinfo/timezone",
	"agent-disks",
	"agent-winsvc",
	"agent-wmi",
}

var knownSubjects = func() map[string]struct{} {
	m := make(map[string]struct{}, len(knownSubjectList))
	for _, s := range knownSubjectList {
		m[s] = struct{}{}
	}
	return m
}()

// shardLabels is a pre-computed slice of the string form of each shard
// index ("0", "1", ..., strconv.Itoa(dbShards-1)). Caching them avoids an
// allocation on every sampler tick and every per-shard metric write.
var shardLabels = func() []string {
	l := make([]string, dbShards)
	for i := range l {
		l[i] = strconv.Itoa(i)
	}
	return l
}()

func subjectLabel(s string) string {
	if _, ok := knownSubjects[s]; ok {
		return s
	}
	return "other"
}

// initMetrics pre-registers every known label combination against zero so
// that dashboards and `rate()` queries see a flat line instead of a gap
// before the first message arrives. Counters created via promauto only
// materialize a given label tuple on first Inc(), so without this the
// series are invisible until traffic hits them.
func initMetrics() {
	for _, s := range append(knownSubjectList, "other") {
		messagesTotal.WithLabelValues(s)
		decodeErrorsTotal.WithLabelValues(s)
	}
	for _, h := range knownHandlers {
		jobsDroppedTotal.WithLabelValues(h)
		for _, r := range []string{"ok", "error", "panic"} {
			jobsProcessedTotal.WithLabelValues(h, r)
		}
	}
	for _, r := range []string{"ok", "config_only", "signal_error", "generate_error"} {
		reloadsTotal.WithLabelValues(r)
	}
	for _, r := range []string{"in_sync", "drift_detected", "ok", "query_error", "regen_error", "signal_error"} {
		reconcileTotal.WithLabelValues(r)
	}
	for _, s := range shardLabels {
		shardQueueDepth.WithLabelValues(s)
	}
}

// StartMetricsServer starts the Prometheus /metrics endpoint on the address
// in METRICS_LISTEN (e.g. ":9189"). Returns true if the listener was
// started, false if METRICS_LISTEN was unset. Errors from the HTTP server
// are logged but non-fatal — metrics must never take down the check-in
// path. Callers should gate the queue-depth sampler on the return value so
// we don't waste a ticker when the endpoint is disabled.
func StartMetricsServer(logger *logrus.Logger) bool {
	addr := os.Getenv("METRICS_LISTEN")
	if addr == "" {
		logger.Debugln("METRICS_LISTEN not set, metrics endpoint disabled")
		return false
	}

	initMetrics()

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	srv := &http.Server{
		Addr:              addr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		// Route stdlib http errors (TLS handshake failures, keepalive
		// parse errors, etc.) through logrus so they land in the same
		// stream as the rest of nats-api.
		ErrorLog: log.New(logger.WriterLevel(logrus.WarnLevel), "metrics: ", 0),
	}
	go func() {
		logger.Infof("Metrics endpoint listening on %s/metrics", addr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Errorf("metrics server: %v", err)
		}
	}()
	return true
}
