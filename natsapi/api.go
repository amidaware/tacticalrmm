package api

import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"

	"strings"
	"sync"
	"time"

	"github.com/go-resty/resty/v2"
	nats "github.com/nats-io/nats.go"
)

var rClient = resty.New()

func getAPI(apihost, natshost string) (string, string, error) {
	if apihost != "" && natshost != "" {
		return apihost, natshost, nil
	}

	f, err := os.Open(`/etc/nginx/sites-available/rmm.conf`)
	if err != nil {
		return "", "", err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		if strings.Contains(scanner.Text(), "server_name") && !strings.Contains(scanner.Text(), "301") {
			r := strings.NewReplacer("server_name", "", ";", "")
			s := strings.ReplaceAll(r.Replace(scanner.Text()), " ", "")
			return fmt.Sprintf("https://%s/natsapi", s), fmt.Sprintf("tls://%s:4222", s), nil
		}
	}
	return "", "", errors.New("unable to parse api from nginx conf")
}

func Listen(apihost, natshost, version string, debug bool) {
	api, natsurl, err := getAPI(apihost, natshost)
	if err != nil {
		log.Fatalln(err)
	}

	log.Printf("Tactical Nats API Version %s\n", version)
	log.Println("Api base url: ", api)
	log.Println("Nats connection url: ", natsurl)

	rClient.SetHostURL(api)
	rClient.SetTimeout(10 * time.Second)
	natsinfo, err := rClient.R().SetResult(&NatsInfo{}).Get("/natsinfo/")
	if err != nil {
		log.Fatalln(err)
	}
	if natsinfo.IsError() {
		log.Fatalln(natsinfo.String())
	}

	opts := []nats.Option{
		nats.Name("TacticalRMM"),
		nats.UserInfo(natsinfo.Result().(*NatsInfo).User,
			natsinfo.Result().(*NatsInfo).Password),
		nats.ReconnectWait(time.Second * 5),
		nats.RetryOnFailedConnect(true),
		nats.MaxReconnects(-1),
		nats.ReconnectBufSize(-1),
	}

	nc, err := nats.Connect(natsurl, opts...)
	if err != nil {
		log.Fatalln(err)
	}

	var wg sync.WaitGroup
	wg.Add(1)
	go getWMI(rClient, nc)
	go monitorAgents(rClient, nc)
	wg.Wait()
}
