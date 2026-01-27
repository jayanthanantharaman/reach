"""
State Management for REACH.


This module provides session and conversation state management
for the multi-agent content creation system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Message:
    """Represents a single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """
    Manages the state of a single conversation.
    
    Attributes:
        conversation_id: Unique identifier for the conversation
        messages: List of messages in the conversation
        context: Shared context data across the conversation
        current_agent: Currently active agent
        generated_content: Content generated during the conversation
    """

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[Message] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    current_agent: Optional[str] = None
    generated_content: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add a message to the conversation."""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_history(self, limit: Optional[int] = None) -> list[dict[str, str]]:
        """Get conversation history as list of dicts."""
        messages = self.messages[-limit:] if limit else self.messages
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def update_context(self, key: str, value: Any) -> None:
        """Update context data."""
        self.context[key] = value
        self.updated_at = datetime.now()

    def store_content(self, content_type: str, content: Any) -> None:
        """Store generated content."""
        if content_type not in self.generated_content:
            self.generated_content[content_type] = []
        self.generated_content[content_type].append({
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now()

    def get_latest_content(self, content_type: str) -> Optional[Any]:
        """Get the latest generated content of a type."""
        if content_type in self.generated_content:
            items = self.generated_content[content_type]
            if items:
                return items[-1]["content"]
        return None

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in self.messages
            ],
            "context": self.context,
            "current_agent": self.current_agent,
            "generated_content": self.generated_content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationState":
        """Create state from dictionary."""
        state = cls(
            conversation_id=data.get("conversation_id", str(uuid.uuid4())),
            context=data.get("context", {}),
            current_agent=data.get("current_agent"),
            generated_content=data.get("generated_content", {}),
        )

        # Restore messages
        for msg_data in data.get("messages", []):
            state.messages.append(Message(
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data.get("timestamp", datetime.now().isoformat())),
                metadata=msg_data.get("metadata", {}),
            ))

        return state


class SessionManager:
    """
    Manages multiple conversation sessions.
    
    This class provides:
    - Session creation and retrieval
    - Session persistence (in-memory)
    - Session cleanup
    """

    def __init__(self):
        """Initialize the session manager."""
        self._sessions: dict[str, ConversationState] = {}

    def create_session(
        self,
        session_id: Optional[str] = None,
        initial_context: Optional[dict[str, Any]] = None,
    ) -> ConversationState:
        """
        Create a new session.
        
        Args:
            session_id: Optional custom session ID
            initial_context: Optional initial context data
            
        Returns:
            New ConversationState instance
        """
        session_id = session_id or str(uuid.uuid4())
        state = ConversationState(
            conversation_id=session_id,
            context=initial_context or {},
        )
        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """
        Get an existing session.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            ConversationState if found, None otherwise
        """
        return self._sessions.get(session_id)

    def get_or_create_session(
        self,
        session_id: str,
        initial_context: Optional[dict[str, Any]] = None,
    ) -> ConversationState:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Session ID
            initial_context: Optional initial context for new sessions
            
        Returns:
            ConversationState instance
        """
        if session_id in self._sessions:
            return self._sessions[session_id]
        return self.create_session(session_id, initial_context)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[str]:
        """
        List all session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self._sessions.keys())

    def get_session_count(self) -> int:
        """
        Get number of active sessions.
        
        Returns:
            Number of sessions
        """
        return len(self._sessions)

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of sessions removed
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = [
            sid for sid, state in self._sessions.items()
            if state.updated_at < cutoff
        ]

        for sid in to_remove:
            del self._sessions[sid]

        return len(to_remove)

    def export_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Export session data as dictionary.
        
        Args:
            session_id: Session ID to export
            
        Returns:
            Session data dictionary or None
        """
        state = self.get_session(session_id)
        if state:
            return state.to_dict()
        return None

    def import_session(self, data: dict[str, Any]) -> ConversationState:
        """
        Import session from dictionary.
        
        Args:
            data: Session data dictionary
            
        Returns:
            Imported ConversationState
        """
        state = ConversationState.from_dict(data)
        self._sessions[state.conversation_id] = state
        return state