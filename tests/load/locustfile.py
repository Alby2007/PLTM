"""Load testing scenarios for LTM system using Locust"""

from locust import HttpUser, task, between, events
import random
import json
from datetime import datetime


class LTMUser(HttpUser):
    """
    Simulated user for load testing.
    
    Simulates realistic user behavior:
    - Register/login
    - Create memories
    - Search memories
    - View statistics
    - Bulk operations
    """
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Called when user starts - register and login"""
        self.user_id = f"load_test_user_{random.randint(1, 10000)}"
        self.access_token = None
        
        # Register user
        response = self.client.post("/auth/register", json={
            "email": f"{self.user_id}@example.com",
            "password": "testpass123",
            "full_name": f"Load Test User {self.user_id}",
            "tenant_id": "load_test"
        }, catch_response=True)
        
        if response.status_code == 201:
            data = response.json()
            self.access_token = data.get("access_token")
            response.success()
        else:
            # User might already exist, try login
            response = self.client.post("/auth/login", json={
                "email": f"{self.user_id}@example.com",
                "password": "testpass123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
    
    def _get_headers(self):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    @task(10)
    def create_memory(self):
        """Create a new memory atom (most common operation)"""
        if not self.access_token:
            return
        
        predicates = ["likes", "dislikes", "works_at", "studies_at", "uses", "prefers"]
        objects = ["Python", "JavaScript", "Rust", "Go", "Java", "C++", "Anthropic", "Google"]
        atom_types = ["preference", "affiliation", "skill", "belief"]
        
        self.client.post(
            f"/api/v1/memory/{self.user_id}",
            json={
                "subject": self.user_id,
                "predicate": random.choice(predicates),
                "object": random.choice(objects),
                "atom_type": random.choice(atom_types),
                "confidence": random.uniform(0.7, 1.0),
                "contexts": []
            },
            headers=self._get_headers(),
            name="/api/v1/memory/[user_id] (POST)"
        )
    
    @task(20)
    def get_memories(self):
        """Get user's memories (very common operation)"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/memory/{self.user_id}?limit=50",
            headers=self._get_headers(),
            name="/api/v1/memory/[user_id] (GET)"
        )
    
    @task(5)
    def search_full_text(self):
        """Full-text search"""
        if not self.access_token:
            return
        
        queries = ["Python", "programming", "work", "like", "learn"]
        
        self.client.get(
            f"/api/v1/search/{self.user_id}/full-text?q={random.choice(queries)}",
            headers=self._get_headers(),
            name="/api/v1/search/[user_id]/full-text"
        )
    
    @task(3)
    def search_semantic(self):
        """Semantic search (more expensive)"""
        if not self.access_token:
            return
        
        queries = ["programming languages", "software development", "work experience"]
        
        self.client.get(
            f"/api/v1/search/{self.user_id}/semantic?q={random.choice(queries)}",
            headers=self._get_headers(),
            name="/api/v1/search/[user_id]/semantic"
        )
    
    @task(2)
    def get_statistics(self):
        """Get memory statistics"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/memory/{self.user_id}/stats",
            headers=self._get_headers(),
            name="/api/v1/memory/[user_id]/stats"
        )
    
    @task(1)
    def get_weak_memories(self):
        """Get weak memories"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/memory/{self.user_id}/weak?threshold=0.5",
            headers=self._get_headers(),
            name="/api/v1/memory/[user_id]/weak"
        )
    
    @task(1)
    def reconsolidate(self):
        """Reconsolidate weak memories"""
        if not self.access_token:
            return
        
        self.client.post(
            f"/api/v1/memory/{self.user_id}/reconsolidate?threshold=0.5",
            headers=self._get_headers(),
            name="/api/v1/memory/[user_id]/reconsolidate"
        )
    
    @task(1)
    def bulk_import(self):
        """Bulk import atoms"""
        if not self.access_token:
            return
        
        atoms = [
            {
                "subject": self.user_id,
                "predicate": "likes",
                "object": f"Technology_{i}",
                "atom_type": "preference",
                "confidence": 0.8
            }
            for i in range(10)
        ]
        
        self.client.post(
            f"/api/v1/bulk/{self.user_id}/import",
            json={
                "atoms": atoms,
                "validate": True,
                "skip_duplicates": True
            },
            headers=self._get_headers(),
            name="/api/v1/bulk/[user_id]/import"
        )


