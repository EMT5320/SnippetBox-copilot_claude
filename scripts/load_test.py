"""Load testing script for search endpoint."""
from locust import HttpUser, task, between
import random


class SnippetBoxUser(HttpUser):
    """Load test user for SnippetBox."""
    
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        """Setup - create some test data."""
        # Create a few snippets for search
        for i in range(5):
            self.client.post("/snippets", json={
                "title": f"Load Test Snippet {i}",
                "content": f"Content for load testing {i}" * 10,
                "tags": ["loadtest", f"tag{i}"]
            })
    
    @task(10)
    def search_all(self):
        """Search all snippets (most common operation)."""
        page = random.randint(1, 5)
        self.client.get(f"/snippets?page={page}&page_size=20")
    
    @task(5)
    def search_with_query(self):
        """Search with text query."""
        queries = ["Load", "Test", "Snippet", "Content"]
        query = random.choice(queries)
        self.client.get(f"/snippets?query={query}")
    
    @task(3)
    def search_with_tag(self):
        """Search by tag."""
        tags = ["loadtest", "tag0", "tag1", "tag2"]
        tag = random.choice(tags)
        self.client.get(f"/snippets?tag={tag}")
    
    @task(2)
    def search_combined(self):
        """Search with combined filters."""
        self.client.get("/snippets?query=Load&tag=loadtest&page=1")
    
    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get("/health")


if __name__ == "__main__":
    import os
    os.system("locust -f scripts/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=30s --headless")
