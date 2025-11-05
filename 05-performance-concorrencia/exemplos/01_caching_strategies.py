"""
Exemplo: Caching Strategies em Prática

Execute: python 01_caching_strategies.py

Demonstra diferentes estratégias de cache com métricas.
"""

import time
from typing import Optional
import json

# Simular cache em memória
class SimpleCache:
    def __init__(self):
        self.data = {}
        self.ttl = {}

    def get(self, key: str) -> Optional[str]:
        if key in self.ttl and time.time() > self.ttl[key]:
            del self.data[key]
            del self.ttl[key]
            return None
        return self.data.get(key)

    def setex(self, key: str, ttl: int, value: str):
        self.data[key] = value
        self.ttl[key] = time.time() + ttl

    def clear(self):
        self.data.clear()
        self.ttl.clear()

cache = SimpleCache()

# Simular database lento
class SlowDatabase:
    def __init__(self):
        self.query_count = 0
        self.data = {
            1: {"id": 1, "name": "Alice"},
            2: {"id": 2, "name": "Bob"},
        }

    def get_user(self, user_id: int):
        self.query_count += 1
        print(f"  🐌 [DB Query] Fetching user {user_id}... (500ms)")
        time.sleep(0.5)
        return self.data.get(user_id)

db = SlowDatabase()

# Cache-Aside
def cache_aside_get_user(user_id: int):
    key = f"user:{user_id}"
    cached = cache.get(key)
    
    if cached:
        print(f"  ⚡ [CACHE HIT] User {user_id}")
        return json.loads(cached)
    
    print(f"  ❌ [CACHE MISS]")
    user = db.get_user(user_id)
    if user:
        cache.setex(key, 60, json.dumps(user))
    return user

def main():
    print("=" * 50)
    print("🚀 CACHING DEMONSTRATION")
    print("=" * 50)
    
    print("\n1️⃣  First call (cache miss):")
    start = time.time()
    cache_aside_get_user(1)
    print(f"   Time: {time.time() - start:.3f}s")
    
    print("\n2️⃣  Second call (cache hit):")
    start = time.time()
    cache_aside_get_user(1)
    print(f"   Time: {time.time() - start:.3f}s")
    
    print(f"\n📊 DB Queries: {db.query_count}")

if __name__ == "__main__":
    main()
