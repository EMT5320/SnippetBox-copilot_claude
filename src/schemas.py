"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from src.config import settings


class SnippetCreate(BaseModel):
    """Schema for creating a snippet."""
    title: str = Field(..., min_length=1, max_length=settings.MAX_TITLE_LENGTH)
    content: str = Field(..., min_length=1, max_length=settings.MAX_CONTENT_LENGTH)
    tags: List[str] = Field(default_factory=list, max_length=settings.MAX_TAGS_COUNT)
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if len(v) > settings.MAX_TAGS_COUNT:
            raise ValueError(f'Maximum {settings.MAX_TAGS_COUNT} tags allowed')
        for tag in v:
            if len(tag) > settings.MAX_TAG_LENGTH:
                raise ValueError(f'Tag length cannot exceed {settings.MAX_TAG_LENGTH} characters')
            if not tag.strip():
                raise ValueError('Tag cannot be empty')
        return [tag.strip() for tag in v]


class SnippetUpdate(BaseModel):
    """Schema for updating a snippet."""
    title: Optional[str] = Field(None, min_length=1, max_length=settings.MAX_TITLE_LENGTH)
    content: Optional[str] = Field(None, min_length=1, max_length=settings.MAX_CONTENT_LENGTH)
    tags: Optional[List[str]] = Field(None, max_length=settings.MAX_TAGS_COUNT)
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v is None:
            return v
        if len(v) > settings.MAX_TAGS_COUNT:
            raise ValueError(f'Maximum {settings.MAX_TAGS_COUNT} tags allowed')
        for tag in v:
            if len(tag) > settings.MAX_TAG_LENGTH:
                raise ValueError(f'Tag length cannot exceed {settings.MAX_TAG_LENGTH} characters')
            if not tag.strip():
                raise ValueError('Tag cannot be empty')
        return [tag.strip() for tag in v]


class SnippetResponse(BaseModel):
    """Schema for snippet response."""
    id: int
    title: str
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class SnippetCreateResponse(BaseModel):
    """Schema for create response."""
    id: int
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class SnippetSearchResponse(BaseModel):
    """Schema for search response."""
    total: int
    page: int
    page_size: int
    items: List[SnippetResponse]


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    time: str


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error_code: str
    message: str
    trace_id: str
