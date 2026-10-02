"""Chats feature slice.

Only model/schema/repository symbols are exported here.
Router and WebSocket handler are imported directly in main.py to avoid
circular import chains through the orchestrator package.
"""

from app.features.chats.models import Conversation, Message
from app.features.chats.repository import (
    append_message,
    create_chat,
    delete_chat,
    get_chat,
    get_chat_history,
    list_chats,
    rename_chat,
)
from app.features.chats.schemas import (
    ChatCreate,
    ChatDetail,
    ChatListResponse,
    ChatOut,
    ChatRename,
    ChatSummary,
    ErrorFrame,
    MessageEndFrame,
    MessageFrame,
    MessageOut,
    MessageStartFrame,
    ReadyFrame,
    Source,
    SourcesFrame,
    TokenFrame,
    UserMessageFrame,
)

__all__ = [
    "ChatCreate",
    "ChatDetail",
    "ChatListResponse",
    "ChatOut",
    "ChatRename",
    "ChatSummary",
    "Conversation",
    "ErrorFrame",
    "Message",
    "MessageEndFrame",
    "MessageFrame",
    "MessageOut",
    "MessageStartFrame",
    "ReadyFrame",
    "Source",
    "SourcesFrame",
    "TokenFrame",
    "UserMessageFrame",
    "append_message",
    "create_chat",
    "delete_chat",
    "get_chat",
    "get_chat_history",
    "list_chats",
    "rename_chat",
]
