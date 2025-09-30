"""FastAPI application entry point."""
from fastapi import FastAPI, Depends, HTTPException, status, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
import uvicorn

from src.config import settings
from src.database import get_db, init_db
from src.schemas import (
    SnippetCreate, SnippetUpdate, SnippetResponse,
    SnippetCreateResponse, SnippetSearchResponse,
    HealthResponse, ErrorResponse
)
from src.crud import (
    create_snippet, get_snippet, search_snippets,
    update_snippet, delete_snippet, CRUDException
)
from src.middleware import TracingMiddleware, RateLimitMiddleware, logger
from src.utils import get_trace_id, parse_tags

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Online code snippet service"
)

# Add middlewares
app.add_middleware(TracingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Add CORS
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured error response."""
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": str(exc.detail),
            "trace_id": get_trace_id()
        }
    )


@app.exception_handler(CRUDException)
async def crud_exception_handler(request, exc: CRUDException):
    """Handle CRUD exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "trace_id": get_trace_id()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.log("error", "Unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "trace_id": get_trace_id()
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()
    logger.log("info", "Application started", version=settings.APP_VERSION)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/snippets", response_model=SnippetCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_snippet_endpoint(
    snippet: SnippetCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new code snippet (idempotent)."""
    try:
        created = await create_snippet(db, snippet)
        logger.log("info", "Snippet created", snippet_id=created.id)
        return {
            "id": created.id,
            "created_at": created.created_at
        }
    except Exception as e:
        logger.log("error", "Failed to create snippet", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "CREATE_FAILED",
                "message": "Failed to create snippet",
                "trace_id": get_trace_id()
            }
        )


@app.get("/snippets/{snippet_id}", response_model=SnippetResponse)
async def get_snippet_endpoint(snippet_id: int):
    """Get a single code snippet by ID."""
    snippet = await get_snippet(snippet_id)
    
    if not snippet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SNIPPET_NOT_FOUND",
                "message": f"Snippet with ID {snippet_id} not found",
                "trace_id": get_trace_id()
            }
        )
    
    return {
        "id": snippet.id,
        "title": snippet.title,
        "content": snippet.content,
        "tags": parse_tags(snippet.tags),
        "created_at": snippet.created_at,
        "updated_at": snippet.updated_at
    }


@app.get("/snippets", response_model=SnippetSearchResponse)
async def search_snippets_endpoint(
    query: Optional[str] = Query(None, description="Full-text search query"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size")
):
    """Search code snippets with filters and pagination."""
    try:
        snippets, total = await search_snippets(query, tag, page, page_size)
        
        items = [
            {
                "id": s.id,
                "title": s.title,
                "content": s.content,
                "tags": parse_tags(s.tags),
                "created_at": s.created_at,
                "updated_at": s.updated_at
            }
            for s in snippets
        ]
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }
    except Exception as e:
        logger.log("error", "Search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "SEARCH_FAILED",
                "message": "Failed to search snippets",
                "trace_id": get_trace_id()
            }
        )


@app.patch("/snippets/{snippet_id}", response_model=SnippetResponse)
async def update_snippet_endpoint(
    snippet_id: int,
    update_data: SnippetUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a code snippet (partial update)."""
    try:
        updated = await update_snippet(snippet_id, update_data)
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "SNIPPET_NOT_FOUND",
                    "message": f"Snippet with ID {snippet_id} not found",
                    "trace_id": get_trace_id()
                }
            )
        
        logger.log("info", "Snippet updated", snippet_id=snippet_id)
        
        return {
            "id": updated.id,
            "title": updated.title,
            "content": updated.content,
            "tags": parse_tags(updated.tags),
            "created_at": updated.created_at,
            "updated_at": updated.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.log("error", "Update failed", snippet_id=snippet_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "UPDATE_FAILED",
                "message": "Failed to update snippet",
                "trace_id": get_trace_id()
            }
        )


@app.delete("/snippets/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snippet_endpoint(snippet_id: int):
    """Soft delete a code snippet."""
    try:
        deleted = await delete_snippet(snippet_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "SNIPPET_NOT_FOUND",
                    "message": f"Snippet with ID {snippet_id} not found",
                    "trace_id": get_trace_id()
                }
            )
        
        logger.log("info", "Snippet deleted", snippet_id=snippet_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.log("error", "Delete failed", snippet_id=snippet_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "DELETE_FAILED",
                "message": "Failed to delete snippet",
                "trace_id": get_trace_id()
            }
        )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
