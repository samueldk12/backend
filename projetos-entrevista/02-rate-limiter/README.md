# 🚦 Projeto 2: Rate Limiter

> Proteção contra abuse de APIs - aparece em 80% das entrevistas de backend

---

## 📋 Problema

**Descrição:** Implementar rate limiter para proteger APIs contra abuse.

**Exemplo:**
```
Regra: Máximo 100 requests por minuto

Request 1-100: ✅ Allow
Request 101:   ❌ 429 Too Many Requests (retry after 60s)
```

---

## 🎯 Requisitos

### Funcionais
1. ✅ Limitar requests por usuário/IP
2. ✅ Diferentes limites por endpoint
3. ✅ Retornar `429 Too Many Requests` quando exceder
4. ✅ Headers informativos:
   - `X-RateLimit-Limit`: Limite total
   - `X-RateLimit-Remaining`: Quantos restam
   - `X-RateLimit-Reset`: Quando reseta (timestamp)

### Não-funcionais
1. **Baixa latência**: <10ms overhead
2. **Distribuído**: Funcionar com múltiplos servidores
3. **Fault-tolerant**: Se rate limiter cair, permitir requests (fail-open)
4. **Escalável**: Milhões de usuários

---

## 🔧 Algoritmos de Rate Limiting

### 1. Token Bucket (Recomendado!)

**Como funciona:**
- Bucket com N tokens
- Cada request consome 1 token
- Tokens são adicionados a taxa constante
- Se não tem token: rate limited

```python
import time
from typing import Optional

class TokenBucket:
    """
    Token Bucket Algorithm

    Exemplo: 10 requests/segundo
    - Bucket size: 10 tokens
    - Refill rate: 10 tokens/segundo

    Permite bursts (10 requests imediatos)
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Tamanho do bucket (max requests instantâneos)
            refill_rate: Tokens por segundo
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    def allow_request(self, tokens_needed: int = 1) -> bool:
        """
        Verificar se pode fazer request

        Returns:
            True se permitido, False se rate limited
        """
        # Refill tokens baseado no tempo passado
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

        # Consumir tokens
        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True

        return False


# Uso
bucket = TokenBucket(capacity=10, refill_rate=10)  # 10 req/s

for i in range(15):
    if bucket.allow_request():
        print(f"Request {i+1}: ✅ Allowed")
    else:
        print(f"Request {i+1}: ❌ Rate Limited")

# Output:
# Request 1-10: ✅ Allowed (usa todos os tokens)
# Request 11-15: ❌ Rate Limited (sem tokens)
```

**Vantagens:**
- ✅ Permite bursts (flexibilidade)
- ✅ Fácil de entender
- ✅ Memory efficient

**Usado por:** Amazon API Gateway, Stripe

---

### 2. Leaky Bucket

```python
from collections import deque
import time

class LeakyBucket:
    """
    Leaky Bucket: requests vazam a taxa constante

    Como uma fila FIFO com leak rate
    """

    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.queue = deque()
        self.leak_rate = leak_rate
        self.last_leak = time.time()

    def allow_request(self) -> bool:
        # Vazar requests antigos
        now = time.time()
        elapsed = now - self.last_leak
        leaks = int(elapsed * self.leak_rate)

        for _ in range(leaks):
            if self.queue:
                self.queue.popleft()

        self.last_leak = now

        # Adicionar request se cabe
        if len(self.queue) < self.capacity:
            self.queue.append(now)
            return True

        return False
```

**Vantagens:**
- ✅ Output rate constante (smooth)

**Desvantagens:**
- ❌ Não permite bursts
- ❌ Usa mais memória (queue)

---

### 3. Fixed Window Counter

