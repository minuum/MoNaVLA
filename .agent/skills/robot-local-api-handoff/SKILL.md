---
name: robot-local-api-handoff
description: Define or verify the minimal local FastAPI contract needed for a robot-side server to work with `vla-inference-gradio` and existing MoNaVLA API clients. Use when preparing a robot-local inference server, handoff note, or compatibility checklist.
---

# Robot Local API Handoff

Use this skill when the goal is not to deploy Billy's server, but to make a
robot-local server compatible with the existing Gradio dashboard and API
clients.

## What matters

- Keep the server on the robot side, usually `http://localhost:8000`
- Match the existing `/predict` contract
- Keep `action` as exactly 2 values: `[linear_x, linear_y]`
- Accept `instruction` for compatibility even if the local model ignores text
- Support `X-API-Key`

## Required endpoints

- `POST /predict`
- `POST /reset`
- `GET /health`

## `/predict` request

```json
{
  "image": "<base64 encoded image>",
  "instruction": "Navigate toward the gray basket until it gets closer"
}
```

Required headers:

```http
Content-Type: application/json
X-API-Key: <VLA_API_KEY>
```

## `/predict` response

Minimum required response:

```json
{
  "action": [1.15, 0.0],
  "latency_ms": 87.3
}
```

Recommended full response:

```json
{
  "action": [1.15, 0.0],
  "latency_ms": 87.3,
  "model_name": "exp19_proxy_local",
  "strategy": "proxy_mlp",
  "source": "inferred",
  "buffer_status": {}
}
```

## `/reset` response

```json
{
  "status": "success",
  "message": "history reset"
}
```

## `/health` response

Keep it simple. At minimum:

```json
{
  "status": "healthy",
  "model_loaded": true
}
```

## Hard constraints

- Do not change `action` to 3D in the main response field
- Do not rename `latency_ms`
- Do not remove `instruction` from the request schema
- Extra metadata is fine, but the old keys must keep working

## Fast handoff template

When asked to prepare a robot-side handoff, provide:

1. Base URL: `http://localhost:8000`
2. Required headers
3. `/predict` request JSON
4. `/predict` response JSON
5. `/reset` response JSON
6. One-line warning: `action` must stay `[linear_x, linear_y]`
