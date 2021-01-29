package api

import (
	"time"

	"github.com/go-resty/resty/v2"
	nats "github.com/nats-io/nats.go"
	"github.com/ugorji/go/codec"
)

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
