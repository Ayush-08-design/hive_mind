# hive mind

**Multi-user collaborative agentic chat: many people and one or more AI agents working together in a single shared session. Built in pure Python.**

> 🚧 Status: in active development.

## Overview

Think "Google Docs, but for agentic systems." Multiple users join the same chat session in real time, see each other's messages, and collaborate with a shared AI agent that can reason and call tools on the group's behalf.

## Features

- **Shared sessions:** many users in one live conversation over WebSockets
- **Event-sourced log:** every message, token, and tool call is an ordered, replayable event
- **Raw agent loop:** hand-written, no orchestration framework
- **Turn serialization:** a per-session queue ensures one agent run at a time
- **Attribution:** the agent knows who said what
- **Roles and approvals:** owner/editor/viewer roles, with approval for risky tool calls
- **Reconnect and replay:** clients resume from their last seen event
- **Scalable:** Redis pub/sub to broadcast across multiple server workers
- **Pluggable LLMs and tools:** provider-agnostic interface and a tool registry

## Architecture

```
Users ──WebSocket──▶ FastAPI ──▶ Event store (DB)
                        │              │
                        ▼              ▼
                  Session queue ──▶ Agent loop ──▶ LLM + Tools
                        │
                        ▼
              Broker (Redis pub/sub) ──▶ broadcast to all users in session
```

## Project structure

```
hive_mind/
├── app/
│   ├── api/            # REST routes + WebSocket endpoint
│   ├── core/           # events, session manager, broker, presence
│   ├── agent/          # agent loop, context builder, llm/, tools/
│   ├── db/             # models and repository layer
│   ├── services/       # auth, permissions, memory
│   └── observability/  # logging and tracing
├── frontend/
├── tests/
├── docker-compose.yml
└── pyproject.toml
```

## Tech stack

Python 3.12+, FastAPI, asyncio, SQLAlchemy (SQLite/Postgres), Redis, Pydantic v2.

## Roadmap

- [ ] Event model and persistent store
- [ ] WebSocket broadcast (in-memory broker)
- [ ] Agent loop with streamed tokens
- [ ] Auth, roles, and presence
- [ ] Tool approvals, cancel, reconnect and replay
- [ ] Redis broker for multi-worker scaling
- [ ] Tests with a fake LLM, plus tracing
