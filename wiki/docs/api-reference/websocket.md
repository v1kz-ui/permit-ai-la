---
sidebar_position: 8
title: WebSocket
---

# WebSocket API

Real-time project updates via WebSocket connections.

## Connection

```
ws://localhost:8000/api/v1/ws/{project_id}
```

Requires authentication token as query parameter or in the initial handshake.

## Event Types

| Event | Trigger | Payload |
|-------|---------|---------|
| `clearance_changed` | Clearance status updated | `{clearance_id, project_id, department, old_status, new_status}` |
| `permit_changed` | Project status updated | `{project_id, old_status, new_status}` |
| `inspection_scheduled` | New inspection created | `{inspection_id, project_id, type, scheduled_date}` |

## Architecture

```
Status Change → Redis Pub/Sub → WebSocket Server → Connected Clients
```

Events are published to Redis channels and broadcast to all WebSocket clients subscribed to the relevant project. This allows horizontal scaling of the API server while maintaining real-time updates across all instances.
