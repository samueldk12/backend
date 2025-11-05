# 🐦 Projeto 7: Twitter Clone (System Design)

> System design clássico - aparece em 95% das entrevistas de high-level

---

## 📋 Problema

**Descrição:** Design de sistema de microblogging (Twitter) escalável para 500M usuários ativos.

**Requisitos Funcionais:**
1. ✅ Postar tweet (280 caracteres + mídia)
2. ✅ Seguir/deixar de seguir usuários
3. ✅ Timeline (feed pessoal com tweets de quem segue)
4. ✅ Notificações (likes, retweets, menções)
5. ✅ Busca de tweets
6. ✅ Trending topics

**Requisitos Não-Funcionais:**
1. 📊 **Escala**: 500M usuários ativos, 200M tweets/dia
2. ⚡ **Latência**: Timeline <200ms, Post tweet <1s
3. 💪 **Disponibilidade**: 99.99% uptime
4. 🔄 **Consistência**: Eventual consistency OK para timeline

**Estimativas de Escala:**
```
Usuários: 500M ativos/mês, 150M ativos/dia
Tweets: 200M tweets/dia = 2,300 tweets/segundo
Leituras: 100B timeline views/dia = 1.1M views/segundo (read-heavy!)

Razão read/write: 500:1 (muito mais leituras!)

Storage:
- Tweets: 200M/dia * 365 * 5 anos * 300 bytes = 109TB
- Mídia: ~20% têm foto/vídeo → +500TB
- Total: ~600TB em 5 anos

Bandwidth:
- Escrita: 2,300 tweets/s * 300 bytes = 690 KB/s (trivial)
- Leitura: 1.1M views/s * 10 tweets * 300 bytes = 3.3 GB/s (MASSIVO!)
```

---

## 🏗️ High-Level Architecture

```
┌─────────────┐
│   Cliente   │ (Web/Mobile)
└──────┬──────┘
       │
   HTTPS/WSS
       │
┌──────▼──────────────────────────────────────────┐
│         CDN (CloudFlare/Akamai)                  │
│   - Static assets (JS, CSS, images)             │
│   - Avatar cache                                 │
└──────┬──────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────┐
│     Load Balancer (NGINX/ALB)                    │
│   - Round robin                                  │
│   - Health checks                                │
│   - SSL termination                              │
└──────┬──────────────────────────────────────────┘
       │
       ├────────────────┬────────────────┬─────────────────┐
       │                │                │                 │
┌──────▼──────┐  ┌─────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐
│ API Server  │  │ API Server │  │ API Server │  │  WebSocket  │
│  (FastAPI)  │  │  (FastAPI) │  │  (FastAPI) │  │   Server    │
└──────┬──────┘  └──────┬─────┘  └──────┬─────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼─────┐ ┌─────▼──────┐ ┌────▼─────┐
       │  Timeline   │ │   Tweet    │ │  User    │
       │  Service    │ │  Service   │ │ Service  │
       └──────┬──────┘ └──────┬─────┘ └────┬─────┘
              │              │              │
       ┌──────▼──────────────▼──────────────▼─────┐
       │                                           │
┌──────▼──────┐  ┌─────────────┐  ┌─────────────┐ │
│   Redis     │  │  PostgreSQL │  │  Cassandra  │ │
│   Cache     │  │  (Usuarios) │  │   (Tweets)  │ │
└─────────────┘  └─────────────┘  └─────────────┘ │
                                                   │
┌──────────────────────────────────────────────────┘
│
├─> ElasticSearch (Busca de tweets)
├─> Kafka (Event streaming)
├─> S3 (Armazenamento de mídia)
└─> Redis Pub/Sub (Notificações real-time)
```

---

## 🗄️ Database Design

### 1. Schema SQL (PostgreSQL - Usuários e Relações)

```sql
-- Usuários
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    verified BOOLEAN DEFAULT FALSE,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_username (username),
    INDEX idx_email (email)
);

-- Relação de follow (grafo social)
CREATE TABLE follows (
    follower_id BIGINT NOT NULL,
    followee_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (follower_id, followee_id),
    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (followee_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_follower (follower_id),
    INDEX idx_followee (followee_id)
);

-- IMPORTANTE: Atualizar contadores de forma atômica
CREATE OR REPLACE FUNCTION increment_followers()
RETURNS TRIGGER AS $$
BEGIN
    -- Incrementar followers do followee
    UPDATE users SET followers_count = followers_count + 1
    WHERE id = NEW.followee_id;

    -- Incrementar following do follower
    UPDATE users SET following_count = following_count + 1
    WHERE id = NEW.follower_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_followers
AFTER INSERT ON follows
FOR EACH ROW EXECUTE FUNCTION increment_followers();
```

