# AI Lab Command Center API Reference

## Authentication

All endpoints require `Authorization: Bearer <token>` unless in `PUBLIC_PATHS`.

```bash
# Get shared token (for demo/testing)
TOKEN=$(cat ~/.hermes/profiles/default/dashboard/.api-token)

# Use token
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/revenue/status
```

## Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (JSON) |
| `/metrics` | GET | Prometheus metrics |
| `/` | GET | Landing page |
| `/dashboard` | GET | Main dashboard |
| `/api/disk/rescue` | GET | Disk forecast (cached 30min) |

## Authenticated Endpoints

### Revenue & Money Paths
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/revenue/status` | GET | Revenue readiness score |
| `/api/revenue/export` | GET | Markdown revenue report |
| `/api/money/leads` | GET | Prospecting leads list |

### System & Monitoring
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system/snapshot` | GET | Full system state |
| `/api/system/predictions` | GET | Disk trend forecast |
| `/api/p50` | GET | Per-endpoint latency |
| `/api/trends` | GET | 7d/30d trend deltas |

### Workflows & Products
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflows/productize` | GET | Ready workflow packs |
| `/api/workflows/productize/{slug}/export` | GET | tar.gz pack download |

### Exports (all require auth)
| Endpoint | Method |
|----------|--------|
| `/api/revenue/export` | GET |
| `/api/revenue/export.json` | GET |
| `/api/predictions/export` | GET |
| `/api/predictions/export.json` | GET |
| `/api/agent/improvements/export` | GET |
| `/api/disk/rescue/export` | GET |

## WebSocket

Connect to `/ws` for real-time updates. Broadcasts every 15s:

```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## Error Responses

All errors follow: `{"detail": "...", "error": "ERROR_CODE"}`

| Code | Status | Meaning |
|------|--------|---------|
| `UNAUTHORIZED` | 401 | Missing/invalid token |
| `INVALID_AUTH` | 401 | Token verification failed |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |