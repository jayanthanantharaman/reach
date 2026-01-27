"""
Unit tests for REACH state management.

"""

import pytest
from datetime import datetime, timedelta

from src.workflow.state_management import (
    Message,
    ConversationState,
    SessionManager,
)


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test basic message creation."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test message with metadata."""
        metadata = {"agent": "blog_writer", "tokens": 100}
        msg = Message(role="assistant", content="Response", metadata=metadata)

        assert msg.metadata == metadata


class TestConversationState:
    """Tests for ConversationState class."""

    def test_state_creation(self):
        """Test basic state creation."""
        state = ConversationState()

        assert state.conversation_id is not None
        assert state.messages == []
        assert state.context == {}
        assert state.current_agent is None

    def test_add_message(self):
        """Test adding messages."""
        state = ConversationState()
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there!")

        assert len(state.messages) == 2
        assert state.messages[0].role == "user"
        assert state.messages[1].role == "assistant"

    def test_get_history(self):
        """Test getting conversation history."""
        state = ConversationState()
        state.add_message("user", "Message 1")
        state.add_message("assistant", "Response 1")
        state.add_message("user", "Message 2")

        history = state.get_history()
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Message 1"

    def test_get_history_with_limit(self):
        """Test getting limited history."""
        state = ConversationState()
        for i in range(10):
            state.add_message("user", f"Message {i}")

        history = state.get_history(limit=3)
        assert len(history) == 3
        assert history[0]["content"] == "Message 7"

    def test_update_context(self):
        """Test updating context."""
        state = ConversationState()
        state.update_context("topic", "AI Marketing")
        state.update_context("keywords", ["AI", "marketing"])

        assert state.context["topic"] == "AI Marketing"
        assert state.context["keywords"] == ["AI", "marketing"]

    def test_store_content(self):
        """Test storing generated content."""
        state = ConversationState()
        state.store_content("blog", "Blog content here")
        state.store_content("blog", "Another blog")
        state.store_content("linkedin", "LinkedIn post")

        assert len(state.generated_content["blog"]) == 2
        assert len(state.generated_content["linkedin"]) == 1

    def test_get_latest_content(self):
        """Test getting latest content."""
        state = ConversationState()
        state.store_content("blog", "First blog")
        state.store_content("blog", "Second blog")

        latest = state.get_latest_content("blog")
        assert latest == "Second blog"

        missing = state.get_latest_content("image")
        assert missing is None

    def test_clear_history(self):
        """Test clearing history."""
        state = ConversationState()
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi")

        state.clear_history()
        assert state.messages == []

    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = ConversationState()
        state.add_message("user", "Hello")
        state.update_context("key", "value")

        data = state.to_dict()

        assert "conversation_id" in data
        assert "messages" in data
        assert "context" in data
        assert len(data["messages"]) == 1

    def test_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            "conversation_id": "test-123",
            "messages": [
                {"role": "user", "content": "Hello", "timestamp": datetime.now().isoformat()},
            ],
            "context": {"key": "value"},
            "current_agent": "blog_writer",
            "generated_content": {},
        }

        state = ConversationState.from_dict(data)

        assert state.conversation_id == "test-123"
        assert len(state.messages) == 1
        assert state.context["key"] == "value"


class TestSessionManager:
    """Tests for SessionManager class."""

    def test_create_session(self):
        """Test creating a session."""
        manager = SessionManager()
        session = manager.create_session()

        assert session is not None
        assert session.conversation_id is not None

    def test_create_session_with_id(self):
        """Test creating a session with custom ID."""
        manager = SessionManager()
        session = manager.create_session(session_id="custom-123")

        assert session.conversation_id == "custom-123"

    def test_create_session_with_context(self):
        """Test creating a session with initial context."""
        manager = SessionManager()
        context = {"user": "test_user", "preferences": {"tone": "professional"}}
        session = manager.create_session(initial_context=context)

        assert session.context["user"] == "test_user"

    def test_get_session(self):
        """Test getting an existing session."""
        manager = SessionManager()
        created = manager.create_session(session_id="test-session")

        retrieved = manager.get_session("test-session")
        assert retrieved is created

    def test_get_nonexistent_session(self):
        """Test getting a non-existent session."""
        manager = SessionManager()
        session = manager.get_session("nonexistent")

        assert session is None

    def test_get_or_create_session(self):
        """Test get or create session."""
        manager = SessionManager()

        # First call creates
        session1 = manager.get_or_create_session("test-id")
        assert session1 is not None

        # Second call retrieves
        session2 = manager.get_or_create_session("test-id")
        assert session1 is session2

    def test_delete_session(self):
        """Test deleting a session."""
        manager = SessionManager()
        manager.create_session(session_id="to-delete")

        result = manager.delete_session("to-delete")
        assert result is True

        session = manager.get_session("to-delete")
        assert session is None

    def test_delete_nonexistent_session(self):
        """Test deleting a non-existent session."""
        manager = SessionManager()
        result = manager.delete_session("nonexistent")

        assert result is False

    def test_list_sessions(self):
        """Test listing all sessions."""
        manager = SessionManager()
        manager.create_session(session_id="session-1")
        manager.create_session(session_id="session-2")
        manager.create_session(session_id="session-3")

        sessions = manager.list_sessions()
        assert len(sessions) == 3
        assert "session-1" in sessions
        assert "session-2" in sessions

    def test_get_session_count(self):
        """Test getting session count."""
        manager = SessionManager()
        assert manager.get_session_count() == 0

        manager.create_session()
        manager.create_session()
        assert manager.get_session_count() == 2

    def test_export_session(self):
        """Test exporting a session."""
        manager = SessionManager()
        session = manager.create_session(session_id="export-test")
        session.add_message("user", "Hello")

        data = manager.export_session("export-test")

        assert data is not None
        assert data["conversation_id"] == "export-test"
        assert len(data["messages"]) == 1

    def test_export_nonexistent_session(self):
        """Test exporting a non-existent session."""
        manager = SessionManager()
        data = manager.export_session("nonexistent")

        assert data is None

    def test_import_session(self):
        """Test importing a session."""
        manager = SessionManager()
        data = {
            "conversation_id": "imported-session",
            "messages": [
                {"role": "user", "content": "Imported message"},
            ],
            "context": {"imported": True},
            "current_agent": None,
            "generated_content": {},
        }

        session = manager.import_session(data)

        assert session.conversation_id == "imported-session"
        assert len(session.messages) == 1

        # Should be retrievable
        retrieved = manager.get_session("imported-session")
        assert retrieved is session