# 🔗 Projeto 1: URL Shortener (Bitly Clone)

> O projeto mais comum em entrevistas de backend (aparece em 70% das empresas)

---

## 📋 Problema

**Descrição:** Construir um serviço de encurtamento de URLs como Bitly.

**Exemplo:**
```
Input:  https://www.example.com/very/long/url/that/needs/shortening
Output: https://short.url/abc123

Quando acessar https://short.url/abc123 → redireciona para URL original
```

---

## 🎯 Requisitos

### Funcionais
1. ✅ Dado URL longo, retornar URL curto (6-8 caracteres)
2. ✅ Dado URL curto, redirecionar para URL longo
3. ✅ URLs expiram após X dias (opcional)
4. ✅ URLs customizadas: `short.url/google` → `https://google.com`
5. ✅ Analytics: quantas vezes foi acessado

### Não-funcionais
1. **Disponibilidade**: 99.9% uptime
2. **Latência**: <100ms para redirect
3. **Escalabilidade**: 100M URLs criadas, 10B redirects/mês
4. **Durabilidade**: URLs não podem ser perdidos

---

## 📐 Estimativas (Back-of-envelope)

### Traffic
- **Writes (criar URL)**: 100M/mês = ~40 URLs/s
- **Reads (redirects)**: 10B/mês = ~4000 redirects/s
- **Read:Write ratio**: 100:1

### Storage
- Cada URL: ~500 bytes (URL longo + short + metadata)
- 100M URLs/mês * 500 bytes = **50GB/mês**
- 5 anos: 50GB * 12 * 5 = **3TB**

### Bandwidth
- Writes: 40 URLs/s * 500 bytes = **20KB/s**
- Reads: 4000 req/s * 500 bytes = **2MB/s**

---

## 🔧 Low-Level Design (Implementação)

### 1. Geração de Short URL

#### Abordagem A: Hash (MD5, SHA256)

```python
import hashlib

def generate_short_url_hash(long_url: str) -> str:
    """
    Usa hash do URL longo

    Prós: Determinístico (mesmo URL = mesmo short)
    Contras: Colisões, não é shortest possible
    """
    # MD5 retorna 128 bits = 32 caracteres hex
    hash_full = hashlib.md5(long_url.encode()).hexdigest()

    # Pegar primeiros 6 caracteres
    short_code = hash_full[:6]

    # Problema: Colisões!
    # Se já existe, incrementar: abc123 → abc124

    return short_code


# Problema com colisões
def handle_collision(short_code: str, db) -> str:
    """Se short_code já existe, tentar próximo"""
    original = short_code
    counter = 0

    while db.exists(short_code):
        counter += 1
        short_code = f"{original}{counter}"

    return short_code
```

**Análise:**
- ✅ Mesmo URL sempre gera mesmo short (cache-friendly)
- ❌ Colisões são comuns (birthday paradox)
- ❌ Tamanho não é mínimo

---

#### Abordagem B: Base62 Encoding (Melhor!)

```python
import random
import string

class Base62:
    """
    Base62: [a-zA-Z0-9] = 62 caracteres

    6 caracteres = 62^6 = 56 bilhões de combinações
    7 caracteres = 62^7 = 3.5 trilhões de combinações
    """

    ALPHABET = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    BASE = len(ALPHABET)  # 62

    @classmethod
    def encode(cls, num: int) -> str:
        """
        Converte número para base62

        Exemplo: 12345 → 3d7
        """
        if num == 0:
            return cls.ALPHABET[0]

        result = []
        while num > 0:
            result.append(cls.ALPHABET[num % cls.BASE])
            num //= cls.BASE

        return ''.join(reversed(result))

    @classmethod
    def decode(cls, code: str) -> int:
        """
        Converte base62 para número

        Exemplo: 3d7 → 12345
        """
        num = 0
        for char in code:
            num = num * cls.BASE + cls.ALPHABET.index(char)
        return num


# Como usar
def generate_short_url_base62(url_id: int) -> str:
    """
    Usa ID incremental do banco

    url_id=1 → a
    url_id=62 → ba
    url_id=12345 → 3d7
    """
    return Base62.encode(url_id)


# Exemplo
url_id = 12345
short_code = generate_short_url_base62(url_id)
print(f"ID {url_id} → {short_code}")  # 3d7
print(f"{short_code} → {Base62.decode(short_code)}")  # 12345
```

**Vantagens:**
- ✅ Sem colisões (cada ID é único)
- ✅ Shortest possible (62^6 = 56B combinações)
- ✅ Reversível (short → ID → buscar no DB)

**Decisão:** Use Base62 com auto-increment ID!

---

#### Abordagem C: Random + Verificação

