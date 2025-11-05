# 05 - Performance e Concorrência

## Índice

1. [Caching Strategies](#caching-strategies)
2. [Load Balancing](#load-balancing)
3. [Rate Limiting](#rate-limiting)
4. [Database Optimization](#database-optimization)

---

## Caching Strategies

### Cache-Aside (Lazy Loading)

```python
import redis

cache = redis.Redis()

def get_user(user_id):
    # 1. Tenta cache
    cached = cache.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    # 2. Cache miss: busca DB
    user = db.query(User).get(user_id)

    # 3. Salva no cache
    cache.setex(f"user:{user_id}", 3600, json.dumps(user))

    return user
```

### Write-Through

```python
def update_user(user_id, data):
    # 1. Atualiza DB
    db.query(User).filter_by(id=user_id).update(data)
    db.commit()

    # 2. Atualiza cache
    cache.setex(f"user:{user_id}", 3600, json.dumps(data))
```

### Write-Behind (Write-Back)

```python
def update_user(user_id, data):
    # 1. Atualiza cache primeiro (rápido!)
    cache.setex(f"user:{user_id}", 3600, json.dumps(data))

    # 2. Queue para atualizar DB depois
    task_queue.enqueue(update_db, user_id, data)
```

### Cache Invalidation

```python
# Time-based
cache.setex("key", 3600, value)  # Expira em 1h

# Event-based
def delete_user(user_id):
    db.delete(user_id)
    cache.delete(f"user:{user_id}")  # Invalida cache

# Cache stampede prevention
import asyncio

locks = {}

async def get_with_lock(key):
    if key in locks:
        # Espera o primeiro terminar
        await locks[key].wait()
        return cache.get(key)

    # Primeiro a pegar
    locks[key] = asyncio.Event()

    value = await fetch_from_db(key)
    cache.set(key, value)

    locks[key].set()  # Libera waiters
    del locks[key]

    return value
```

---

## Load Balancing

### Round Robin

```python
servers = ["server1", "server2", "server3"]
current = 0

def get_server():
    global current
    server = servers[current]
    current = (current + 1) % len(servers)
    return server

# Request 1 → server1
# Request 2 → server2
# Request 3 → server3
# Request 4 → server1 (volta ao início)
```

### Least Connections

```python
class LoadBalancer:
    def __init__(self):
        self.servers = {
            "server1": 0,  # conexões ativas
            "server2": 0,
            "server3": 0,
        }

    def get_server(self):
        # Retorna servidor com menos conexões
        return min(self.servers, key=self.servers.get)

    def release(self, server):
        self.servers[server] -= 1
```

### Sticky Sessions

```python
# Nginx config
upstream backend {
    ip_hash;  # Mesmo IP → mesmo servidor
    server backend1.example.com;
    server backend2.example.com;
}
```

---

## Rate Limiting

### Token Bucket

```python
import time

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens/second
        self.last_refill = time.time()

    def consume(self, tokens=1):
        # Refill tokens
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

        # Consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False  # Rate limit exceeded

# Uso
limiter = TokenBucket(capacity=100, refill_rate=10)  # 10 req/s

if limiter.consume():
    # Process request
    pass
else:
    # Return 429 Too Many Requests
    raise HTTPException(status_code=429)
```

### Sliding Window (Redis)

```python
import redis
import time

def is_rate_limited(user_id, max_requests=100, window=60):
    """100 requests por 60 segundos"""
    key = f"rate_limit:{user_id}"
    now = time.time()

    # Remove requests antigas
    cache.zremrangebyscore(key, 0, now - window)

    # Conta requests no window
    count = cache.zcard(key)

    if count >= max_requests:
        return True  # Rate limited

    # Adiciona request atual
    cache.zadd(key, {now: now})
    cache.expire(key, window)

    return False
```

---

## Database Optimization

### Connection Pooling

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=20,          # Pool fixo
    max_overflow=10,       # +10 em pico
    pool_timeout=30,       # Timeout
    pool_pre_ping=True,    # Testa conexão antes
)
```

### Query Optimization

```python
# ❌ N+1 queries
users = session.query(User).all()
for user in users:
    print(user.posts)  # Query por user!

# ✅ Eager loading
from sqlalchemy.orm import selectinload

users = session.query(User).options(
    selectinload(User.posts)
).all()

# ✅ Aggregate
from sqlalchemy import func

counts = session.query(
    User.id,
    func.count(Post.id)
).outerjoin(Post).group_by(User.id).all()
```

### Read Replicas

```python
# Master para writes
engine_master = create_engine(MASTER_URL)

# Replicas para reads
engine_replica = create_engine(REPLICA_URL)

def get_user(user_id):
    # Read from replica
    with Session(engine_replica) as session:
        return session.query(User).get(user_id)

def update_user(user_id, data):
    # Write to master
    with Session(engine_master) as session:
        user = session.query(User).get(user_id)
        user.update(data)
        session.commit()
```

---

## Profiling

### Python cProfile

```python
import cProfile
import pstats

def minha_funcao():
    # Código a profiler
    pass

# Profiler
cProfile.run('minha_funcao()', 'stats.prof')

# Análise
p = pstats.Stats('stats.prof')
p.sort_stats('cumulative').print_stats(10)
```

### APM (Application Performance Monitoring)

```python
# New Relic, Datadog, etc.
import newrelic.agent

@newrelic.agent.background_task()
def processar_task():
    # Task é monitorada automaticamente
    pass
```

---

## Próximo Módulo

➡️ [06 - Filas e Streaming](../06-filas-streaming/README.md)
