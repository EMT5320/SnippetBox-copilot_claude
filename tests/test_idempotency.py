"""Idempotency tests."""
import pytest
from httpx import AsyncClient
from src.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestIdempotency:
    """Test idempotent creation."""
    
    async def test_duplicate_create_returns_same_resource(self, client):
        """Test that creating duplicate snippet returns same ID."""
        snippet_data = {
            "title": "Idempotency Test",
            "content": "Same content for idempotency",
            "tags": ["idempotent"]
        }
        
        # Create first time
        response1 = await client.post("/snippets", json=snippet_data)
        assert response1.status_code == 201
        id1 = response1.json()["id"]
        
        # Create second time with same data
        response2 = await client.post("/snippets", json=snippet_data)
        assert response2.status_code == 201
        id2 = response2.json()["id"]
        
        # Should return the same ID
        assert id1 == id2
    
    async def test_different_content_creates_new(self, client):
        """Test that different content creates new snippet."""
        snippet1 = {
            "title": "Same Title",
            "content": "Different content 1",
            "tags": []
        }
        snippet2 = {
            "title": "Same Title",
            "content": "Different content 2",
            "tags": []
        }
        
        response1 = await client.post("/snippets", json=snippet1)
        response2 = await client.post("/snippets", json=snippet2)
        
        assert response1.json()["id"] != response2.json()["id"]