class AdminUser(HttpUser):
    """
    Simulated admin user for load testing admin endpoints.
    """
    
    wait_time = between(5, 10)
    
    def on_start(self):
        """Login as admin"""
        # TODO: Implement admin login
        self.access_token = None
    
    @task
    def get_auth_stats(self):
        """Get authentication statistics"""
        if not self.access_token:
            return
        
        self.client.get(
            "/auth/admin/stats",
            headers={
                "Authorization": f"Bearer {self.access_token}"
            },
            name="/auth/admin/stats"
        )


class ReadOnlyUser(HttpUser):
    """
    Simulated read-only user (analytics, monitoring).
    """
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Register and login"""
        self.user_id = f"readonly_user_{random.randint(1, 1000)}"
        self.access_token = None
        
        response = self.client.post("/auth/register", json={
            "email": f"{self.user_id}@example.com",
            "password": "testpass123",
            "full_name": f"Read Only User {self.user_id}",
            "tenant_id": "load_test"
        })
        
        if response.status_code == 201:
            data = response.json()
            self.access_token = data.get("access_token")
    
    @task(10)
    def get_memories(self):
        """Get memories"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/memory/{self.user_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/api/v1/memory/[user_id] (GET)"
        )
    
    @task(5)
    def search(self):
        """Search memories"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/search/{self.user_id}/full-text?q=test",
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/api/v1/search/[user_id]/full-text"
        )
    
    @task(3)
    def get_stats(self):
        """Get statistics"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/memory/{self.user_id}/stats",
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/api/v1/memory/[user_id]/stats"
        )


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics"""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("Load test starting...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    print("Load test completed!")
    
    # Print summary statistics
    stats = environment.stats
    print(f"\nTotal requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min response time: {stats.total.min_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")
    
    # Check if we met performance targets
    if stats.total.avg_response_time > 200:
        print("\n⚠️  WARNING: Average response time exceeds 200ms target")
    
    if stats.total.num_failures > stats.total.num_requests * 0.01:
        print("\n⚠️  WARNING: Failure rate exceeds 1% target")
    
    if stats.total.total_rps < 100:
        print("\n⚠️  WARNING: Throughput below 100 req/sec target")


# Custom load test scenarios
class SpikeTest(HttpUser):
    """
    Spike test scenario - sudden burst of traffic.
    """
    
    wait_time = between(0.1, 0.5)  # Very short wait time
    
    def on_start(self):
        self.user_id = f"spike_user_{random.randint(1, 10000)}"
        self.access_token = None
        
        response = self.client.post("/auth/register", json={
            "email": f"{self.user_id}@example.com",
            "password": "testpass123",
            "full_name": f"Spike User {self.user_id}",
            "tenant_id": "spike_test"
        })
        
        if response.status_code == 201:
            self.access_token = response.json().get("access_token")
    
    @task
    def rapid_requests(self):
        """Make rapid requests"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/memory/{self.user_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/api/v1/memory/[user_id] (SPIKE)"
        )


class SoakTest(HttpUser):
    """
    Soak test scenario - sustained load over time.
    """
    
    wait_time = between(2, 4)
    
    def on_start(self):
        self.user_id = f"soak_user_{random.randint(1, 1000)}"
        self.access_token = None
        
        response = self.client.post("/auth/register", json={
            "email": f"{self.user_id}@example.com",
            "password": "testpass123",
            "full_name": f"Soak User {self.user_id}",
            "tenant_id": "soak_test"
        })
        
        if response.status_code == 201:
            self.access_token = response.json().get("access_token")
    
    @task(5)
    def sustained_read(self):
        """Sustained read operations"""
        if not self.access_token:
            return
        
        self.client.get(
            f"/api/v1/memory/{self.user_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/api/v1/memory/[user_id] (SOAK)"
        )
    
    @task(1)
    def sustained_write(self):
        """Sustained write operations"""
        if not self.access_token:
            return
        
        self.client.post(
            f"/api/v1/memory/{self.user_id}",
            json={
                "subject": self.user_id,
                "predicate": "likes",
                "object": f"Item_{random.randint(1, 1000)}",
                "atom_type": "preference",
                "confidence": 0.8
            },
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/api/v1/memory/[user_id] (SOAK POST)"
        )
