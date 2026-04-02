---
sidebar_position: 10
title: Notifications
---

# Notifications

Multi-channel notification system for keeping homeowners and staff informed about permit progress.

## Channels

| Channel | Technology | Use Case |
|---------|-----------|----------|
| Push | Firebase Cloud Messaging | Real-time mobile alerts |
| SMS | Twilio | Critical status changes |
| Email | SMTP (Mailhog in dev) | Detailed updates and summaries |

## Notification Types

| Type | Trigger |
|------|---------|
| `clearance_status_changed` | A clearance moves to a new status |
| `inspection_scheduled` | New inspection date set |
| `inspection_result` | Inspection pass/fail result |
| `document_required` | Additional document needed |
| `permit_status_changed` | Overall permit status change |
| `bottleneck_detected` | ML model flags a delay risk |

## User Preferences

Users can configure which channels they receive for each notification type via:
```
GET  /api/v1/users/me/notification-preferences
PUT  /api/v1/users/me/notification-preferences
```

## Real-Time Updates

WebSocket connections (`/api/v1/ws/{project_id}`) provide instant updates:
- `clearance_changed` events
- `permit_changed` events
- `inspection_scheduled` events

Events are broadcast via Redis pub/sub to all connected clients watching a project.

## Delivery Tracking

Each notification record tracks:
- `delivery_status`: pending, sent, delivered, failed
- `delivered_at`: timestamp of successful delivery
- `error_message`: failure reason if applicable