```python
import time
from collections import defaultdict

class FixedWindowCounter:
    """
    Fixed Window: divide tempo em janelas fixas

    Exemplo: 100 req/minuto
    - 12:00:00-12:00:59 → conta até 100
    - 12:01:00-12:01:59 → reset, conta até 100
    """

    def __init__(self, limit: int, window_size: int):
        """
        Args:
            limit: Max requests por janela
            window_size: Tamanho da janela em segundos
        """
        self.limit = limit
        self.window_size = window_size
        self.windows = defaultdict(int)

    def allow_request(self, user_id: str) -> bool:
        now = int(time.time())
        window_key = now // self.window_size  # Janela atual

        key = f"{user_id}:{window_key}"

        if self.windows[key] < self.limit:
            self.windows[key] += 1
            return True

        return False

    def cleanup_old_windows(self):
        """Limpar janelas antigas (evitar memory leak)"""
        now = int(time.time())
        current_window = now // self.window_size

        # Remover janelas >2 períodos atrás
        keys_to_delete = [
            k for k in self.windows.keys()
            if int(k.split(':')[1]) < current_window - 2
        ]

        for key in keys_to_delete:
            del self.windows[key]


# Uso
limiter = FixedWindowCounter(limit=10, window_size=60)  # 10 req/min

user_id = "user123"
for i in range(15):
    if limiter.allow_request(user_id):
        print(f"Request {i+1}: ✅")
    else:
        print(f"Request {i+1}: ❌")
```

**Problema: Edge case**
```
12:00:50 → 10 requests ✅
12:01:01 → 10 requests ✅
Total: 20 requests em 11 segundos! (burst)
```

---

### 4. Sliding Window Log

```python
import time
from collections import deque

class SlidingWindowLog:
    """
    Mantém log de timestamps de requests

    Mais preciso que Fixed Window
    """

    def __init__(self, limit: int, window_size: int):
        self.limit = limit
        self.window_size = window_size
        self.logs = {}  # user_id -> deque of timestamps

    def allow_request(self, user_id: str) -> bool:
        now = time.time()

        if user_id not in self.logs:
            self.logs[user_id] = deque()

        # Remover requests fora da janela
        while self.logs[user_id] and self.logs[user_id][0] < now - self.window_size:
            self.logs[user_id].popleft()

        # Verificar limite
        if len(self.logs[user_id]) < self.limit:
            self.logs[user_id].append(now)
            return True

        return False


# Uso
limiter = SlidingWindowLog(limit=10, window_size=60)

user_id = "user123"
for i in range(15):
    if limiter.allow_request(user_id):
        print(f"✅ Request {i+1}")
    else:
        print(f"❌ Request {i+1}")
```

**Vantagens:**
- ✅ Mais preciso (sliding window)
- ✅ Sem edge case do Fixed Window

**Desvantagens:**
- ❌ Usa mais memória (log de timestamps)

---

### 5. Sliding Window Counter (Hybrid)

```python
class SlidingWindowCounter:
    """
    Híbrido: Fixed Window + Sliding Window

    Calcula interpolação entre janelas
    Mais eficiente em memória que Sliding Log
    """

    def __init__(self, limit: int, window_size: int):
        self.limit = limit
        self.window_size = window_size
        self.windows = {}  # user_id -> {window_id: count}

    def allow_request(self, user_id: str) -> bool:
        now = time.time()
        current_window = int(now // self.window_size)
        previous_window = current_window - 1

        if user_id not in self.windows:
            self.windows[user_id] = {}

        # Limpar janelas antigas
        self.windows[user_id] = {
            w: c for w, c in self.windows[user_id].items()
            if w >= previous_window
        }

        # Calcular requests na janela sliding
        previous_count = self.windows[user_id].get(previous_window, 0)
        current_count = self.windows[user_id].get(current_window, 0)

        # Interpolação: quanto da janela anterior ainda conta?
        elapsed_in_current = now - current_window * self.window_size
        weight = 1 - (elapsed_in_current / self.window_size)

        estimated_count = previous_count * weight + current_count

        if estimated_count < self.limit:
            self.windows[user_id][current_window] = current_count + 1
            return True

        return False
```

**Vantagens:**
- ✅ Preciso como Sliding Log
- ✅ Memory efficient como Fixed Window

**Usado por:** Cloudflare

---

## 🏗️ Implementação Distribuída (Redis)

### Redis-based Rate Limiter

