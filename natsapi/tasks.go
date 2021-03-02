package api

import (
	"sync"
	"time"

	"github.com/go-resty/resty/v2"
	nats "github.com/nats-io/nats.go"
	"github.com/ugorji/go/codec"
)

func monitorAgents(c *resty.Client, nc *nats.Conn) {
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

	tick := time.NewTicker(7 * time.Minute)
	for range tick.C {
		var wg sync.WaitGroup
		agentids, _ := c.R().SetResult(&AgentIDS{}).Get("/offline/agents/")
		ids := agentids.Result().(*AgentIDS).IDs
		wg.Add(len(ids))
		var resp string

		for _, id := range ids {
			go func(id string, nc *nats.Conn, wg *sync.WaitGroup, c *resty.Client) {
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
						p := map[string]string{"agentid": id}
						c.R().SetBody(p).Post("/logcrash/")
					}
				}
			}(id, nc, &wg, c)
		}
		wg.Wait()
	}
}

func getWMI(c *resty.Client, nc *nats.Conn) {
	var payload []byte
	var mh codec.MsgpackHandle
	mh.RawToString = true
	ret := codec.NewEncoderBytes(&payload, new(codec.MsgpackHandle))
	ret.Encode(map[string]string{"func": "wmi"})

	tick := time.NewTicker(18 * time.Minute)
	for range tick.C {
		agentids, _ := c.R().SetResult(&AgentIDS{}).Get("/online/agents/")
		ids := agentids.Result().(*AgentIDS).IDs
		chunks := makeChunks(ids, 40)

		for _, id := range chunks {
			for _, chunk := range id {
				nc.Publish(chunk, payload)
				time.Sleep(time.Duration(randRange(50, 400)) * time.Millisecond)
			}
			time.Sleep(15 * time.Second)
		}
	}
}
