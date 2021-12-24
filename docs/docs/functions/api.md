## API Access

*Version added: v0.8.3*

API Keys can be created to access any of TacticalRMM's api endpoints, which will bypass 2fa authentication

When creating the key you'll need to choose a user, which will reflect what permissions the key has based on the user's role.

Navigate to Settings > Global Settings > API Keys to generate a key

Headers:

```json
{
    "Content-Type": "application/json", 
    "X-API-KEY": "J57BXCFDA2WBCXH0XTELBR5KAI69CNCZ"
}
```

Example curl request:

```bash
curl https://api.example.com/clients/clients/ -H "X-API-KEY: Y57BXCFAA9WBCXH0XTEL6R5KAK69CNCZ"
```

## Enable Swagger

This will let you add a browser interface to see how you can use the api better.

Open `/rmm/api/tacticalrmm/tacticalrmm/local_settings.py` and add 

```conf
SWAGGER_ENABLED = True
```

Then visit `https://api.example.com/api/schema/swagger-ui/` to see it in action.