```python
import secrets

def generate_random_short() -> str:
    """
    Gera código aleatório

    Prós: Não previsível (segurança)
    Contras: Precisa verificar colisão
    """
    length = 6
    alphabet = string.ascii_letters + string.digits

    # secrets.choice é criptograficamente seguro
    short_code = ''.join(secrets.choice(alphabet) for _ in range(length))

    return short_code


def create_short_url_random(long_url: str, db) -> str:
    """Tentar até achar código único"""
    max_attempts = 5

    for _ in range(max_attempts):
        short_code = generate_random_short()

        if not db.exists(short_code):
            db.save(short_code, long_url)
            return short_code

    raise Exception("Could not generate unique short URL")
```

**Quando usar:**
- Custom URLs (usuário escolhe)
- Segurança (não quer que seja previsível)

---

### 2. Database Schema

```python
# models.py
from sqlalchemy import Column, String, Integer, DateTime, Index
from datetime import datetime, timedelta

class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Short code (6-8 caracteres)
    short_code = Column(String(10), unique=True, nullable=False, index=True)

    # URL original
    long_url = Column(String(2048), nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Expiração opcional

    # Analytics
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)

    # User (opcional)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Índices importantes
    __table_args__ = (
        Index('ix_short_code', 'short_code'),  # Busca por short_code
        Index('ix_expires_at', 'expires_at'),  # Cleanup de expirados
    )
```

**Por que esses campos?**
- `short_code`: UNIQUE + INDEX para busca O(1)
- `expires_at`: URLs expiram após X dias
- `access_count`: Analytics simples
- `user_id`: Rastrear quem criou (opcional)

---

### 3. API Implementation

```python
# services/url_service.py
from sqlalchemy.orm import Session
from sqlalchemy import update
from datetime import datetime, timedelta
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)


class URLService:
    def __init__(self, db: Session):
        self.db = db

    def create_short_url(
        self,
        long_url: str,
        custom_code: str = None,
        expires_in_days: int = None
    ) -> dict:
        """
        Criar short URL

        Args:
            long_url: URL para encurtar
            custom_code: Código customizado (opcional)
            expires_in_days: Expiração em dias (opcional)

        Returns:
            {"short_url": "abc123", "long_url": "..."}
        """

        # Validar URL
        if not long_url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        # Verificar se já existe (evitar duplicatas)
        existing = self.db.query(URL).filter(URL.long_url == long_url).first()
        if existing and not existing.expires_at:
            return {
                "short_code": existing.short_code,
                "long_url": existing.long_url,
                "created_at": existing.created_at
            }

        # Gerar short code
        if custom_code:
            # Custom: verificar disponibilidade
            if self.db.query(URL).filter(URL.short_code == custom_code).first():
                raise ValueError(f"Custom code '{custom_code}' already taken")
            short_code = custom_code
        else:
            # Auto: usar ID + base62
            # Placeholder: será atualizado após insert
            short_code = None

        # Calcular expiração
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Criar URL
        url = URL(
            short_code=short_code or "temp",  # Placeholder
            long_url=long_url,
            expires_at=expires_at
        )
        self.db.add(url)
        self.db.flush()  # Obter ID sem commitar

        # Gerar short_code baseado no ID
        if not custom_code:
            url.short_code = Base62.encode(url.id)

        self.db.commit()
        self.db.refresh(url)

        return {
            "short_code": url.short_code,
            "long_url": url.long_url,
            "short_url": f"https://short.url/{url.short_code}",
            "expires_at": url.expires_at
        }


    def get_long_url(self, short_code: str) -> dict:
        """
        Buscar URL original e redirecionar

        Estratégia:
        1. Tentar cache (Redis) - 99% hit rate
        2. Se miss, buscar DB
        3. Cachear resultado
        4. Incrementar contador (async)
        """

        # 1. Tentar cache
        cache_key = f"url:{short_code}"
        cached = redis_client.get(cache_key)

        if cached:
            # Cache hit: incrementar contador (não bloquear)
            self._increment_access_count_async(short_code)
            return {"long_url": cached, "from_cache": True}

        # 2. Cache miss: buscar DB
        url = self.db.query(URL).filter(URL.short_code == short_code).first()

        if not url:
            raise ValueError("Short URL not found")

        # Verificar expiração
        if url.expires_at and url.expires_at < datetime.utcnow():
            raise ValueError("Short URL expired")

        # 3. Cachear (TTL 24h)
        redis_client.setex(cache_key, 86400, url.long_url)

        # 4. Incrementar contador
        self._increment_access_count(url)

        return {"long_url": url.long_url, "from_cache": False}


    def _increment_access_count(self, url: URL):
        """Incrementar contador atomicamente"""
        self.db.execute(
            update(URL)
            .where(URL.id == url.id)
            .values(
                access_count=URL.access_count + 1,
                last_accessed=datetime.utcnow()
            )
        )
        self.db.commit()


    def _increment_access_count_async(self, short_code: str):
        """Incrementar em background (não bloquear redirect)"""
        # Opção 1: Incrementar no Redis, sync para DB periodicamente
        redis_client.incr(f"access_count:{short_code}")

        # Opção 2: Celery task
        # increment_url_counter.delay(short_code)


    def get_analytics(self, short_code: str) -> dict:
        """Buscar analytics de uma URL"""
        url = self.db.query(URL).filter(URL.short_code == short_code).first()

        if not url:
            raise ValueError("Short URL not found")

        return {
            "short_code": url.short_code,
            "long_url": url.long_url,
            "access_count": url.access_count,
            "created_at": url.created_at,
            "last_accessed": url.last_accessed
        }


# routes/urls.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

router = APIRouter()


class CreateURLRequest(BaseModel):
    long_url: HttpUrl
    custom_code: str = None
    expires_in_days: int = None


@router.post("/shorten")
def shorten_url(
    request: CreateURLRequest,
    db: Session = Depends(get_db)
):
    """Criar short URL"""
    service = URLService(db)

    try:
        result = service.create_short_url(
            long_url=str(request.long_url),
            custom_code=request.custom_code,
            expires_in_days=request.expires_in_days
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{short_code}")
def redirect_url(
    short_code: str,
    db: Session = Depends(get_db)
):
    """Redirecionar para URL original"""
    service = URLService(db)

    try:
        result = service.get_long_url(short_code)

        # 301: Permanent redirect (cacheable)
        # 302: Temporary redirect (não cacheable)
        return RedirectResponse(
            url=result["long_url"],
            status_code=301  # ou 302 se quiser analytics precisos
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/{short_code}/stats")
def get_stats(
    short_code: str,
    db: Session = Depends(get_db)
):
    """Ver analytics"""
    service = URLService(db)

    try:
        return service.get_analytics(short_code)
    except ValueError as e:
        raise HTTPException(404, str(e))
```

