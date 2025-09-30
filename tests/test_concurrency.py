"""Concurrency bug test - race condition in idempotent creation."""
import pytest
import asyncio
from httpx import AsyncClient
from src.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestConcurrencyBug:
    """Test for concurrent creation race condition.
    
    KNOWN BUG: When multiple requests create the same snippet concurrently,
    there's a race condition where unique constraint can be violated or
    multiple snippets with same hash can be created.
    
    This happens because the check-and-create is not atomic.
    """
    
    async def test_concurrent_creation_race_condition(self, client):
        """Test concurrent creation of identical snippets.
        
        This test demonstrates the race condition bug where concurrent
        requests to create the same snippet can fail or create duplicates.
        """
        snippet_data = {
            "title": "Concurrent Test Bug",
            "content": "This will expose the race condition",
            "tags": ["concurrency", "bug"]
        }
        
        # Create 10 concurrent requests for the same snippet
        tasks = [
            client.post("/snippets", json=snippet_data)
            for _ in range(10)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful responses
        successful = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code == 201
        ]
        
        # Extract IDs
        ids = [r.json()["id"] for r in successful]
        unique_ids = set(ids)
        
        # EXPECTED (after fix): All should return the same ID
        # ACTUAL (with bug): May have multiple IDs or errors
        print(f"Created {len(successful)} snippets with {len(unique_ids)} unique IDs")
        print(f"IDs: {unique_ids}")
        
        # After fix, this should pass
        assert len(unique_ids) == 1, \
            f"Race condition detected: {len(unique_ids)} different IDs created instead of 1"