### 2. Schema NoSQL (Cassandra - Tweets)

```sql
-- Cassandra para tweets (alta escrita, particionamento)

-- Tweets por ID (lookup direto)
CREATE TABLE tweets (
    tweet_id UUID PRIMARY KEY,
    user_id BIGINT,
    content TEXT,
    media_urls LIST<TEXT>,
    likes_count INT,
    retweets_count INT,
    replies_count INT,
    created_at TIMESTAMP
);

-- Timeline de usuário (write fanout)
CREATE TABLE user_timeline (
    user_id BIGINT,
    tweet_id UUID,
    author_id BIGINT,
    content TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, created_at, tweet_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- Tweets de um usuário (perfil)
CREATE TABLE user_tweets (
    user_id BIGINT,
    tweet_id UUID,
    content TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, created_at, tweet_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- Likes (para verificar se user já deu like)
CREATE TABLE tweet_likes (
    tweet_id UUID,
    user_id BIGINT,
    created_at TIMESTAMP,
    PRIMARY KEY (tweet_id, user_id)
);

-- User likes (perfil: tweets que user curtiu)
CREATE TABLE user_likes (
    user_id BIGINT,
    tweet_id UUID,
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, created_at, tweet_id)
) WITH CLUSTERING ORDER BY (created_at DESC);
```

**Por que Cassandra para tweets?**
- ✅ Alta escrita (200M tweets/dia)
- ✅ Particionamento automático (sharding)
- ✅ Eventual consistency (OK para timeline)
- ✅ Replicação multi-datacenter
- ✅ Time-series data (ORDER BY created_at DESC)

---

## ⚙️ Core Features Implementation

### 1. Postar Tweet

**Abordagem: Hybrid Fanout (Twitter real)**

```python
from fastapi import FastAPI, Depends
from cassandra.cluster import Cluster
import redis
import uuid
from datetime import datetime

app = FastAPI()

# Cassandra
cassandra = Cluster(['cassandra1', 'cassandra2']).connect('twitter')

# Redis
redis_client = redis.Redis(host='redis', port=6379)

# Kafka
from kafka import KafkaProducer
kafka_producer = KafkaProducer(bootstrap_servers=['kafka:9092'])


CELEBRITY_THRESHOLD = 5000  # >5k followers = celebrity


@app.post("/tweets")
async def post_tweet(
    user_id: int,
    content: str,
    media_urls: List[str] = None
):
    """
    Postar tweet

    Estratégia Hybrid Fanout:
    1. Salvar tweet no Cassandra
    2. Se author tem <5k followers: PUSH (fanout na escrita)
    3. Se author tem >5k followers: PULL (fanout na leitura)
    """
    # 1. Validar
    if len(content) > 280:
        raise HTTPException(400, "Tweet too long")

    # 2. Criar tweet
    tweet_id = uuid.uuid4()
    created_at = datetime.utcnow()

    query = """
        INSERT INTO tweets (tweet_id, user_id, content, media_urls,
                           likes_count, retweets_count, replies_count, created_at)
        VALUES (?, ?, ?, ?, 0, 0, 0, ?)
    """

    cassandra.execute(query, (tweet_id, user_id, content, media_urls, created_at))

    # 3. Salvar no user_tweets (perfil do autor)
    query = """
        INSERT INTO user_tweets (user_id, tweet_id, content, created_at)
        VALUES (?, ?, ?, ?)
    """
    cassandra.execute(query, (user_id, tweet_id, content, created_at))

    # 4. Fanout (assíncrono via Kafka)
    user = get_user(user_id)

    if user.followers_count < CELEBRITY_THRESHOLD:
        # PUSH: Fanout para followers (background)
        kafka_producer.send('tweet_fanout', {
            'tweet_id': str(tweet_id),
            'user_id': user_id,
            'content': content,
            'created_at': created_at.isoformat()
        })
    else:
        # PULL: Não fazer fanout, será buscado on-demand
        pass

    # 5. Invalidar cache
    redis_client.delete(f"timeline:{user_id}")

    return {
        "tweet_id": str(tweet_id),
        "status": "posted",
        "fanout": "push" if user.followers_count < CELEBRITY_THRESHOLD else "pull"
    }


# Worker assíncrono (Celery/Kafka Consumer)
def fanout_worker():
    """
    Worker que faz fanout de tweets para followers

    Consome mensagens do Kafka
    """
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        'tweet_fanout',
        bootstrap_servers=['kafka:9092']
    )

    for message in consumer:
        data = message.value

        tweet_id = data['tweet_id']
        user_id = data['user_id']
        content = data['content']
        created_at = datetime.fromisoformat(data['created_at'])

        # Buscar followers (paginar se muitos)
        followers = get_followers(user_id, limit=5000)

        # Inserir tweet no timeline de cada follower
        for follower_id in followers:
            query = """
                INSERT INTO user_timeline (user_id, tweet_id, author_id, content, created_at)
                VALUES (?, ?, ?, ?, ?)
            """
            cassandra.execute(query, (follower_id, tweet_id, user_id, content, created_at))

        print(f"✓ Fanout concluído: {tweet_id} para {len(followers)} followers")
```

