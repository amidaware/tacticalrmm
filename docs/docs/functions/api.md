
# TacticalRMM-API

*Version added: v0.8.3*

[Tactical-API Documentation Repository](https://github.com/unplugged216/tacticalrmm-api-documentation)

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
curl https://api.example.com/clients -H "X-API-KEY: Y57BXCFAA9WBCXH0XTEL6R5KAK69CNCZ"
```

## Indices

* [Agents](#agents)

  * [Agent Checks](#1-agent-checks)
  * [Agent Details](#2-agent-details)
  * [Agent List](#3-agent-list)
  * [Agent Tasks](#4-agent-tasks)
  * [Agent Windows Updates](#5-agent-windows-updates)
  * [Run Script](#6-run-script)

* [Alerts](#alerts)

  * [Alert List](#1-alert-list)

* [Clients](#clients)

  * [Client Agents](#1-client-agents)
  * [Create Client](#2-create-client)
  * [List Clients](#3-list-clients)

* [Core](#core)

  * [Dashboard Info](#1-dashboard-info)
  * [List Custom Fields](#2-list-custom-fields)

* [Scripts](#scripts)

  * [List Scripts](#1-list-scripts)


--------


## Agents



### 1. Agent Checks



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/agents/:id/checks
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Authorization | Token SomeCrazyToeknGeneratedWithAuthenticate |  |



***URL variables:***

| Key | Value | Description |
| --- | ------|-------------|
| id |  | ID of the agent being requested |



### 2. Agent Details



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/agents/:id
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



***URL variables:***

| Key | Value | Description |
| --- | ------|-------------|
| id |  | ID of the agent being requested |



### 3. Agent List



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/agents
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



### 4. Agent Tasks



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/agents/:id/tasks
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



***URL variables:***

| Key | Value | Description |
| --- | ------|-------------|
| id |  | ID of the agent being requested |



### 5. Agent Windows Updates



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/winupdate/:id
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



***URL variables:***

| Key | Value | Description |
| --- | ------|-------------|
| id |  | ID of the agent being requested |



### 6. Run Script


- `pk`: ID of the endpoint 
- `timeout`: how long should the script be allowed to run before timing out. 
- `scriptPK`: ID of the script
- output: Should we `wait`, `forget`, or `email`?
- `emails`: An array of email addresses to send the output to
- `emailmode`: This is unknown at the moment


***Endpoint:***

```bash
Method: POST
Type: RAW
URL: https://api.example.com/agents/:id/runscript/
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



***URL variables:***

| Key | Value | Description |
| --- | ------|-------------|
| id |  | Agent ID |



***Body:***

```js        
{
    "output": "wait",
    "email": [],
    "emailMode": "default",
    "custom_field": null,
    "save_all_output": false,
    "script": 86,
    "args": [],
    "timeout": 90
}
```



## Alerts



### 1. Alert List



***Endpoint:***

```bash
Method: PATCH
Type: RAW
URL: https://api.example.com/alerts/
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



## Clients



### 1. Client Agents


Replace the value oh `clientPK` with that of the client ID you are looking up.


***Endpoint:***

```bash
Method: GET
Type: RAW
URL: https://api.example.com/agents/
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



***Query params:***

| Key | Value | Description |
| --- | ------|-------------|
| client |  | Client ID |



### 2. Create Client



***Endpoint:***

```bash
Method: POST
Type: RAW
URL: https://api.example.com/clients/
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



***Body:***

```js        
{
    "client": {
        "name": "Test 123"
    },
    "site": {
        "name": "Test 123 Site 1"
    },
    "custom_fields": [
        {
            "string_value": "Some custom field content",
            "field": 1
        }
    ]
}
```



### 3. List Clients



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/clients/
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



## Core



### 1. Dashboard Info



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/core/dashinfo/
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



### 2. List Custom Fields



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/core/customfields/
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



## Scripts
List, manipulate and execute scripts.



### 1. List Scripts



***Endpoint:***

```bash
Method: GET
Type: 
URL: https://api.example.com/scripts
```


***Headers:***

| Key | Value | Description |
| --- | ------|-------------|
| Content-Type | application/json |  |



***Available Variables:***

| Key | Value | Type |
| --- | ------|-------------|
| BASE_URI | https://api.example.com |  |
| API_KEY | SomeCrazyToeknGeneratedWithAuthenticate |  |



---
[Back to top](#tacticalrmm-api)
> Made with &#9829; by [thedevsaddam](https://github.com/thedevsaddam) | Generated at: 2021-11-14 13:24:18 by [docgen](https://github.com/thedevsaddam/docgen)