---

## 🏗️ High-Level Design (Escalabilidade)

### Arquitetura Básica

```
┌─────────┐
│ Client  │
└────┬────┘
     │
     ▼
┌─────────────┐
│ Load        │
│ Balancer    │
└─────┬───────┘
      │
      ▼
┌─────────────┐     ┌──────────┐
│ Web Servers │────>│  Redis   │ (Cache)
│ (FastAPI)   │     │ (99% hit)│
└─────┬───────┘     └──────────┘
      │
      ▼
┌─────────────┐
│ PostgreSQL  │ (Master-Slave)
│ (URLs)      │
└─────────────┘
```

---

### Otimizações para Escala

#### 1. Cache (Redis)

```python
# 99% dos acessos são redirects (reads)
# Cache TUDO em Redis com TTL 24h

def get_long_url_cached(short_code: str) -> str:
    # 1. Redis (1-2ms)
    cached = redis_client.get(f"url:{short_code}")
    if cached:
        return cached

    # 2. DB (10-50ms) - raro
    url = db.query(URL).filter(URL.short_code == short_code).first()
    redis_client.setex(f"url:{short_code}", 86400, url.long_url)

    return url.long_url
```

**Resultado:**
- Latência: 1-2ms (vs 50ms sem cache)
- DB load: redução de 99%

---

#### 2. Database Sharding

```
Quando chegamos em 1B+ URLs, sharding por range:

Shard 1: IDs 1-100M       (short codes: a-ZZZZZ)
Shard 2: IDs 100M-200M    (short codes: 10000-...)
Shard 3: IDs 200M-300M

Como rotear?
Base62.decode(short_code) → ID → shard_id = ID % num_shards
```

---

#### 3. Analytics (Separate Pipeline)

```python
# Problema: Incrementar contador bloqueia redirect
# Solução: Pipeline assíncrono

# 1. Write to Redis (não bloquear)
redis_client.incr(f"access_count:{short_code}")

# 2. Background job: sync Redis → DB (a cada 5min)
@celery_app.task
def sync_analytics_to_db():
    # Ler contadores do Redis
    # Batch update no DB
    # Limpar Redis
    ...
```

---

#### 4. Rate Limiting

```python
# Prevenir abuse: max 10 URLs/hora por IP

from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@router.post("/shorten", dependencies=[Depends(RateLimiter(times=10, hours=1))])
def shorten_url(...):
    ...
```

---

## 🎯 Trade-offs e Decisões

### 1. Encoding: Hash vs Base62 vs Random

