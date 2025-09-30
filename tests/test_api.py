"""API tests for SnippetBox."""
import pytest
from httpx import AsyncClient
from src.main import app
from src.database import init_db
import os


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Setup test database."""
    # Use test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_snippetbox.db"
    await init_db()
    yield
    # Cleanup
    if os.path.exists("test_snippetbox.db"):
        os.remove("test_snippetbox.db")


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestHealthCheck:
    """Health check tests."""
    
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "time" in data


class TestCreateSnippet:
    """Create snippet tests."""
    
    async def test_create_snippet_success(self, client):
        """Test successful snippet creation."""
        snippet_data = {
            "title": "Test Snippet",
            "content": "print('Hello, World!')",
            "tags": ["python", "test"]
        }
        response = await client.post("/snippets", json=snippet_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "created_at" in data
    
    async def test_create_snippet_missing_title(self, client):
        """Test creation with missing title."""
        snippet_data = {
            "content": "print('Hello')",
            "tags": []
        }
        response = await client.post("/snippets", json=snippet_data)
        assert response.status_code == 422
    
    async def test_create_snippet_invalid_tags(self, client):
        """Test creation with invalid tags."""
        snippet_data = {
            "title": "Test",
            "content": "code",
            "tags": ["" * 100]  # Too long tag
        }
        response = await client.post("/snippets", json=snippet_data)
        assert response.status_code == 422


class TestGetSnippet:
    """Get snippet tests."""
    
    async def test_get_snippet_success(self, client):
        """Test successful snippet retrieval."""
        # Create a snippet first
        create_response = await client.post("/snippets", json={
            "title": "Get Test",
            "content": "code here",
            "tags": ["test"]
        })
        snippet_id = create_response.json()["id"]
        
        # Get the snippet
        response = await client.get(f"/snippets/{snippet_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Get Test"
        assert data["content"] == "code here"
        assert data["tags"] == ["test"]
    
    async def test_get_nonexistent_snippet(self, client):
        """Test getting non-existent snippet."""
        response = await client.get("/snippets/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "SNIPPET_NOT_FOUND"


class TestSearchSnippets:
    """Search snippets tests."""
    
    async def test_search_all_snippets(self, client):
        """Test searching all snippets."""
        # Create test snippets
        await client.post("/snippets", json={
            "title": "Search Test 1",
            "content": "Python code",
            "tags": ["python"]
        })
        await client.post("/snippets", json={
            "title": "Search Test 2",
            "content": "JavaScript code",
            "tags": ["javascript"]
        })
        
        response = await client.get("/snippets")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["page"] == 1
        assert data["page_size"] == 20
    
    async def test_search_with_query(self, client):
        """Test searching with text query."""
        await client.post("/snippets", json={
            "title": "Unique Title Search",
            "content": "def function(): pass",
            "tags": []
        })
        
        response = await client.get("/snippets?query=Unique")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    async def test_search_with_tag(self, client):
        """Test searching by tag."""
        await client.post("/snippets", json={
            "title": "Tagged Snippet",
            "content": "content",
            "tags": ["specific-tag"]
        })
        
        response = await client.get("/snippets?tag=specific-tag")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    async def test_search_pagination(self, client):
        """Test pagination."""
        response = await client.get("/snippets?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5


class TestUpdateSnippet:
    """Update snippet tests."""
    
    async def test_update_snippet_title(self, client):
        """Test updating snippet title."""
        # Create snippet
        create_response = await client.post("/snippets", json={
            "title": "Original Title",
            "content": "content",
            "tags": []
        })
        snippet_id = create_response.json()["id"]
        
        # Update title
        response = await client.patch(f"/snippets/{snippet_id}", json={
            "title": "Updated Title"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "content"
    
    async def test_update_snippet_partial(self, client):
        """Test partial update."""
        create_response = await client.post("/snippets", json={
            "title": "Test",
            "content": "Original content",
            "tags": ["tag1"]
        })
        snippet_id = create_response.json()["id"]
        
        response = await client.patch(f"/snippets/{snippet_id}", json={
            "tags": ["tag1", "tag2"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "tag2" in data["tags"]
    
    async def test_update_nonexistent_snippet(self, client):
        """Test updating non-existent snippet."""
        response = await client.patch("/snippets/99999", json={
            "title": "New Title"
        })
        assert response.status_code == 404


class TestDeleteSnippet:
    """Delete snippet tests."""
    
    async def test_delete_snippet(self, client):
        """Test soft delete."""
        # Create snippet
        create_response = await client.post("/snippets", json={
            "title": "To Delete",
            "content": "content",
            "tags": []
        })
        snippet_id = create_response.json()["id"]
        
        # Delete snippet
        response = await client.delete(f"/snippets/{snippet_id}")
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await client.get(f"/snippets/{snippet_id}")
        assert get_response.status_code == 404
    
    async def test_delete_nonexistent_snippet(self, client):
        """Test deleting non-existent snippet."""
        response = await client.delete("/snippets/99999")
        assert response.status_code == 404
