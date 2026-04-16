package main

// env CGO_ENABLED=0 go build -ldflags "-s -w" -o nats-api

import (
	"flag"
	"fmt"
	"os"
	"runtime/debug"
	"strings"

	"github.com/amidaware/tacticalrmm/natsapi"
	"github.com/sirupsen/logrus"
)

var (
	version = "3.5.6"
	log     = logrus.New()
)

func main() {
	ver := flag.Bool("version", false, "Prints version")
	cfg := flag.String("config", "", "Path to config file")
	logLevel := flag.String("log", "INFO", "The log level")
	// bootstrap runs one-shot: generate nats-rmm.conf from the database,
	// write it to -out (or $NATS_CONFIG), and exit. Used by the tactical-nats
	// container's entrypoint before supervisord starts nats-server, so that
	// nats-server has a valid config on first boot without depending on the
	// tactical-backend PVC or a Redis-based transport.
	bootstrap := flag.Bool("bootstrap", false, "Generate nats-rmm.conf from the database and exit")
	out := flag.String("out", "", "Output path for bootstrap mode (defaults to $NATS_CONFIG or /opt/tactical/api/nats-rmm.conf)")
	authCallout := flag.Bool("auth-callout", false, "Enable NATS auth callout mode (validate credentials via Postgres instead of static config)")
	flag.Parse()

	if *ver {

		fmt.Println(version)
		bi, ok := debug.ReadBuildInfo()
		if ok {
			fmt.Println(bi.String())
		}
		return
	}

	setupLogging(logLevel)

	if *bootstrap {
		outPath := *out
		if outPath == "" {
			if env := os.Getenv("NATS_CONFIG"); env != "" {
				outPath = env
			} else {
				outPath = "/opt/tactical/api/nats-rmm.conf"
			}
		}
		natsapi.Bootstrap(log, *cfg, outPath)
		return
	}

	authCalloutEnabled := *authCallout || strings.EqualFold(os.Getenv("AUTH_CALLOUT"), "true")
	natsapi.Svc(log, *cfg, authCalloutEnabled)
}

func setupLogging(level *string) {
	ll, err := logrus.ParseLevel(*level)
	if err != nil {
		ll = logrus.InfoLevel
	}
	log.SetLevel(ll)
}
