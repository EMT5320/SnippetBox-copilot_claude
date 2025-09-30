-- SnippetBox Database Schema
CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    content_hash TEXT NOT NULL UNIQUE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_snippets_deleted_at ON snippets(deleted_at);
CREATE INDEX IF NOT EXISTS idx_snippets_content_hash ON snippets(content_hash);
CREATE INDEX IF NOT EXISTS idx_snippets_created_at ON snippets(created_at DESC);

-- Full-text search support (SQLite FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS snippets_fts USING fts5(
    title, 
    content, 
    content='snippets', 
    content_rowid='id'
);

-- Triggers to keep FTS table in sync
CREATE TRIGGER IF NOT EXISTS snippets_ai AFTER INSERT ON snippets BEGIN
    INSERT INTO snippets_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS snippets_ad AFTER DELETE ON snippets BEGIN
    DELETE FROM snippets_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS snippets_au AFTER UPDATE ON snippets BEGIN
    UPDATE snippets_fts SET title = new.title, content = new.content WHERE rowid = new.id;
END;
