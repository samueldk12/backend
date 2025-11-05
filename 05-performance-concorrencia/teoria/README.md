# Módulo 05 - Performance e Concorrência

## 🎯 Objetivo

Otimizar aplicações para alta performance e gerenciar concorrência de forma eficiente.

---

## 📚 Tópicos Principais

### 1. Threading vs Multiprocessing vs Async

**Regra de Ouro:**
```python
# CPU-bound → Multiprocessing
with ProcessPoolExecutor() as executor:
    results = executor.map(heavy_computation, data)

# I/O-bound → Async/Await
async with aiohttp.ClientSession() as session:
    results = await asyncio.gather(*[fetch(session, url) for url in urls])

# I/O-bound (lib síncrona) → Threading
with ThreadPoolExecutor() as executor:
    results = executor.map(requests.get, urls)
```

### 2. Connection Pooling

```python
# ❌ Ruim: Nova conexão a cada request
def get_user(user_id):
    db = create_connection()  # Lento!
    user = db.query(User).get(user_id)
    db.close()
    return user

# ✅ Bom: Pool de conexões reutilizadas
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # 20 conexões permanentes
    max_overflow=10,       # Até 30 no total
    pool_pre_ping=True     # Valida antes de usar
)
```

### 3. Caching Strategies

**Cache-Aside (Lazy Loading):**
```python
def get_user(user_id):
    # 1. Tentar cache
    cached = redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    # 2. Cache miss → buscar DB
    user = db.query(User).get(user_id)

    # 3. Salvar no cache
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))

    return user
```

**Write-Through:**
```python
def update_user(user_id, data):
    # 1. Atualizar DB
    user = db.query(User).get(user_id)
    user.update(data)
    db.commit()

    # 2. Atualizar cache imediatamente
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))
```

**Cache Invalidation:**
```python
# Padrão: TTL (Time To Live)
redis.setex("key", 3600, value)  # Expira em 1 hora

# Invalidação manual
def delete_user(user_id):
    db.delete(user)
    redis.delete(f"user:{user_id}")  # Limpar cache
```

### 4. Database Query Optimization

```python
# ❌ N+1 Problem
users = db.query(User).all()
for user in users:
    posts = db.query(Post).filter_by(user_id=user.id).all()  # N queries!

# ✅ Eager Loading
users = db.query(User).options(joinedload(User.posts)).all()  # 1 query!

# ✅ Pagination (Cursor-based)
posts = db.query(Post) \
    .filter(Post.id > last_id) \
    .order_by(Post.id) \
    .limit(20) \
    .all()

# ❌ Evite: OFFSET em páginas grandes
posts = db.query(Post).offset(10000).limit(20)  # Lê 10020 linhas!
```

### 5. Async FastAPI

```python
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

app = FastAPI()

# Async database
async_engine = create_async_engine("postgresql+asyncpg://...")

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

# Async external API calls
import aiohttp

@app.get("/external-data")
async def get_external():
    async with aiohttp.ClientSession() as session:
        tasks = [
            session.get("https://api1.com/data"),
            session.get("https://api2.com/data"),
            session.get("https://api3.com/data"),
        ]
        responses = await asyncio.gather(*tasks)
        return [await r.json() for r in responses]
```

### 6. Load Balancing

```nginx
# Nginx Load Balancer
upstream backend {
    least_conn;  # Estratégia: menos conexões
    server backend1:8000 weight=3;
    server backend2:8000 weight=2;
    server backend3:8000 weight=1;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
```

**Estratégias:**
- **Round Robin**: Distribui igualmente
- **Least Connections**: Servidor com menos conexões
- **IP Hash**: Mesmo cliente → mesmo servidor (sticky sessions)
- **Weighted**: Servidores mais potentes recebem mais

### 7. Rate Limiting

```python
from fastapi import FastAPI, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.get("/api/data")
@limiter.limit("5/minute")  # 5 requests por minuto
async def get_data(request: Request):
    return {"data": "..."}

# Rate limit com Redis (distribuído)
import redis
from datetime import datetime, timedelta

def rate_limit(user_id: str, max_requests: int = 100, window: int = 3600):
    key = f"rate_limit:{user_id}"
    current = redis.get(key)

    if current and int(current) >= max_requests:
        raise HTTPException(429, "Rate limit exceeded")

    redis.incr(key)
    if not current:
        redis.expire(key, window)
```

### 8. Profiling

```python
# cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Código a ser analisado
result = expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 funções mais lentas

# Line profiler
from line_profiler import LineProfiler

lp = LineProfiler()
lp.add_function(my_function)
lp.run('my_function()')
lp.print_stats()

# Memory profiler
from memory_profiler import profile

@profile
def my_function():
    data = [i for i in range(1000000)]
    return sum(data)
```

### 9. Benchmarking

```python
import time
from functools import wraps

def benchmark(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper

@benchmark
def slow_function():
    time.sleep(1)
    return "done"

# Benchmarking com pytest-benchmark
def test_my_function(benchmark):
    result = benchmark(my_function, arg1, arg2)
    assert result == expected
```

---

## 🎓 Checklist de Performance

### Database:
- [ ] Indexes em colunas de busca/join
- [ ] Evitar N+1 queries
- [ ] Connection pooling configurado
- [ ] Queries analisadas com EXPLAIN
- [ ] Paginação cursor-based

### Caching:
- [ ] Redis para dados frequentes
- [ ] TTL apropriado
- [ ] Estratégia de invalidação
- [ ] Cache warming para dados críticos

### API:
- [ ] Async/await onde possível
- [ ] Rate limiting implementado
- [ ] Response compression (gzip/brotli)
- [ ] HTTP caching headers

### Infrastructure:
- [ ] Load balancer configurado
- [ ] Auto-scaling habilitado
- [ ] CDN para assets estáticos
- [ ] Health checks configurados

---

## 📊 Números de Referência

```
Latência típica:
- L1 cache:           0.5 ns
- L2 cache:           7 ns
- RAM:                100 ns
- SSD:                150 μs
- Network (mesma DC): 500 μs
- HDD:                10 ms
- Network (cross-DC): 150 ms

Throughput esperado:
- FastAPI (async):    10k-20k req/s
- PostgreSQL:         10k-40k reads/s
- Redis:              100k+ ops/s
- Nginx:              50k-100k req/s
```

---

## 📝 Próximos Passos

1. Exemplos em [`../exemplos/`](../exemplos/)
2. Exercícios em [`../exercicios/`](../exercicios/)
3. Avance para **[Módulo 06 - Filas e Streaming](../../06-filas-streaming/teoria/README.md)**
