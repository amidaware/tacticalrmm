# Scripts V2 API

Base URL: `/v2/scripts/`  
Auth: All endpoints require `Authorization: Token <knox-token>` header.

---

## Endpoints

| Method | URL | Description |
|---|---|---|
| `GET` | `/v2/scripts/` | List scripts with cursor pagination, search, filtering |
| `GET` | `/v2/scripts/filters/` | Get available filter values for specified fields |

---

## List Scripts

```
GET /v2/scripts/
```

### Response `200 OK`

```json
{
  "next": "cD1bIkNvbW11bml0eSIsIDQyXQ==",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Get Disk Usage",
      "description": "Returns disk usage for all drives",
      "script_type": "userdefined",
      "shell": "powershell",
      "args": [],
      "category": "Windows",
      "favorite": false,
      "default_timeout": 90,
      "syntax": null,
      "filename": null,
      "hidden": false,
      "supported_platforms": ["windows"],
      "run_as_user": false,
      "env_vars": []
    }
  ]
}
```

> `next` and `previous` are cursor strings (base64). `null` means no more pages.

---

## Pagination

Cursor-based pagination. Default ordering: `category`, `id`.

| Parameter | Type | Default | Max | Description |
|---|---|---|---|---|
| `cursor` | string | — | — | Cursor from previous response |
| `page_size` | int | 100 | 1000 | Results per page |

```
GET /v2/scripts/?cursor=cD1bIkNvbW11bml0eSIsIDQyXQ==&page_size=25
```

### Infinity scroll pattern

```javascript
let cursor = null;

async function loadMore() {
  const url = cursor
    ? `/v2/scripts/?cursor=${cursor}`
    : `/v2/scripts/`;

  const res = await fetch(url, {
    headers: { "Authorization": `Token ${token}` }
  });
  const data = await res.json();

  appendToList(data.results);
  cursor = data.next; // null when last page
}
```

---

## Search

Searches by `name` (case-insensitive `ILIKE`).

| Parameter | Description |
|---|---|
| `search` | Text to search in script name |

```
GET /v2/scripts/?search=backup
```

---

## Filtering

| Parameter | Type | Description |
|---|---|---|
| `script_type` | string | `userdefined` or `builtin` |
| `shell` | string | `powershell`, `cmd`, `python`, `bash`, `nushell` |
| `category` | string | Exact match on category name |
| `favorite` | bool | `true` or `false` |
| `hidden` | bool | `true` or `false` |
| `run_as_user` | bool | `true` or `false` |
| `supported_platforms` | string (comma-separated) | Filter by supported platform — OR logic |

### `supported_platforms` values

| Value | Platform |
|---|---|
| `windows` | Windows |
| `linux` | Linux |
| `darwin` | macOS |

```
GET /v2/scripts/?supported_platforms=windows
GET /v2/scripts/?supported_platforms=linux,darwin
GET /v2/scripts/?shell=powershell&hidden=false
GET /v2/scripts/?script_type=userdefined&favorite=true
GET /v2/scripts/?category=Windows&supported_platforms=windows,linux
```

---

## Combined Example

```
GET /v2/scripts/?search=disk&shell=powershell&hidden=false&page_size=25
GET /v2/scripts/?search=disk&shell=powershell&hidden=false&page_size=25&cursor=cD1bIkNvbW11bml0eSIsIDQyXQ==
```

---

---

## Available Filters

```
GET /v2/scripts/filters/?fields=category
GET /v2/scripts/filters/?fields=category,shell,script_type,supported_platforms
```

### Query parameters

| Parameter | Required | Description |
|---|---|---|
| `fields` | yes | Comma-separated list of fields. Allowed: `category`, `shell`, `script_type`, `supported_platforms` |

### Response `200 OK`

```json
{
  "category": ["Community", "Linux", "Utilities", "Windows"],
  "shell": ["bash", "powershell", "python"],
  "script_type": ["builtin", "userdefined"],
  "supported_platforms": ["darwin", "linux", "windows"]
}
```

### With filters applied (faceted search)

All filter parameters from the list endpoint are supported. The returned values reflect only what's available within the filtered dataset.

```
# Which categories have PowerShell scripts?
GET /v2/scripts/filters/?fields=category&shell=powershell

# Which platforms are available for Windows category scripts?
GET /v2/scripts/filters/?fields=supported_platforms&category=Windows

# Combined
GET /v2/scripts/filters/?fields=category,supported_platforms&shell=python&hidden=false
```

### Response `400 Bad Request`

```json
{
  "fields": "This field is required. Allowed values: ['category', 'script_type', 'shell', 'supported_platforms']"
}
```

---

## Error Responses

### 401 Unauthorized
```json
{"detail": "Authentication credentials were not provided."}
```

### 404 Not Found
```json
{"detail": "Not found."}
```
