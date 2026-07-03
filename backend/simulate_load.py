import asyncio
import httpx
import time
import statistics
import random
import json

BASE_URL = "http://localhost:8001"
CONCURRENCY_LEVELS = [10, 50, 100, 200]
REQUESTS_PER_USER = 5

async def run_user_session(client, user_id, results):
    """Simulates a single user session with multiple requests."""
    try:
        # 1. Login
        start = time.perf_counter()
        resp = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        latency = time.perf_counter() - start
        results['login'].append(latency)
        
        if resp.status_code != 200:
            results['errors'] += 1
            return
            
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Sequential requests as per user activity
        for _ in range(REQUESTS_PER_USER):
            # Get Items
            start = time.perf_counter()
            resp = await client.get("/items", headers=headers)
            results['get_items'].append(time.perf_counter() - start)
            
            # Get Feed (Filtered)
            start = time.perf_counter()
            resp = await client.get("/priorities/feed?tier=high", headers=headers)
            results['get_feed'].append(time.perf_counter() - start)
            
            # Simulated think time
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
    except Exception as e:
        results['errors'] += 1
        print(f"Session error: {e}")

async def run_load_test(concurrency):
    print(f"\n--- Testing with Concurrency: {concurrency} ---")
    results = {
        'login': [],
        'get_items': [],
        'get_feed': [],
        'errors': 0
    }
    
    start_time = time.perf_counter()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        tasks = [run_user_session(client, i, results) for i in range(concurrency)]
        await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    total_duration = end_time - start_time
    total_reqs = len(results['login']) + len(results['get_items']) + len(results['get_feed'])
    
    print(f"Total Time: {total_duration:.2f}s")
    print(f"Total Requests: {total_reqs}")
    print(f"Throughput: {total_reqs / total_duration:.2f} req/s")
    print(f"Errors: {results['errors']}")
    
    for key in ['login', 'get_items', 'get_feed']:
        if results[key]:
            avg = statistics.mean(results[key]) * 1000
            p95 = statistics.quantiles(results[key], n=20)[18] * 1000 # 95th percentile
            print(f"  {key:10}: Avg {avg:6.2f}ms, P95 {p95:6.2f}ms")
            
    return {
        'concurrency': concurrency,
        'throughput': total_reqs / total_duration,
        'avg_latency': statistics.mean(results['get_items']) if results['get_items'] else 0,
        'errors': results['errors']
    }

async def main():
    print("Starting Load Simulation...")
    # Add some data first to make it interesting
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        resp = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Adding 100 items for realistic processing...")
        for i in range(100):
            await client.post("/items", headers=headers, json={
                "text": f"Load test item {i}: Need to check this priority report.",
                "source": "Slack" if i % 2 == 0 else "Email"
            })

    final_stats = []
    for c in CONCURRENCY_LEVELS:
        stats = await run_load_test(c)
        final_stats.append(stats)
        await asyncio.sleep(2) # Cooldown
        
    print("\nSimulation Complete.")
    with open("load_stats.json", "w") as f:
        json.dump(final_stats, f)

if __name__ == "__main__":
    asyncio.run(main())
