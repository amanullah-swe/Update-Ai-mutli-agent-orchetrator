"""Import every model so ``Base.metadata`` is fully populated for Alembic."""

from app.models.conversation import Conversation, Message

__all__ = ["Conversation", "Message"]