**Por que Hybrid Fanout?**

| Tipo | Usuários Normais (<5k) | Celebridades (>5k) |
|------|------------------------|-------------------|
| **Estratégia** | PUSH (write fanout) | PULL (read fanout) |
| **Quando escreve** | Fanout para todos followers | Não fazer fanout |
| **Quando lê** | Buscar timeline pré-calculada | Buscar tweets de followees |
| **Trade-off** | Escrita lenta, leitura rápida | Escrita rápida, leitura lenta |

**Exemplo:**
```
User normal (@john, 500 followers):
  - Posta tweet → Fanout para 500 timelines (2-3s)
  - Followers leem timeline → Instantâneo (já calculado)

Celebrity (@elonmusk, 150M followers):
  - Posta tweet → SEM fanout (instantâneo!)
  - Followers leem timeline → Buscar tweets de Elon on-demand
```

---

### 2. Timeline (Home Feed)

```python
@app.get("/timeline")
async def get_timeline(
    user_id: int,
    limit: int = 20,
    cursor: str = None
):
    """
    Buscar timeline (home feed)

    Estratégia Hybrid:
    1. Buscar tweets pré-calculados (PUSH)
    2. Buscar tweets de celebridades (PULL)
    3. Merge e ordenar por tempo
    """
    # 1. Verificar cache
    cache_key = f"timeline:{user_id}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # 2. Buscar tweets pré-calculados (write fanout)
    query = """
        SELECT tweet_id, author_id, content, created_at
        FROM user_timeline
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """
    pre_computed_tweets = cassandra.execute(query, (user_id, limit))

    # 3. Buscar celebridades que o user segue
    celebrity_followees = get_celebrity_followees(user_id)

    # 4. Buscar tweets recentes de celebridades (read fanout)
    celebrity_tweets = []

    for celebrity_id in celebrity_followees:
        query = """
            SELECT tweet_id, user_id, content, created_at
            FROM user_tweets
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        """
        tweets = cassandra.execute(query, (celebrity_id,))
        celebrity_tweets.extend(tweets)

    # 5. Merge e ordenar por created_at
    all_tweets = list(pre_computed_tweets) + celebrity_tweets
    all_tweets.sort(key=lambda t: t.created_at, reverse=True)

    # 6. Limitar e paginar
    result = all_tweets[:limit]

    # 7. Enriquecer com dados de user (avatar, nome)
    enriched = enrich_with_user_data(result)

    # 8. Cachear (5 minutos)
    redis_client.setex(cache_key, 300, json.dumps(enriched))

    return enriched


def get_celebrity_followees(user_id: int) -> List[int]:
    """
    Retornar IDs de celebridades que user segue

    Celebridade = followers_count > 5000
    """
    query = """
        SELECT followee_id
        FROM follows
        WHERE follower_id = ?
    """
    followees = db.execute(query, (user_id,))

    # Filtrar celebridades (verificar no cache)
    celebrities = []

    for (followee_id,) in followees:
        # Cache: celebrity:{user_id} = true/false
        is_celebrity = redis_client.get(f"celebrity:{followee_id}")

        if is_celebrity == b'true':
            celebrities.append(followee_id)

    return celebrities
```

**Complexidade:**
- Pre-computed tweets: O(1) - já estão na tabela user_timeline
- Celebrity tweets: O(C * log N) - C=num celebridades seguidas (~5-10)
- Merge: O(N log N) - N=tweets totais (~100)
- **Total: O(1) na prática** (C e N são pequenos)

---

### 3. Like Tweet (Atomic Counter)

