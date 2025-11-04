# Guia de Debugging e Troubleshooting

> Técnicas e ferramentas para debugar problemas em aplicações backend.

---

## 📚 Índice

1. [Debugging Básico](#1-debugging-básico)
2. [Performance Issues](#2-performance-issues)
3. [Memory Leaks](#3-memory-leaks)
4. [Database Problems](#4-database-problems)
5. [Network Issues](#5-network-issues)
6. [Production Debugging](#6-production-debugging)
7. [Tools e Ferramentas](#7-tools-e-ferramentas)

---

## 1. Debugging Básico

### 1.1 Print Debugging (Básico mas Eficaz)

```python
# ✅ BOM - Structured logging
import logging

logger = logging.getLogger(__name__)

def process_order(order_id):
    logger.info(f"Processing order", extra={"order_id": order_id})

    order = get_order(order_id)
    logger.debug(f"Order fetched", extra={"order": order})

    # ... processing

    logger.info(f"Order processed successfully", extra={"order_id": order_id})


# ❌ RUIM - Print statements
def process_order(order_id):
    print(f"Processing {order_id}")  # Desorganizado
    # ...
```

### 1.2 Python Debugger (pdb)

```python
# Inserir breakpoint
import pdb; pdb.set_trace()  # Python < 3.7
breakpoint()  # Python 3.7+

# Comandos úteis:
# n (next)      - Próxima linha
# s (step)      - Entrar em função
# c (continue)  - Continuar até próximo breakpoint
# l (list)      - Mostrar código
# p var         - Print variável
# pp var        - Pretty print
# w (where)     - Stack trace
# q (quit)      - Sair
```

### 1.3 IPython Debugger (ipdb) - RECOMENDADO

```python
# pip install ipdb

import ipdb; ipdb.set_trace()

# Benefícios vs pdb:
# - Autocomplete
# - Syntax highlighting
# - History
```

### 1.4 VS Code Debug

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true
        }
    ]
}

// Usar breakpoints visuais (F9)
// F5 para debug, F10 (step over), F11 (step into)
```

---

## 2. Performance Issues

### 2.1 Identificar Gargalos

```python
# Usar cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Código a ser analisado
result = slow_function()

profiler.disable()

# Analisar resultados
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 funções mais lentas

# Resultado:
#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#        10    0.020    0.002    0.500    0.050 slow_function
#       100    0.480    0.005    0.480    0.005 database_query  ← Gargalo!
```

### 2.2 Line Profiler (Linha por Linha)

```python
# pip install line_profiler

from line_profiler import LineProfiler

lp = LineProfiler()
lp.add_function(my_function)
lp.run('my_function()')
lp.print_stats()

# Output:
# Line #      Hits         Time  Per Hit   % Time  Line Contents
# ====================================================================
#      1                                           def my_function():
#      2        10       1000.0    100.0     10.0      x = expensive_op()
#      3        10       9000.0    900.0     90.0      y = very_slow()  ← Gargalo!
```

### 2.3 Memory Profiler

```python
# pip install memory_profiler

from memory_profiler import profile

@profile
def my_function():
    data = [i for i in range(1000000)]  # Aloca muita memória
    return sum(data)

my_function()

# Output:
# Line #    Mem usage    Increment   Line Contents
# ================================================
#      3     50.0 MiB     0.0 MiB   def my_function():
#      4     88.2 MiB    38.2 MiB       data = [...]  ← Usa 38MB!
```

### 2.4 Debugging Slow Queries

```python
# Middleware para log de queries lentas
from fastapi import Request
import time

@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    start = time.time()

    response = await call_next(request)

    duration = time.time() - start

    if duration > 1.0:  # > 1 segundo
        logger.warning(
            "Slow request",
            extra={
                "path": request.url.path,
                "method": request.method,
                "duration": duration
            }
        )

    return response
```

---

## 3. Memory Leaks

### 3.1 Detectar Memory Leaks

```python
# Usar tracemalloc (built-in)
import tracemalloc

tracemalloc.start()

# Snapshot antes
snapshot1 = tracemalloc.take_snapshot()

# Executar código suspeito
for i in range(1000):
    create_users()  # Suspeita de leak

# Snapshot depois
snapshot2 = tracemalloc.take_snapshot()

# Comparar
top_stats = snapshot2.compare_to(snapshot1, 'lineno')

print("Top 10 memory increases:")
for stat in top_stats[:10]:
    print(stat)

# Output:
# /app/models.py:45: size=50.0 MiB (+50.0 MiB), count=1000 (+1000)
#     user = User(...)  ← Leak aqui!
```

### 3.2 Causas Comuns

```python
# ❌ PROBLEMA 1: Referências circulares
class Node:
    def __init__(self):
        self.next = None

a = Node()
b = Node()
a.next = b
b.next = a  # Ciclo! GC vai limpar eventualmente, mas demora

# ✅ SOLUÇÃO: Usar weakref
import weakref

class Node:
    def __init__(self):
        self._next = None

    @property
    def next(self):
        return self._next() if self._next else None

    @next.setter
    def next(self, node):
        self._next = weakref.ref(node) if node else None


# ❌ PROBLEMA 2: Closures mantendo referências
def create_handlers():
    data = [0] * 1_000_000  # 1M elementos

    def handler():
        return len(data)  # Mantém data na memória!

    return handler

# ✅ SOLUÇÃO: Não capturar grandes objetos
def create_handlers():
    data_len = len([0] * 1_000_000)

    def handler():
        return data_len  # Apenas inteiro

    return handler


# ❌ PROBLEMA 3: Caches sem limite
cache = {}  # Cresce infinitamente!

# ✅ SOLUÇÃO: LRU Cache com limite
from functools import lru_cache

@lru_cache(maxsize=1000)  # Máximo 1000 items
def get_user(user_id):
    # ...
```

---

## 4. Database Problems

### 4.1 Debugging Queries Lentas

```sql
-- PostgreSQL: Encontrar queries lentas
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

```python
# SQLAlchemy: Log queries
import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Output:
# INFO sqlalchemy.engine SELECT users.id, users.name FROM users WHERE users.id = 1
# INFO sqlalchemy.engine (1,)
```

### 4.2 EXPLAIN ANALYZE

```python
from sqlalchemy import text

# Ver plano de execução
result = db.execute(text("""
    EXPLAIN ANALYZE
    SELECT * FROM users
    WHERE email = 'joao@example.com'
"""))

for row in result:
    print(row)

# Output:
# Seq Scan on users  (cost=0.00..10.75 rows=1 width=100) (actual time=0.020..0.045 rows=1 loops=1)
#   Filter: (email = 'joao@example.com'::text)
# Planning Time: 0.123 ms
# Execution Time: 0.067 ms

# ⚠️ "Seq Scan" = Full table scan (lento!)
# ✅ "Index Scan" = Usando index (rápido!)
```

### 4.3 Detectar N+1 Queries

```python
# Middleware para contar queries
from contextvars import ContextVar

query_count = ContextVar('query_count', default=0)

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    count = query_count.get()
    query_count.set(count + 1)

@app.middleware("http")
async def count_queries(request: Request, call_next):
    query_count.set(0)

    response = await call_next(request)

    count = query_count.get()
    if count > 10:
        logger.warning(f"N+1 detected? {count} queries in {request.url.path}")

    return response
```

---

## 5. Network Issues

### 5.1 Debugging API Calls

```python
# Usar httpx com logging
import httpx
import logging

logging.basicConfig(level=logging.DEBUG)

async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/users")

# Output (mostra todos os detalhes):
# DEBUG httpx._client Opening connection to https://api.example.com
# DEBUG httpx._client Sending request GET /users
# DEBUG httpx._client Response status: 200
```

### 5.2 Timeouts

```python
# ✅ BOM - Sempre definir timeouts
import httpx

async with httpx.AsyncClient(timeout=5.0) as client:  # 5s timeout
    try:
        response = await client.get("https://slow-api.com/data")
    except httpx.TimeoutException:
        logger.error("Request timeout!")
        # Fallback ou retry


# ❌ RUIM - Sem timeout
async with httpx.AsyncClient() as client:  # Timeout infinito!
    response = await client.get("https://slow-api.com/data")  # Pode travar
```

### 5.3 Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),  # Max 3 tentativas
    wait=wait_exponential(multiplier=1, min=1, max=10)  # Backoff exponencial
)
async def call_external_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()

# Tentativas:
# 1ª: Falha → aguarda 1s
# 2ª: Falha → aguarda 2s
# 3ª: Falha → raise exception
```

---

## 6. Production Debugging

### 6.1 Structured Logging

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Log com context
logger.info(
    "user_created",
    user_id=123,
    email="joao@example.com",
    ip="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

# Output JSON (fácil de parsear):
{
    "event": "user_created",
    "level": "info",
    "timestamp": "2025-01-15T10:30:00",
    "user_id": 123,
    "email": "joao@example.com",
    "ip": "192.168.1.1"
}
```

### 6.2 Error Tracking (Sentry)

```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,  # 100% das transactions
    environment="production"
)

# Capturar exceptions automaticamente
@app.get("/users/{user_id}")
def get_user(user_id: int):
    try:
        user = db.query(User).get(user_id)
        return user
    except Exception as e:
        sentry_sdk.capture_exception(e)  # Envia para Sentry
        raise

# Adicionar contexto
with sentry_sdk.configure_scope() as scope:
    scope.user = {"id": user_id, "email": user.email}
    scope.set_tag("api_version", "v1")
    scope.set_extra("request_id", request_id)
```

### 6.3 Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Instrumentar FastAPI
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(__name__)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Criar span
    with tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user_id", user_id)

        # Buscar do DB (span filho)
        with tracer.start_as_current_span("db_query"):
            user = await db.get(user_id)

        # Buscar posts (span filho)
        with tracer.start_as_current_span("get_posts"):
            posts = await get_posts(user_id)

        return {"user": user, "posts": posts}

# Jaeger UI mostra timeline completo:
# ┌─ get_user (200ms) ────────────────────────────┐
# │  ┌─ db_query (100ms) ──┐                      │
# │  └──────────────────────┘                      │
# │                          ┌─ get_posts (90ms) ─┤
# │                          └────────────────────┘│
# └───────────────────────────────────────────────┘
```

---

## 7. Tools e Ferramentas

### 7.1 Monitoring Stack

```
Logs:        ELK Stack (Elasticsearch, Logstash, Kibana)
Metrics:     Prometheus + Grafana
Tracing:     Jaeger / Zipkin
Errors:      Sentry / Rollbar
APM:         New Relic / DataDog
```

### 7.2 Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

# Métricas
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    with request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).time():
        response = await call_next(request)

    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 7.3 Health Checks

```python
@app.get("/health/live")
def liveness():
    """Liveness probe: app está rodando?"""
    return {"status": "ok"}

@app.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe: app está pronta para receber tráfego?"""
    try:
        # Verificar DB
        db.execute(text("SELECT 1"))

        # Verificar Redis
        redis_client.ping()

        return {"status": "ready", "checks": {"db": "ok", "redis": "ok"}}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}, 503
```

---

## 🔍 Troubleshooting Checklist

### API está lenta

```
1. ✅ Verificar logs de slow requests
2. ✅ Analisar queries com EXPLAIN ANALYZE
3. ✅ Verificar N+1 queries
4. ✅ Profile com cProfile
5. ✅ Verificar cache hit rate
6. ✅ Verificar connection pooling
7. ✅ Analisar spans no Jaeger
```

### Memory usage crescendo

```
1. ✅ Usar tracemalloc para identificar leak
2. ✅ Verificar closures
3. ✅ Verificar caches sem limite
4. ✅ Verificar referências circulares
5. ✅ Profile com memory_profiler
```

### Database lento

```
1. ✅ EXPLAIN ANALYZE nas queries
2. ✅ Verificar indexes
3. ✅ Verificar N+1 queries
4. ✅ Analisar pg_stat_statements
5. ✅ Verificar connection pool size
6. ✅ Verificar locks (pg_locks)
```

### API retornando 500

```
1. ✅ Verificar logs (Sentry)
2. ✅ Verificar stack trace
3. ✅ Verificar se DB está up
4. ✅ Verificar se Redis está up
5. ✅ Verificar environment variables
6. ✅ Verificar migrations aplicadas
```

---

## 💡 Boas Práticas

### DO ✅

- Log com structured logging (JSON)
- Sempre definir timeouts em API calls
- Usar Sentry para error tracking
- Monitorar com Prometheus/Grafana
- Profile antes de otimizar
- Usar tracing em microservices
- Health checks (liveness + readiness)
- Circuit breakers para APIs externas

### DON'T ❌

- Usar print() em produção
- Deixar debug=True em produção
- Ignorar warnings
- Otimizar sem medir
- Deixar código de debug no commit
- Log de passwords/secrets
- Catch exception genérico sem log

---

## 🎓 Recursos

- [Python Debugging with pdb](https://docs.python.org/3/library/pdb.html)
- [cProfile Documentation](https://docs.python.org/3/library/profile.html)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

---

**Lembre-se:** Debugging é uma habilidade. Quanto mais você pratica, melhor fica! 🐛🔍