```python
import redis
import time
from typing import Optional

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)


class RedisRateLimiter:
    """
    Rate limiter distribuído com Redis

    Funciona com múltiplos servidores
    """

    def __init__(self, limit: int, window_size: int):
        self.limit = limit
        self.window_size = window_size

    def allow_request(self, user_id: str) -> dict:
        """
        Verificar se request é permitida

        Returns:
            {
                "allowed": bool,
                "limit": int,
                "remaining": int,
                "reset": int (timestamp)
            }
        """
        now = int(time.time())
        window_key = now // self.window_size
        key = f"rate_limit:{user_id}:{window_key}"

        # Incrementar contador atomicamente
        current = redis_client.incr(key)

        # Primeira vez: setar TTL
        if current == 1:
            redis_client.expire(key, self.window_size * 2)  # TTL 2x window

        # Calcular reset time
        reset_time = (window_key + 1) * self.window_size

        # Verificar limite
        allowed = current <= self.limit

        return {
            "allowed": allowed,
            "limit": self.limit,
            "remaining": max(0, self.limit - current),
            "reset": reset_time
        }


# Uso
limiter = RedisRateLimiter(limit=100, window_size=60)

result = limiter.allow_request("user123")

if result["allowed"]:
    print("✅ Request allowed")
    print(f"Remaining: {result['remaining']}")
else:
    print("❌ Rate limited")
    print(f"Reset in: {result['reset'] - int(time.time())} seconds")
```

---

### Redis Lua Script (Atomic)

```python
# rate_limit.lua
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- Remover requests fora da janela
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- Contar requests na janela
local current = redis.call('ZCARD', key)

if current < limit then
    -- Adicionar request
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window)
    return {1, limit - current - 1}
else
    return {0, 0}
end
"""


class RedisLuaRateLimiter:
    """Rate limiter usando Lua script (atomic)"""

    def __init__(self, limit: int, window_size: int):
        self.limit = limit
        self.window_size = window_size
        self.script = redis_client.register_script(RATE_LIMIT_SCRIPT)

    def allow_request(self, user_id: str) -> dict:
        now = time.time()
        key = f"rate_limit:{user_id}"

        # Executar script atomicamente
        result = self.script(
            keys=[key],
            args=[self.limit, self.window_size, now]
        )

        allowed = bool(result[0])
        remaining = result[1]

        return {
            "allowed": allowed,
            "remaining": remaining
        }
```

---

## 🎯 FastAPI Integration

```python
# middleware/rate_limiter.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import time

app = FastAPI()

limiter = RedisRateLimiter(limit=100, window_size=60)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware global de rate limiting

    Aplica a TODAS as rotas
    """

    # Identificar usuário (IP ou user_id)
    user_id = request.client.host  # IP address

    # Se autenticado, usar user_id
    # user = await get_current_user(request)
    # if user:
    #     user_id = f"user:{user.id}"

    # Verificar rate limit
    result = limiter.allow_request(user_id)

    if not result["allowed"]:
        # 429 Too Many Requests
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "retry_after": result["reset"] - int(time.time())
            },
            headers={
                "X-RateLimit-Limit": str(result["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(result["reset"]),
                "Retry-After": str(result["reset"] - int(time.time()))
            }
        )

    # Request permitida
    response = await call_next(request)

    # Adicionar headers informativos
    response.headers["X-RateLimit-Limit"] = str(result["limit"])
    response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
    response.headers["X-RateLimit-Reset"] = str(result["reset"])

    return response


# Rate limiting por endpoint
from fastapi import Depends

def rate_limit(limit: int, window: int):
    """
    Decorator para rate limiting específico

    @router.post("/expensive", dependencies=[Depends(rate_limit(10, 60))])
    """
    limiter = RedisRateLimiter(limit=limit, window_size=window)

    async def check_rate_limit(request: Request):
        user_id = request.client.host

        result = limiter.allow_request(user_id)

        if not result["allowed"]:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(result["reset"] - int(time.time()))
                }
            )

    return check_rate_limit


# Uso
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/expensive-operation", dependencies=[Depends(rate_limit(10, 60))])
def expensive_operation():
    """Limitado a 10 requests por minuto"""
    return {"message": "Operation completed"}


@router.post("/normal-operation")
def normal_operation():
    """Usa rate limit global (100/min)"""
    return {"message": "Operation completed"}
```