```python
@app.post("/tweets/{tweet_id}/like")
async def like_tweet(tweet_id: str, user_id: int):
    """
    Curtir tweet

    Operações atômicas para evitar race conditions
    """
    tweet_uuid = uuid.UUID(tweet_id)

    # 1. Verificar se já curtiu (idempotência)
    query = """
        SELECT user_id FROM tweet_likes
        WHERE tweet_id = ? AND user_id = ?
    """
    existing = cassandra.execute(query, (tweet_uuid, user_id))

    if existing.one():
        return {"status": "already_liked"}

    # 2. Adicionar like
    query = """
        INSERT INTO tweet_likes (tweet_id, user_id, created_at)
        VALUES (?, ?, ?)
    """
    cassandra.execute(query, (tweet_uuid, user_id, datetime.utcnow()))

    # 3. Incrementar contador (LWT - Lightweight Transaction para atomicidade)
    query = """
        UPDATE tweets
        SET likes_count = likes_count + 1
        WHERE tweet_id = ?
    """
    cassandra.execute(query, (tweet_uuid,))

    # 4. Salvar em user_likes (para página "Tweets que curti")
    query = """
        INSERT INTO user_likes (user_id, tweet_id, created_at)
        VALUES (?, ?, ?)
    """
    cassandra.execute(query, (user_id, tweet_uuid, datetime.utcnow()))

    # 5. Notificação assíncrona (Kafka)
    kafka_producer.send('notifications', {
        'type': 'like',
        'tweet_id': tweet_id,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat()
    })

    return {"status": "liked", "tweet_id": tweet_id}
```

---

### 4. Busca de Tweets (ElasticSearch)

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(['es1', 'es2', 'es3'])


# Indexar tweet quando é criado
def index_tweet(tweet_id: str, user_id: int, content: str, created_at: datetime):
    """Indexar tweet no ElasticSearch"""
    doc = {
        'tweet_id': tweet_id,
        'user_id': user_id,
        'content': content,
        'created_at': created_at.isoformat()
    }

    es.index(index='tweets', id=tweet_id, document=doc)


@app.get("/search")
async def search_tweets(
    query: str,
    limit: int = 20,
    from_: int = 0
):
    """
    Buscar tweets

    ElasticSearch para full-text search
    """
    search_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["content^2", "user.display_name"],  # Boost content
                "fuzziness": "AUTO"  # Tolerância a typos
            }
        },
        "sort": [
            {"created_at": {"order": "desc"}}
        ],
        "from": from_,
        "size": limit
    }

    results = es.search(index='tweets', body=search_query)

    tweets = [hit['_source'] for hit in results['hits']['hits']]

    return {
        "tweets": tweets,
        "total": results['hits']['total']['value']
    }
```

---

### 5. Notificações Real-Time (WebSocket + Redis Pub/Sub)

```python
from fastapi import WebSocket
from typing import Dict, Set

class ConnectionManager:
    """Gerenciar conexões WebSocket"""

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

    async def send_to_user(self, user_id: int, message: dict):
        """Enviar notificação para user"""
        if user_id in self.active_connections:
            disconnected = set()

            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.add(websocket)

            # Limpar conexões mortas
            self.active_connections[user_id] -= disconnected


manager = ConnectionManager()


@app.websocket("/ws/notifications/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket para notificações real-time"""
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Manter conexão aberta (heartbeat)
            await websocket.receive_text()
    except:
        manager.disconnect(websocket, user_id)


# Worker de notificações (Kafka Consumer)
async def notification_worker():
    """
    Consumir notificações do Kafka e enviar via WebSocket

    Suporta múltiplos servidores via Redis Pub/Sub
    """
    from kafka import KafkaConsumer

    consumer = KafkaConsumer('notifications', bootstrap_servers=['kafka:9092'])

    # Redis Pub/Sub para multi-server
    redis_pubsub = redis_client.pubsub()

    for message in consumer:
        notification = message.value

        user_id = notification['user_id']
        type_ = notification['type']

        # Enviar para user local
        await manager.send_to_user(user_id, notification)

        # Enviar para outros servidores (via Redis Pub/Sub)
        redis_client.publish(f"notifications:{user_id}", json.dumps(notification))
```

---

## 📊 Otimizações Críticas

### 1. Caching Strategy

```python
"""
Multi-layer cache:

L1: Application Cache (em memória, 1-5s TTL)
L2: Redis (distributed, 5min-1h TTL)
L3: Database (source of truth)
"""

# L1: Application cache
from functools import lru_cache

@lru_cache(maxsize=10000)
def get_user_cached(user_id: int):
    """Cache em memória (rápido mas não compartilhado)"""
    return get_user_from_db(user_id)


# L2: Redis cache
def get_timeline_cached(user_id: int):
    """Cache distribuído (compartilhado entre servidores)"""
    key = f"timeline:{user_id}"

    # Tentar cache
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)

    # Cache miss
    timeline = generate_timeline(user_id)

    # Cachear (5 minutos)
    redis_client.setex(key, 300, json.dumps(timeline))

    return timeline
