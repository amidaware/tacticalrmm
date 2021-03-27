package api

import (
	"encoding/json"
	"io/ioutil"
	"log"
	"math/rand"
	"sync"
	"time"

	nats "github.com/nats-io/nats.go"
	"github.com/ugorji/go/codec"
)

type JsonFile struct {
	Agents  []string `json:"agents"`
	Key     string   `json:"key"`
	NatsURL string   `json:"natsurl"`
}

type Recovery struct {
	Func string            `json:"func"`
	Data map[string]string `json:"payload"`
}

func setupNatsOptions(key string) []nats.Option {
	opts := []nats.Option{
		nats.Name("TacticalRMM"),
		nats.UserInfo("tacticalrmm", key),
		nats.ReconnectWait(time.Second * 2),
		nats.RetryOnFailedConnect(true),
		nats.MaxReconnects(3),
		nats.ReconnectBufSize(-1),
	}
	return opts
}

func MonitorAgents(file string) {
	var result JsonFile
	var payload, recPayload []byte
	var mh codec.MsgpackHandle
	mh.RawToString = true
	ret := codec.NewEncoderBytes(&payload, new(codec.MsgpackHandle))
	ret.Encode(map[string]string{"func": "ping"})

	rec := codec.NewEncoderBytes(&recPayload, new(codec.MsgpackHandle))
	rec.Encode(Recovery{
		Func: "recover",
		Data: map[string]string{"mode": "tacagent"},
	})

	jret, _ := ioutil.ReadFile(file)
	err := json.Unmarshal(jret, &result)
	if err != nil {
		log.Fatalln(err)
	}

	opts := setupNatsOptions(result.Key)

	nc, err := nats.Connect(result.NatsURL, opts...)
	if err != nil {
		log.Fatalln(err)
	}
	defer nc.Close()

	var wg sync.WaitGroup
	var resp string
	wg.Add(len(result.Agents))

	for _, id := range result.Agents {
		go func(id string, nc *nats.Conn, wg *sync.WaitGroup) {
			defer wg.Done()
			out, err := nc.Request(id, payload, 1*time.Second)
			if err != nil {
				return
			}
			dec := codec.NewDecoderBytes(out.Data, &mh)
			if err := dec.Decode(&resp); err == nil {
				// if the agent is respoding to pong from the rpc service but is not showing as online (handled by tacticalagent service)
				// then tacticalagent service is hung. forcefully restart it
				if resp == "pong" {
					nc.Publish(id, recPayload)
				}
			}
		}(id, nc, &wg)
	}
	wg.Wait()
}

func GetWMI(file string) {
	var result JsonFile
	var payload []byte
	var mh codec.MsgpackHandle
	mh.RawToString = true
	ret := codec.NewEncoderBytes(&payload, new(codec.MsgpackHandle))
	ret.Encode(map[string]string{"func": "wmi"})

	jret, _ := ioutil.ReadFile(file)
	err := json.Unmarshal(jret, &result)
	if err != nil {
		log.Fatalln(err)
	}

	opts := setupNatsOptions(result.Key)

	nc, err := nats.Connect(result.NatsURL, opts...)
	if err != nil {
		log.Fatalln(err)
	}
	defer nc.Close()

	var wg sync.WaitGroup
	wg.Add(len(result.Agents))

	for _, id := range result.Agents {
		go func(id string, nc *nats.Conn, wg *sync.WaitGroup) {
			defer wg.Done()
			time.Sleep(time.Duration(randRange(0, 20)) * time.Second)
			nc.Publish(id, payload)
		}(id, nc, &wg)
	}
	wg.Wait()
}

func randRange(min, max int) int {
	rand.Seed(time.Now().UnixNano())
	return rand.Intn(max-min) + min
}
