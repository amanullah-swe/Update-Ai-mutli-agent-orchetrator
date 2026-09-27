# ADR-010 — Streaming transport: SSE (text/event-stream) for /api/chat

- **Status:** Superseded by [ADR-011](./011-chat-transport-websocket.md)
- **Date:** 2026-09-27
- **Related:** CLAUDE.md "Build decisions" #10

> **Superseded 2026-09-27.** 007 was rescoped to a WebSocket chat transport
> (ADR-011). This record is kept for history. The chat event vocabulary it defined
> (`message_start → token → sources → message_end`, in-band `error`) was carried over,
> only the transport and framing changed.

## Context

The chat API must stream. The spec says "SSE where appropriate" and the frontend
(006) already parses `text/event-stream`. `EventSource` cannot POST a request body,
and the chat contract is `POST /api/chat` — so the frontend uses `fetch` +
`ReadableStream`. The backend must produce a matching stream.

Options: (a) SSE over POST (`text/event-stream`); (b) WebSocket; (c) chunked JSON.

## Decision

Standardize on **SSE (`text/event-stream`) over `POST /api/chat`**, framed as the
frontend parses it: each event is `event: <type>\ndata: <payload>\n\n` (blank-line
terminated), and the stream ends with `event: done\ndata: [DONE]`. The event set is
`message_start → token* → sources → message_end → done` (error is in-band). The
backend emits it via Starlette `StreamingResponse`.

## Consequences

- One transport spans backend and frontend with no extra dependency.
- Token deltas must never contain a blank line (would break framing) — mock
  provider tokenizes around paragraph breaks; the `format_sse` helper asserts this.
- WebSockets (bidirectional / mid-stream signaling) are out of scope for chat;
  revisit only if a need arises.