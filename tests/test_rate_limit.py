"""Rate limit tests."""
import pytest
import asyncio
from httpx import AsyncClient
from src.main import app
from src.config import settings


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestRateLimit:
    """Rate limiting tests."""
    
    async def test_rate_limit_enforcement(self, client):
        """Test that rate limit is enforced."""
        if not settings.RATE_LIMIT_ENABLED:
            pytest.skip("Rate limiting disabled")
        
        limit = settings.RATE_LIMIT_PER_MINUTE
        
        # Make requests up to limit
        tasks = []
        for i in range(limit + 5):
            snippet_data = {
                "title": f"Rate Test {i}",
                "content": f"Content {i}",
                "tags": []
            }
            tasks.append(client.post("/snippets", json=snippet_data))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count 429 responses
        rate_limited = sum(
            1 for r in responses 
            if not isinstance(r, Exception) and r.status_code == 429
        )
        
        # Should have some rate limited requests
        assert rate_limited > 0
    
    async def test_read_operations_not_rate_limited(self, client):
        """Test that read operations are not rate limited."""
        # Make many read requests
        tasks = [client.get("/health") for _ in range(100)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
