# Code Signing

*Version added: Tactical RMM v0.6.0 / Agent v1.5.0*

Tactical RMM agents are now [code signed](https://comodosslstore.com/resources/what-is-microsoft-authenticode-code-signing-certificate/)!

To get access to code signed agents, you must be a [Github Sponsor](https://github.com/sponsors/wh1te909) with a minumum monthly donation of $50.00

Once you have become a sponsor, please email **support@amidaware.com** with your Github username (and Discord username if you're on our [Discord](https://discord.gg/upGTkWp))

Please allow up to 24 hours for a response

You will then be sent a code signing auth token, which you should enter into Tactical's web UI from *Settings > Code Signing*


## How does it work?

Everytime you generate an agent or an agent does a self-update, your self-hosted instance sends a request to Tactical's code signing servers with your auth token.

If the token is valid, the server sends you back a code signed agent. If not, it sends you back the un-signed agent.

If you think your auth token has been compromised or stolen then please email support or contact wh1te909 on discord to get a new token / invalidate the old one.