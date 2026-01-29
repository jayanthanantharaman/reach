"""
Content Storage Module for REACH.

This module provides SQLite-based persistent storage for generated content,
keeping the last 5 items per content type.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class ContentStorage:
    """
    SQLite-based storage for generated content.
    
    Stores content with metadata and automatically maintains
    only the last 5 items per content type.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the content storage.
        
        Args:
            db_path: Path to SQLite database file. Defaults to 'content_history.db'
                    in the project root.
        """
        if db_path is None:
            # Default to project root
            db_path = str(Path(__file__).resolve().parents[2] / "content_history.db")
        
        self.db_path = db_path
        self.max_items_per_type = 5
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    prompt TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_type 
                ON content_history(content_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON content_history(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON content_history(created_at DESC)
            """)
            
            conn.commit()

    def save_content(
        self,
        session_id: str,
        content_type: str,
        content: str,
        prompt: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """
        Save generated content to the database.
        
        Automatically removes old entries to keep only the last 5
        items per content type.
        
        Args:
            session_id: Session identifier
            content_type: Type of content (blog, linkedin, instagram, etc.)
            content: The generated content text
            prompt: Optional original prompt that generated this content
            metadata: Optional additional metadata as a dictionary
            
        Returns:
            The ID of the inserted record
        """
        metadata_json = json.dumps(metadata) if metadata else None
        
        with sqlite3.connect(self.db_path) as conn:
            # Insert new content
            cursor = conn.execute(
                """
                INSERT INTO content_history 
                (session_id, content_type, content, prompt, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, content_type, content, prompt, metadata_json)
            )
            inserted_id = cursor.lastrowid
            
            # Delete old entries, keeping only last 5 per content type
            conn.execute(
                """
                DELETE FROM content_history 
                WHERE content_type = ? AND id NOT IN (
                    SELECT id FROM content_history 
                    WHERE content_type = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                )
                """,
                (content_type, content_type, self.max_items_per_type)
            )
            
            conn.commit()
            
        return inserted_id

    def get_recent_content(
        self,
        content_type: Optional[str] = None,
        limit: int = 5,
        session_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get recent content from the database.
        
        Args:
            content_type: Optional filter by content type
            limit: Maximum number of items to return (default 5)
            session_id: Optional filter by session ID
            
        Returns:
            List of content dictionaries with id, content_type, content,
            prompt, metadata, and created_at
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM content_history WHERE 1=1"
            params = []
            
            if content_type:
                query += " AND content_type = ?"
                params.append(content_type)
            
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "content_type": row["content_type"],
                    "content": row["content"],
                    "prompt": row["prompt"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def get_content_by_id(self, content_id: int) -> Optional[dict[str, Any]]:
        """
        Get a specific content item by ID.
        
        Args:
            content_id: The content ID
            
        Returns:
            Content dictionary or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM content_history WHERE id = ?",
                (content_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "content_type": row["content_type"],
                    "content": row["content"],
                    "prompt": row["prompt"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "created_at": row["created_at"],
                }
            return None

    def get_content_types(self) -> list[str]:
        """
        Get all unique content types in the database.
        
        Returns:
            List of content type strings
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT DISTINCT content_type FROM content_history ORDER BY content_type"
            )
            return [row[0] for row in cursor.fetchall()]

    def get_content_count(self, content_type: Optional[str] = None) -> int:
        """
        Get the count of content items.
        
        Args:
            content_type: Optional filter by content type
            
        Returns:
            Number of content items
        """
        with sqlite3.connect(self.db_path) as conn:
            if content_type:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM content_history WHERE content_type = ?",
                    (content_type,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM content_history")
            return cursor.fetchone()[0]

    def delete_content(self, content_id: int) -> bool:
        """
        Delete a specific content item.
        
        Args:
            content_id: The content ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM content_history WHERE id = ?",
                (content_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        """
        Clear all content from the database.
        
        Returns:
            Number of items deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM content_history")
            conn.commit()
            return cursor.rowcount

    def clear_by_type(self, content_type: str) -> int:
        """
        Clear all content of a specific type.
        
        Args:
            content_type: The content type to clear
            
        Returns:
            Number of items deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM content_history WHERE content_type = ?",
                (content_type,)
            )
            conn.commit()
            return cursor.rowcount

    def search_content(
        self,
        search_term: str,
        content_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search content by text.
        
        Args:
            search_term: Text to search for in content
            content_type: Optional filter by content type
            limit: Maximum results to return
            
        Returns:
            List of matching content dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM content_history WHERE content LIKE ?"
            params = [f"%{search_term}%"]
            
            if content_type:
                query += " AND content_type = ?"
                params.append(content_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "content_type": row["content_type"],
                    "content": row["content"],
                    "prompt": row["prompt"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def get_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            # Total count
            total = conn.execute("SELECT COUNT(*) FROM content_history").fetchone()[0]
            
            # Count by type
            cursor = conn.execute(
                """
                SELECT content_type, COUNT(*) as count 
                FROM content_history 
                GROUP BY content_type
                """
            )
            by_type = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Latest entry
            cursor = conn.execute(
                "SELECT created_at FROM content_history ORDER BY created_at DESC LIMIT 1"
            )
            latest = cursor.fetchone()
            latest_at = latest[0] if latest else None
            
            # Database file size
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            return {
                "total_items": total,
                "items_by_type": by_type,
                "latest_entry": latest_at,
                "database_size_bytes": db_size,
                "max_items_per_type": self.max_items_per_type,
            }