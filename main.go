package main

// env CGO_ENABLED=0 go build -ldflags "-s -w" -o nats-api

import (
	"flag"
	"fmt"

	"github.com/sirupsen/logrus"
	"github.com/wh1te909/tacticalrmm/natsapi"
)

var (
	version = "3.0.2"
	log     = logrus.New()
)

func main() {
	ver := flag.Bool("version", false, "Prints version")
	cfg := flag.String("config", "", "Path to config file")
	logLevel := flag.String("log", "INFO", "The log level")
	flag.Parse()

	if *ver {
		fmt.Println(version)
		return
	}

	setupLogging(logLevel)

	api.Svc(log, *cfg)
}

func setupLogging(level *string) {
	ll, err := logrus.ParseLevel(*level)
	if err != nil {
		ll = logrus.InfoLevel
	}
	log.SetLevel(ll)
}