---

## 📊 Comparação de Algoritmos

| Algoritmo | Memória | Precisão | Bursts | Complexidade | Usado Por |
|-----------|---------|----------|--------|--------------|-----------|
| **Token Bucket** | O(1) | Alta | ✅ Sim | Baixa | AWS, Stripe |
| **Leaky Bucket** | O(n) | Alta | ❌ Não | Média | Nginx |
| **Fixed Window** | O(1) | Baixa | ⚠️ Edge | Baixa | Simples |
| **Sliding Log** | O(n) | Muito Alta | ✅ Sim | Alta | Preciso |
| **Sliding Counter** | O(1) | Alta | ✅ Sim | Média | Cloudflare |

**Recomendação:**
- **Geral**: Token Bucket (balance entre tudo)
- **Strict**: Sliding Window Counter
- **Simples**: Fixed Window Counter

---

## 🧪 Testes

```python
import pytest
import time

def test_token_bucket_allows_up_to_capacity():
    bucket = TokenBucket(capacity=10, refill_rate=10)

    # Primeiras 10: permitidas
    for i in range(10):
        assert bucket.allow_request() == True

    # 11ª: negada
    assert bucket.allow_request() == False


def test_token_bucket_refills_over_time():
    bucket = TokenBucket(capacity=10, refill_rate=10)

    # Esgotar tokens
    for _ in range(10):
        bucket.allow_request()

    # Aguardar 0.5s (5 tokens refill)
    time.sleep(0.5)

    # Próximas 5: permitidas
    for i in range(5):
        assert bucket.allow_request() == True

    # 6ª: negada
    assert bucket.allow_request() == False


def test_redis_rate_limiter_distributed():
    limiter = RedisRateLimiter(limit=10, window_size=60)

    user_id = f"test_user_{time.time()}"

    # Primeiras 10: permitidas
    for i in range(10):
        result = limiter.allow_request(user_id)
        assert result["allowed"] == True
        assert result["remaining"] == 9 - i

    # 11ª: negada
    result = limiter.allow_request(user_id)
    assert result["allowed"] == False
    assert result["remaining"] == 0
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Como você implementaria rate limiting distribuído?"

**Você:** "Uso Redis como store centralizado. Cada servidor incrementa contador no Redis atomicamente. Para garantir atomicidade, uso Lua script que executa INCR + EXPIRE em uma única operação."

---

**Interviewer:** "E se o Redis cair?"

**Você:** "Fail-open strategy: se Redis não responder, permitir requests ao invés de negar. Rate limiting é proteção, não deve causar downtime. Para alta disponibilidade, uso Redis Cluster com replicação."

---

**Interviewer:** "Token Bucket vs Leaky Bucket?"

**Você:** "Token Bucket permite bursts (bom para UX), usa O(1) memória. Leaky Bucket tem output rate constante (melhor para backend stability), mas usa O(n) memória. Escolho Token Bucket para APIs públicas (permite bursts temporários) e Leaky Bucket para serviços internos críticos."

---

## ✅ Checklist da Entrevista

- [ ] Explicar problema (abuse prevention)
- [ ] Requisitos (limite por user/IP, 429 response)
- [ ] Algoritmos (Token Bucket, Fixed Window, Sliding)
- [ ] Comparação (trade-offs de cada)
- [ ] Implementação distribuída (Redis)
- [ ] Atomicidade (Lua script)
- [ ] Headers (X-RateLimit-*)
- [ ] Fail-open strategy
- [ ] Performance (<10ms overhead)
- [ ] Escalabilidade (Redis Cluster)

---

**Projeto essencial para APIs! 🚦**

Empresas: Stripe, Shopify, Twitter, GitHub, Cloudflare...
