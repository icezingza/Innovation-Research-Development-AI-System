import asyncio
import httpx
import time
import statistics
import sys
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor

# Constants
BASE_URL = "http://127.0.0.1:8085"
TOTAL_REQUESTS = 1000
CONCURRENCY = 100 # Adjust concurrency to prevent local port exhaustion

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

async def register_and_login():
    """Register a tenant and get JWT for the stress test."""
    print(f"{CYAN}Initializing Test Tenant...{RESET}")
    tenant_name = f"StressTest Corp {int(time.time())}"
    admin_email = f"stress@{int(time.time())}.com"
    password = "SovereignPass123!"

    async with httpx.AsyncClient() as client:
        # 1. Register
        try:
            reg_resp = await client.post(
                f"{BASE_URL}/tenants",
                json={
                    "name": tenant_name,
                    "domain": f"stress{int(time.time())}.com",
                    "tier": "enterprise",
                    "admin_email": admin_email,
                    "admin_password": password
                },
                headers={"X-API-Key": "dev-api-key"}
            )
            
            if reg_resp.status_code not in (200, 201):
                print(f"{RED}Failed to register tenant: {reg_resp.text}{RESET}")
                return None, None
            
            tenant_id = reg_resp.json()["id"]
            
            # 2. Login
            login_resp = await client.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": admin_email,
                    "password": password,
                    "tenant_id": tenant_id
                }
            )
            
            if login_resp.status_code == 200:
                token = login_resp.json()["access_token"]
                print(f"{GREEN}Test Tenant Ready (ID: {tenant_id}){RESET}")
                return tenant_id, token
            else:
                print(f"{RED}Login failed: {login_resp.text}{RESET}")
                return None, None
        except Exception as e:
            print(f"{RED}Error initializing tenant: {e}{RESET}")
            return None, None

async def worker(worker_id: int, queue: asyncio.Queue, token: str, stats: list):
    """Worker processing tasks from the queue."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        while True:
            try:
                task_id = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
            start_time = time.time()
            try:
                # Dispatch valid task
                resp = await client.post(
                    f"{BASE_URL}/research/tasks",
                    json={
                        "question": f"Load testing AI query #{task_id} with parallel execution.",
                        "constraints": ["Fast response"]
                    },
                    headers=headers
                )
                latency = time.time() - start_time
                status = resp.status_code
                
                # Check circuit breaker tripping (Rate Limit / Service Unavailable)
                if status == 429:
                    error_msg = "Rate Limited"
                elif status == 503:
                    error_msg = "Circuit Breaker Tripped (503)"
                elif status >= 500:
                    error_msg = f"Server Error {status}"
                else:
                    error_msg = None
                    
                stats.append({"task_id": task_id, "latency": latency, "status": status, "error": error_msg})
            except Exception as e:
                latency = time.time() - start_time
                stats.append({"task_id": task_id, "latency": latency, "status": 0, "error": str(e)})
            finally:
                queue.task_done()
                # Simple progress reporting
                if len(stats) % 100 == 0:
                    sys.stdout.write(f"\r{CYAN}Processed {len(stats)}/{TOTAL_REQUESTS} requests...{RESET}")
                    sys.stdout.flush()

async def run_stress_test():
    print(f"\n{BOLD}===================================================================={RESET}")
    print(f"{BOLD}   NAMONEXUS DISTRIBUTED LOAD SIMULATION (NRE v5.0.0){RESET}")
    print(f"{BOLD}===================================================================={RESET}")
    
    # 0. Clean old db
    if os.path.exists("cognition_sim.db"):
        try:
            os.remove("cognition_sim.db")
        except:
            pass

    # 1. Start Server
    print(f"{CYAN}Starting FastAPI server in background on port 8085...{RESET}")
    env = os.environ.copy()
    env["SQLITE_URL"] = "sqlite+aiosqlite:///cognition_sim.db"
    env["ENABLE_API_KEY_AUTH"] = "false" # skip platform key for tenant creation
    
    # Start the server using uvicorn
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8085"],
        stdout=open("stress_server.log", "w"),
        stderr=subprocess.STDOUT,
        env=env
    )
    
    print(f"{CYAN}Waiting 10 seconds for uvicorn to initialize...{RESET}")
    time.sleep(10)
    
    print(f"Targeting: {BASE_URL}")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Concurrency Limit: {CONCURRENCY}")
    
    # 2. Setup Tenant
    tenant_id, token = await register_and_login()
    
    print(f"\n{YELLOW}[Phase 1/2] Bombarding System with {TOTAL_REQUESTS} requests...{RESET}")
    
    # 2. Setup Queue & Workers
    queue = asyncio.Queue()
    for i in range(TOTAL_REQUESTS):
        queue.put_nowait(i)
        
    stats = []
    start_time = time.time()
    
    workers = [
        asyncio.create_task(worker(i, queue, token, stats)) 
        for i in range(CONCURRENCY)
    ]
    
    await asyncio.gather(*workers)
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\n\n{GREEN}[Phase 2/2] Stress Test Complete! Generating Report...{RESET}\n")
    
    # 3. Analyze Results
    successes = [s for s in stats if s["status"] in (200, 202)]
    rate_limits = [s for s in stats if s["status"] == 429]
    circuit_trips = [s for s in stats if s["status"] == 503]
    errors = [s for s in stats if s["status"] not in (200, 202, 429, 503)]
    
    latencies = [s["latency"] for s in successes]
    
    print(f"{BOLD}--- PERFORMANCE METRICS ---{RESET}")
    print(f"Total Time:      {total_time:.2f} seconds")
    print(f"Throughput:      {TOTAL_REQUESTS / total_time:.2f} req/sec")
    
    if latencies:
        print(f"Avg Latency:     {statistics.mean(latencies):.4f} sec")
        print(f"Min Latency:     {min(latencies):.4f} sec")
        print(f"Max Latency:     {max(latencies):.4f} sec")
        if len(latencies) > 1:
            print(f"Latency P95:     {statistics.quantiles(latencies, n=100)[94]:.4f} sec")
    
    print(f"\n{BOLD}--- CIRCUIT BREAKER & RATE LIMITS ---{RESET}")
    print(f"Successful Req:  {GREEN}{len(successes)}{RESET} (Tasks Accepted)")
    print(f"Rate Limited:    {YELLOW}{len(rate_limits)}{RESET} (Redis Token Bucket Guardrail)")
    print(f"Circuit Tripped: {RED}{len(circuit_trips)}{RESET} (Load Shedding Active)")
    print(f"Other Errors:    {RED}{len(errors)}{RESET}")
    
    # 4. Check API Gateway Health post-stress
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{BASE_URL}/health")
            if health.status_code == 200:
                print(f"\n{BOLD}Post-Test Health:{RESET} {GREEN}SYSTEM IS STABLE AND RECOVERED!{RESET}")
            else:
                print(f"\n{BOLD}Post-Test Health:{RESET} {RED}SYSTEM IS DEGRADED ({health.status_code}){RESET}")
        except Exception:
            print(f"\n{BOLD}Post-Test Health:{RESET} {RED}SYSTEM CRASHED / UNREACHABLE!{RESET}")
            
    print(f"\n{CYAN}Shutting down server...{RESET}")
    server_process.terminate()
    server_process.wait()
    print(f"{GREEN}Done.{RESET}")

if __name__ == "__main__":
    # Windows event loop fix for aiohttp/httpx closing bugs
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_stress_test())
