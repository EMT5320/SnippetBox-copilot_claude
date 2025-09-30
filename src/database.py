"""Database connection and session management."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db():
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    import aiosqlite
    from pathlib import Path
    
    # Extract database path from URL
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    # Read migration SQL
    migration_file = Path(__file__).parent.parent / "migrations" / "init.sql"
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Execute migration
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(migration_sql)
        await db.commit()
