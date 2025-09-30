"""CRUD operations for snippets."""
import aiosqlite
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Snippet
from src.schemas import SnippetCreate, SnippetUpdate
from src.utils import compute_content_hash, parse_tags, serialize_tags
from src.config import settings


class CRUDException(Exception):
    """Custom exception for CRUD operations."""
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


async def create_snippet(db: AsyncSession, snippet_data: SnippetCreate) -> Snippet:
    """Create a new snippet with idempotency check (race-condition safe)."""
    content_hash = compute_content_hash(snippet_data.title, snippet_data.content)
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Atomic operation: try to insert, ignore if hash conflict (idempotency)
        try:
            tags_json = serialize_tags(snippet_data.tags)
            cursor = await conn.execute(
                """INSERT OR IGNORE INTO snippets (title, content, tags, content_hash) 
                   VALUES (?, ?, ?, ?)""",
                (snippet_data.title, snippet_data.content, tags_json, content_hash)
            )
            await conn.commit()
        except Exception as e:
            # Rollback on any database error
            await conn.rollback()
            raise CRUDException("CREATE_FAILED", f"Database error: {str(e)}")
        
        # Always query to return the record (whether newly created or existing)
        cursor = await conn.execute(
            "SELECT * FROM snippets WHERE content_hash = ? AND deleted_at IS NULL",
            (content_hash,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise CRUDException("CREATE_FAILED", "Failed to create or retrieve snippet")
        
        return Snippet(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            tags=row['tags'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            content_hash=row['content_hash']
        )


async def get_snippet(snippet_id: int) -> Optional[Snippet]:
    """Get a snippet by ID (excluding soft-deleted)."""
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM snippets WHERE id = ? AND deleted_at IS NULL",
            (snippet_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        return Snippet(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            tags=row['tags'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            content_hash=row['content_hash']
        )


async def search_snippets(
    query: Optional[str] = None,
    tag: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[Snippet], int]:
    """Search snippets with filters and pagination."""
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Build query
        where_conditions = ["deleted_at IS NULL"]
        params = []
        
        # Full-text search on title/content
        if query:
            where_conditions.append(
                "id IN (SELECT rowid FROM snippets_fts WHERE snippets_fts MATCH ?)"
            )
            params.append(query)
        
        # Tag filter
        if tag:
            where_conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total
        count_sql = f"SELECT COUNT(*) as total FROM snippets WHERE {where_clause}"
        cursor = await conn.execute(count_sql, params)
        total = (await cursor.fetchone())['total']
        
        # Fetch paginated results
        offset = (page - 1) * page_size
        select_sql = f"""
            SELECT * FROM snippets 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor = await conn.execute(select_sql, params + [page_size, offset])
        rows = await cursor.fetchall()
        
        snippets = [
            Snippet(
                id=row['id'],
                title=row['title'],
                content=row['content'],
                tags=row['tags'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                content_hash=row['content_hash']
            )
            for row in rows
        ]
        
        return snippets, total


async def update_snippet(snippet_id: int, update_data: SnippetUpdate) -> Optional[Snippet]:
    """Update a snippet."""
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Check if snippet exists and not deleted
        cursor = await conn.execute(
            "SELECT * FROM snippets WHERE id = ? AND deleted_at IS NULL",
            (snippet_id,)
        )
        existing = await cursor.fetchone()
        
        if not existing:
            return None
        
        # Build update fields
        update_fields = []
        params = []
        
        if update_data.title is not None:
            update_fields.append("title = ?")
            params.append(update_data.title)
        
        if update_data.content is not None:
            update_fields.append("content = ?")
            params.append(update_data.content)
        
        if update_data.tags is not None:
            update_fields.append("tags = ?")
            params.append(serialize_tags(update_data.tags))
        
        if not update_fields:
            # No fields to update, return existing
            return Snippet(
                id=existing['id'],
                title=existing['title'],
                content=existing['content'],
                tags=existing['tags'],
                created_at=existing['created_at'],
                updated_at=existing['updated_at'],
                content_hash=existing['content_hash']
            )
        
        # Update content_hash if title or content changed
        new_title = update_data.title if update_data.title is not None else existing['title']
        new_content = update_data.content if update_data.content is not None else existing['content']
        new_hash = compute_content_hash(new_title, new_content)
        update_fields.append("content_hash = ?")
        params.append(new_hash)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(snippet_id)
        
        update_sql = f"UPDATE snippets SET {', '.join(update_fields)} WHERE id = ?"
        await conn.execute(update_sql, params)
        await conn.commit()
        
        # Fetch updated snippet
        cursor = await conn.execute(
            "SELECT * FROM snippets WHERE id = ?",
            (snippet_id,)
        )
        row = await cursor.fetchone()
        
        return Snippet(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            tags=row['tags'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            content_hash=row['content_hash']
        )


async def delete_snippet(snippet_id: int) -> bool:
    """Soft delete a snippet."""
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    async with aiosqlite.connect(db_path) as conn:
        # Check if snippet exists and not already deleted
        cursor = await conn.execute(
            "SELECT id FROM snippets WHERE id = ? AND deleted_at IS NULL",
            (snippet_id,)
        )
        existing = await cursor.fetchone()
        
        if not existing:
            return False
        
        # Soft delete
        await conn.execute(
            "UPDATE snippets SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (snippet_id,)
        )
        await conn.commit()
        return True
