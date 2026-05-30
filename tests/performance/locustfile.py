"""
Performance tests for the restaurant rewards system.

Run with:
    locust -f tests/performance/locustfile.py --headless -u 100 -r 10 --run-time 60s --host http://localhost:8000

Targets:
    - p95 response time < 500ms
    - Error rate < 1%
    - Throughput > 50 req/s at 100 concurrent users
"""
import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


RESTAURANT_CODES = ["REST-001", "REST-002", "REST-003", "REST-005"]
CARD_PREFIXES = ["4532", "5412", "3714", "6011"]


def random_card():
    prefix = random.choice(CARD_PREFIXES)
    suffix = random.randint(1000, 9999)
    return f"{prefix}-LOAD-{suffix:04d}"


def random_amount(min_val=20.0, max_val=500.0):
    return round(random.uniform(min_val, max_val), 2)


class RestaurantUser(HttpUser):
    """Simulates a restaurant system registering customer meals."""
    wait_time = between(0.1, 0.5)

    @task(5)
    def register_standard_meal(self):
        """Register a standard-tier meal (amount < 50)."""
        self.client.post(
            "/api/v1/meals",
            json={
                "card_number": random_card(),
                "restaurant_code": random.choice(RESTAURANT_CODES),
                "amount": random_amount(20.0, 49.99),
                "customer_email": f"user{random.randint(1,1000)}@test.com",
            },
            name="/api/v1/meals [standard]",
        )

    @task(4)
    def register_silver_meal(self):
        """Register a silver-tier meal (50 <= amount < 150)."""
        self.client.post(
            "/api/v1/meals",
            json={
                "card_number": random_card(),
                "restaurant_code": random.choice(RESTAURANT_CODES),
                "amount": random_amount(50.0, 149.99),
                "customer_email": f"user{random.randint(1,1000)}@test.com",
            },
            name="/api/v1/meals [silver]",
        )

    @task(2)
    def register_gold_meal(self):
        """Register a gold-tier meal (150 <= amount < 300)."""
        self.client.post(
            "/api/v1/meals",
            json={
                "card_number": random_card(),
                "restaurant_code": random.choice(RESTAURANT_CODES),
                "amount": random_amount(150.0, 299.99),
                "customer_email": f"user{random.randint(1,1000)}@test.com",
            },
            name="/api/v1/meals [gold]",
        )

    @task(1)
    def register_platinum_meal(self):
        """Register a platinum-tier meal (amount >= 300)."""
        self.client.post(
            "/api/v1/meals",
            json={
                "card_number": random_card(),
                "restaurant_code": random.choice(RESTAURANT_CODES),
                "amount": random_amount(300.0, 500.0),
                "customer_email": f"user{random.randint(1,1000)}@test.com",
            },
            name="/api/v1/meals [platinum]",
        )

    @task(2)
    def health_check(self):
        """Check service health."""
        self.client.get("/health", name="/health")


class HeavyLoadUser(HttpUser):
    """Simulates burst load with minimal wait time."""
    wait_time = between(0.01, 0.1)
    weight = 1  # Only 10% of users are heavy loaders

    @task
    def burst_register(self):
        self.client.post(
            "/api/v1/meals",
            json={
                "card_number": random_card(),
                "restaurant_code": "REST-BURST",
                "amount": random_amount(50.0, 200.0),
            },
            name="/api/v1/meals [burst]",
        )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary after test."""
    stats = environment.stats.total
    print(f"\n=== Performance Test Summary ===")
    print(f"Total requests: {stats.num_requests}")
    print(f"Failures: {stats.num_failures}")
    print(f"Failure rate: {stats.fail_ratio * 100:.2f}%")
    print(f"Avg response time: {stats.avg_response_time:.0f}ms")
    print(f"p95 response time: {stats.get_response_time_percentile(0.95):.0f}ms")

    if stats.fail_ratio > 0.01:
        print("FAIL: Error rate exceeds 1%")
    else:
        print("PASS: Error rate within limits")

    p95 = stats.get_response_time_percentile(0.95)
    if p95 and p95 > 500:
        print("FAIL: p95 latency exceeds 500ms")
    elif p95:
        print("PASS: p95 latency within limits")
