-- Reference DDL for the 007 chat schema (conversations + messages).
-- This file is NOT applied anywhere — the Alembic migration at
-- database/migrations/versions/b2e9f1c4a5d6_initial_chat_schema.py is the single
-- source of truth for DDL (build decision #8). This is documentation/eyeball DDL.

CREATE TABLE conversations (
    id          uuid PRIMARY KEY,
    title       varchar(500),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id              uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role            varchar(16) NOT NULL,          -- user | assistant
    content         text NOT NULL,
    sources         jsonb,                          -- the 006 Source[] shape
    error           boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);