```

### 2. Rate Limiting

```python
from redis import Redis

def rate_limit(user_id: int, action: str, limit: int, window: int) -> bool:
    """
    Rate limiting com Redis (sliding window)

    Args:
        user_id: ID do usuário
        action: Ação (ex: "post_tweet", "follow")
        limit: Máximo de ações no window
        window: Janela em segundos

    Limites sugeridos:
    - Post tweet: 50/hora
    - Follow: 100/dia
    - Like: 1000/dia
    """
    key = f"rate_limit:{user_id}:{action}"
    now = time.time()

    # Remover ações antigas (fora do window)
    redis_client.zremrangebyscore(key, 0, now - window)

    # Contar ações no window
    count = redis_client.zcard(key)

    if count >= limit:
        return False  # Rate limited!

    # Adicionar ação atual
    redis_client.zadd(key, {str(now): now})
    redis_client.expire(key, window)

    return True
```

### 3. Sharding Strategy

```python
"""
Cassandra: Auto-sharding por partition key

user_timeline: Shard por user_id
  - User 1-10M → Node 1
  - User 10M-20M → Node 2
  - User 20M-30M → Node 3

tweets: Shard por tweet_id (UUID)
  - Distribuição uniforme
  - Sem hotspots
"""

# PostgreSQL: Manual sharding (se necessário)
def get_db_shard(user_id: int) -> str:
    """Retornar shard de DB baseado em user_id"""
    shard_count = 8
    shard_id = user_id % shard_count

    return f"postgresql://db{shard_id}.example.com/twitter"
```

---

## 🎯 Trade-offs e Decisões

### 1. Cassandra vs PostgreSQL

| Característica | Cassandra | PostgreSQL |
|---------------|-----------|------------|
| **Write throughput** | 🟢 Muito alto | 🟡 Médio |
| **Queries complexas** | 🔴 Limitado | 🟢 Excelente |
| **Joins** | ❌ Não suporta | ✅ Suporta |
| **Escalabilidade** | 🟢 Linear | 🟡 Vertical |
| **Consistência** | 🟡 Eventual | 🟢 Strong |

**Decisão:**
- Cassandra: Tweets (alta escrita, time-series)
- PostgreSQL: Usuários e relações (queries complexas, joins)

### 2. Push vs Pull vs Hybrid

| Estratégia | Escrita | Leitura | Melhor para |
|-----------|---------|---------|-------------|
| **Push** | 🔴 Lenta | 🟢 Rápida | Usuários normais |
| **Pull** | 🟢 Rápida | 🔴 Lenta | Celebridades |
| **Hybrid** | 🟡 Média | 🟡 Média | **Twitter real** |

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Como você lida com hot users (Elon Musk com 150M followers)?"

**Você:** "Hybrid fanout: Usuários com >5k followers não fazem write fanout. Quando alguém lê timeline, buscamos tweets de celebridades on-demand (pull). Isso evita escrever em 150M timelines, mas adiciona latência na leitura. Trade-off aceitável porque celebridades são minoria (<1% usuários)."

---

**Interviewer:** "Como garantir ordem correta no timeline com multiple data centers?"

**Você:** "Clock skew é problema real. Soluções:
1. **Vector clocks**: Cada DC tem relógio lógico
2. **Snowflake IDs**: ID com timestamp + DC_ID + sequence
3. **NTP sync**: Manter todos servers sincronizados (<10ms)

Twitter usa Snowflake IDs (64-bit): 41 bits timestamp + 10 bits machine + 12 bits sequence"

---

**Interviewer:** "Como fazer busca de tweets escalável?"

**Você:** "ElasticSearch cluster com sharding:
- Index por dia (tweets_2024_01_01, tweets_2024_01_02...)
- Shard por hash(tweet_id)
- Replica factor 2-3
- Query apenas últimos 7 dias por padrão
- Archive logs antigos para S3 (cold storage)"

---

## ✅ Checklist da Entrevista

- [ ] Estimar escala (QPS, storage, bandwidth)
- [ ] Desenhar arquitetura high-level
- [ ] Definir schema (SQL + NoSQL)
- [ ] Explicar fanout strategy (push/pull/hybrid)
- [ ] Implementar timeline generation
- [ ] Discutir caching (multi-layer)
- [ ] Rate limiting
- [ ] Busca (ElasticSearch)
- [ ] Notificações real-time (WebSocket)
- [ ] Sharding e replicação
- [ ] Trade-offs e bottlenecks

---

**System design fundamental para entrevistas! 🐦**
