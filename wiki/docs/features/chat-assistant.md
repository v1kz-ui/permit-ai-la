---
sidebar_position: 4
title: AI Chat Assistant
---

# AI Chat Assistant

A conversational interface powered by Claude AI with Retrieval-Augmented Generation (RAG).

**File:** `backend/app/services/chat_service.py`

## How It Works

```
User Message → Sanitize → RAG Retrieval → Build Prompt → Claude API → Response
                              │
                              ▼
                    Knowledge Base
                 (regulatory documents)
```

1. **Input sanitization** -- Filters prompt injection patterns from user input
2. **RAG retrieval** -- Queries the knowledge base for the top 3 most relevant regulatory documents
3. **Context building** -- Constructs a system prompt with:
   - Base guidance (empathetic, grounded in LA code)
   - Project-specific context (address, pathway, status, overlays, clearance statuses)
   - Retrieved regulatory documents
4. **Claude API call** -- Sends conversation history + context to Claude Sonnet
5. **Response** -- Returns AI response with source document citations

## Rate Limiting

- **20 messages per hour** per user
- Redis-backed sliding window
- Fail-open: if Redis is unavailable, rate limiting is skipped
- Remaining count shown in the chat UI

## Safety Features

### Prompt Injection Filtering
User input is scanned for common jailbreak patterns before processing.

### System Prompt Guidance
The AI is instructed to:
- Be empathetic (homeowners lost their homes to fire)
- Ground responses in LA building code and executive orders
- Recommend contacting LADBS or an attorney when uncertain
- Never provide legal advice
- Use bullet points for clarity
- Reference the user's specific project context

### Max Input Length
Messages are capped at 4,000 characters.

## Dashboard UI

The chat page (`/chat`) includes:
- **Project selector** sidebar with search
- **Message bubbles** (user in indigo, assistant in gray)
- **Typing indicator** with animated dots
- **Source citations** expandable under AI responses
- **Suggested questions** grid when no messages yet
- **Rate limit indicator** showing remaining questions
- **Disclaimer banner**: "AI responses are for guidance only -- Not legal advice"

## Model

Uses `claude-sonnet-4-6-20250514` with max 1024 tokens per response.