| Método | Colisões | Tamanho | Previsível | Decisão |
|--------|----------|---------|------------|---------|
| Hash (MD5) | Sim | Maior | Sim | ❌ Não |
| Base62 | Não | Mínimo | Sim | ✅ **Use** |
| Random | Raro | Médio | Não | ⚠️ Custom URLs |

**Decisão:** Base62 com auto-increment ID

---

### 2. Redirect: 301 vs 302

| Código | Significado | Cache | Analytics | Decisão |
|--------|-------------|-------|-----------|---------|
| 301 | Permanent | Sim (browser) | Impreciso | ❌ Analytics ruins |
| 302 | Temporary | Não | Preciso | ✅ **Use** |

**Decisão:** 302 para analytics precisos (ou 301 + contador no redirect)

---

### 3. Storage: SQL vs NoSQL

| Opção | Prós | Contras | Decisão |
|-------|------|---------|---------|
| PostgreSQL | ACID, relations | Scale vertical | ✅ Start aqui |
| Cassandra | Scale horizontal | Eventual consistency | ⚠️ Se >1B URLs |

**Decisão:** PostgreSQL + sharding (suficiente para 99% dos casos)

---

## 🧪 Testes

```python
# tests/test_url_service.py
def test_create_short_url(db_session):
    service = URLService(db_session)

    result = service.create_short_url("https://example.com/long/url")

    assert result["short_code"] is not None
    assert len(result["short_code"]) <= 8
    assert result["long_url"] == "https://example.com/long/url"


def test_custom_code(db_session):
    service = URLService(db_session)

    result = service.create_short_url(
        "https://google.com",
        custom_code="google"
    )

    assert result["short_code"] == "google"


def test_duplicate_custom_code_fails(db_session):
    service = URLService(db_session)

    service.create_short_url("https://google.com", custom_code="test")

    with pytest.raises(ValueError):
        service.create_short_url("https://example.com", custom_code="test")


def test_redirect_increments_counter(db_session):
    service = URLService(db_session)

    result = service.create_short_url("https://example.com")
    short_code = result["short_code"]

    # Acessar 3 vezes
    for _ in range(3):
        service.get_long_url(short_code)

    analytics = service.get_analytics(short_code)
    assert analytics["access_count"] == 3


def test_expired_url_fails(db_session):
    service = URLService(db_session)

    result = service.create_short_url(
        "https://example.com",
        expires_in_days=-1  # Já expirado
    )

    with pytest.raises(ValueError, match="expired"):
        service.get_long_url(result["short_code"])
```

---

## 📊 Números Finais

### Com otimizações:
- **Latência**: 1-2ms (99% cache hit)
- **Throughput**: 10k+ requests/s por servidor
- **Storage**: 3TB para 5 anos
- **Cost**: $500/mês (3 servers + Redis + RDS)

### Escalabilidade:
- **1B URLs**: Single PostgreSQL + Redis
- **10B URLs**: Sharding (3-5 shards)
- **100B URLs**: Cassandra + Redis

---

## 🎓 Perguntas da Entrevista

**Interviewer:** "Como você evitaria colisões?"

**Você:** "Uso Base62 encoding com auto-increment ID. Como cada ID é único, não há colisões. Se precisar de custom URLs, verifico disponibilidade antes de salvar."

---

**Interviewer:** "E se o DB cair?"

**Você:** "99% dos acessos são redirects (reads), que são servidos do Redis cache. Se DB cair, redirects continuam funcionando. Apenas criar novas URLs falha, que é aceitável temporariamente. Para alta disponibilidade, uso PostgreSQL com replicação Master-Slave."

---

**Interviewer:** "Como você escalaria para 1 bilhão de requests/segundo?"

**Você:** "Com essa escala, precisaríamos:
1. CDN para cache geográfico (Cloudflare)
2. Múltiplos data centers (latência global)
3. Sharding do DB (100+ shards)
4. Redis clusters (replicação)
5. Cassandra para write-heavy workload"

---

## ✅ Checklist da Entrevista

Ao explicar este design, mencione:

- [ ] Requisitos funcionais e não-funcionais
- [ ] Estimativas (QPS, storage, bandwidth)
- [ ] API design (POST /shorten, GET /:code)
- [ ] Database schema
- [ ] Algoritmo de encoding (Base62 > Hash)
- [ ] Cache strategy (Redis, 99% hit rate)
- [ ] Trade-offs (301 vs 302, SQL vs NoSQL)
- [ ] Analytics (async pipeline)
- [ ] Rate limiting (abuse prevention)
- [ ] Escalabilidade (sharding, CDN)

---

**Este é o projeto #1 para dominar! 🚀**

Empresas que pedem: Google, Amazon, Meta, Microsoft, Uber, Stripe, Shopify, Twitter, Netflix...
