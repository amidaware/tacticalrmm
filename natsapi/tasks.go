package api

import (
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

	tick := time.NewTicker(10 * time.Minute)
	for range tick.C {
		agentids, _ := c.R().SetResult(&AgentIDS{}).Get("/offline/")
		ids := agentids.Result().(*AgentIDS).IDs
		var resp string
		for _, id := range ids {
			out, err := nc.Request(id, payload, 2*time.Second)
			if err != nil {
				continue
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
		}
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
		agentids, _ := c.R().SetResult(&AgentIDS{}).Get("/wmi/")
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
