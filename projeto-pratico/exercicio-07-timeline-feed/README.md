# Exercício 07 - Timeline e Feed Personalizado

> Sistema de feed de rede social: follow/unfollow, algoritmos de ranking, e otimizações de performance.

---

## 📋 Objetivo

Implementar feed personalizado escalável, explorando:
- Sistema de follow/unfollow (relacionamentos)
- Estratégias de feed generation (push, pull, hybrid)
- Algoritmos de ranking (chronological, engagement-based, personalized)
- Otimizações de performance (cache, denormalization, fanout)
- Paginação eficiente para feeds infinitos

---

## 🎯 O Que Vamos Aprender

1. **Feed generation**: Push vs Pull vs Hybrid
2. **Ranking algorithms**: Simple score, engagement-based, ML
3. **Fanout**: Write fanout vs Read fanout
4. **Performance**: Cache em Redis, pre-computação
5. **Many-to-many**: Modelar relacionamentos
6. **Scalability**: Como Twitter, Instagram, Facebook fazem

---

## 📊 Modelagem: Sistema de Follow

### Modelo de Relacionamento

```python
# models.py
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint
from datetime import datetime

class Follow(Base):
    """
    Relacionamento de seguir entre usuários

    user_id = seguidor (follower)
    following_id = seguido (following)

    Exemplo: João segue Maria
    - user_id = João.id
    - following_id = Maria.id
    """
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Follower
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Following
    created_at = Column(DateTime, default=datetime.utcnow)

    # Prevenir duplicatas
    __table_args__ = (
        UniqueConstraint('user_id', 'following_id', name='uq_user_following'),
    )

    # Relationships
    follower = relationship("User", foreign_keys=[user_id], backref="following")
    followed = relationship("User", foreign_keys=[following_id], backref="followers")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)

    # Contadores denormalizados
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)

    # ... outros campos
```

**Queries úteis:**

```python
# Quem João segue?
following = db.query(User).join(
    Follow, Follow.following_id == User.id
).filter(Follow.user_id == joao_id).all()

# Seguidores de João?
followers = db.query(User).join(
    Follow, Follow.user_id == User.id
).filter(Follow.following_id == joao_id).all()

# João segue Maria?
is_following = db.query(Follow).filter(
    Follow.user_id == joao_id,
    Follow.following_id == maria_id
).first() is not None
```

---

## 🔧 Estratégias de Feed Generation

### Abordagem 1: Pull Model (Read Fanout)

**Como funciona:**
- Quando usuário abre feed: **busca posts** de quem ele segue
- Feed gerado em **tempo real** (query no momento)

```python
# services/feed_service.py
class PullFeedService:
    """
    Pull model: gera feed em tempo de leitura

    Vantagens:
    - Simples de implementar
    - Sempre atualizado (dados frescos)
    - Não precisa armazenamento extra

    Desvantagens:
    - Lento se usuário segue muitas pessoas (JOIN pesado)
    - Query complexa
    - Alto custo em leitura
    """

    def get_feed(self, user_id: int, limit: int = 20, offset: int = 0) -> list:
        """Gera feed buscando posts de quem user segue"""

        # Buscar IDs de quem user segue
        following_ids = db.query(Follow.following_id).filter(
            Follow.user_id == user_id
        ).subquery()

        # Buscar posts dessas pessoas
        posts = db.query(Post).options(
            joinedload(Post.author)
        ).filter(
            Post.user_id.in_(following_ids)
        ).order_by(
            Post.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [self._serialize_post(p) for p in posts]
```

**Quando usar:**
- ✅ MVP, poucos usuários
- ✅ Usuários seguem poucas pessoas (<100)
- ❌ NÃO escala para milhões de usuários

---

### Abordagem 2: Push Model (Write Fanout)

**Como funciona:**
- Quando alguém **cria post**: copia para feed de **todos os seguidores**
- Feed já está **pré-computado** (apenas lê)

```python
# models.py
class FeedEntry(Base):
    """
    Feed pré-computado de cada usuário

    Quando João cria post:
    - Para cada seguidor de João
    - Criar FeedEntry(user_id=seguidor, post_id=post)
    """
    __tablename__ = "feed_entries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Dono do feed
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Índice composto para queries eficientes
    __table_args__ = (
        Index('idx_feed_user_created', 'user_id', 'created_at'),
    )

    post = relationship("Post")


# services/feed_service.py
class PushFeedService:
    """
    Push model: gera feed em tempo de escrita

    Vantagens:
    - Leitura muito rápida (feed já pronto)
    - Escala bem para leitura
    - Query simples

    Desvantagens:
    - Escrita lenta se user tem muitos followers (fanout storm)
    - Armazenamento duplicado
    - Celebridades são problema (1M followers = 1M writes)
    """

    def create_post_and_fanout(self, user_id: int, content: str) -> Post:
        """Criar post e distribuir para feed de seguidores"""

        # Criar post
        post = Post(user_id=user_id, content=content)
        db.add(post)
        db.commit()

        # Buscar seguidores
        followers = db.query(Follow.user_id).filter(
            Follow.following_id == user_id
        ).all()

        # Fanout: adicionar ao feed de cada seguidor
        feed_entries = [
            FeedEntry(user_id=follower.user_id, post_id=post.id)
            for follower in followers
        ]

        db.bulk_save_objects(feed_entries)
        db.commit()

        return post


    def get_feed(self, user_id: int, limit: int = 20, offset: int = 0) -> list:
        """Buscar feed (já pré-computado)"""

        entries = db.query(FeedEntry).options(
            joinedload(FeedEntry.post).joinedload(Post.author)
        ).filter(
            FeedEntry.user_id == user_id
        ).order_by(
            FeedEntry.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [self._serialize_post(entry.post) for entry in entries]
```

**Problema: Fanout Storm**

Se celebridade (1M followers) cria post:
- 1M inserts na tabela `feed_entries`
- Pode demorar minutos
- Bloqueia criação do post

**Solução: Background Job**

```python
# tasks/feed_fanout.py
@celery_app.task(name='tasks.fanout_post')
def fanout_post_to_followers(post_id: int):
    """
    Fanout em background com Celery

    Divide followers em batches de 1000
    Processa cada batch em task separada
    """
    post = db.query(Post).filter(Post.id == post_id).first()

    # Buscar followers
    followers = db.query(Follow.user_id).filter(
        Follow.following_id == post.user_id
    ).all()

    # Dividir em batches
    BATCH_SIZE = 1000
    for i in range(0, len(followers), BATCH_SIZE):
        batch = followers[i:i + BATCH_SIZE]
        fanout_batch.delay(post_id, [f.user_id for f in batch])


@celery_app.task(name='tasks.fanout_batch')
def fanout_batch(post_id: int, follower_ids: list):
    """Fanout de um batch de followers"""
    entries = [
        FeedEntry(user_id=follower_id, post_id=post_id)
        for follower_id in follower_ids
    ]

    db.bulk_save_objects(entries)
    db.commit()
```

---

### Abordagem 3: Hybrid (Pull + Push)

**Como funciona:**
- **Push** para usuários normais (<5k followers)
- **Pull** para celebridades (>5k followers)
- Combina vantagens de ambos

```python
# services/feed_service.py
class HybridFeedService:
    """
    Hybrid: Push para usuários normais, Pull para celebridades

    Como Twitter faz:
    - User normal: push para todos os followers
    - Celebrity: followers fazem pull em tempo real
    """

    CELEBRITY_THRESHOLD = 5000  # Followers para ser considerado celebrity

    def create_post(self, user_id: int, content: str) -> Post:
        """Criar post com fanout híbrido"""

        post = Post(user_id=user_id, content=content)
        db.add(post)
        db.commit()

        # Verificar se é celebrity
        author = db.query(User).filter(User.id == user_id).first()

        if author.followers_count < self.CELEBRITY_THRESHOLD:
            # Usuário normal: push para followers
            fanout_post_to_followers.delay(post.id)
        else:
            # Celebrity: não faz fanout (followers fazem pull)
            pass

        return post


    def get_feed(self, user_id: int, limit: int = 20, cursor: Optional[int] = None) -> list:
        """
        Feed híbrido:
        1. Busca feed pré-computado (push)
        2. Merge com posts de celebrities (pull)
        3. Ordena e retorna top N
        """

        # Buscar quem user segue
        following_ids = db.query(Follow.following_id).filter(
            Follow.user_id == user_id
        ).all()
        following_ids = [f.following_id for f in following_ids]

        # Separar normal users vs celebrities
        celebrities = db.query(User.id).filter(
            User.id.in_(following_ids),
            User.followers_count >= self.CELEBRITY_THRESHOLD
        ).all()
        celebrity_ids = [c.id for c in celebrities]

        # 1. Buscar feed pré-computado (usuários normais)
        precomputed_posts = db.query(Post).join(
            FeedEntry, FeedEntry.post_id == Post.id
        ).filter(
            FeedEntry.user_id == user_id
        ).order_by(Post.created_at.desc()).limit(limit * 2).all()

        # 2. Buscar posts recentes de celebrities (pull)
        celebrity_posts = []
        if celebrity_ids:
            celebrity_posts = db.query(Post).filter(
                Post.user_id.in_(celebrity_ids),
                Post.created_at > datetime.utcnow() - timedelta(days=7)  # Últimos 7 dias
            ).order_by(Post.created_at.desc()).limit(limit).all()

        # 3. Merge e ordenar
        all_posts = list(set(precomputed_posts + celebrity_posts))
        all_posts.sort(key=lambda p: p.created_at, reverse=True)

        return all_posts[:limit]
```

**Vantagens:**
- ✅ Escala para usuários normais (push)
- ✅ Escala para celebrities (pull)
- ✅ Melhor de ambos os mundos

**Usado por:** Twitter, Instagram

---

## 📈 Algoritmos de Ranking

### 1. Chronological (Simples)

```python
posts.order_by(Post.created_at.desc())
```

**Prós:** Simples, transparente
**Contras:** Posts bons podem ficar enterrados

---

### 2. Engagement-Based (Intermediário)

```python
def calculate_engagement_score(post: Post) -> float:
    """
    Score baseado em engajamento

    Fatores:
    - Likes (peso 1)
    - Comentários (peso 3, mais valioso)
    - Tempo desde publicação (decay)
    """
    age_hours = (datetime.utcnow() - post.created_at).total_seconds() / 3600

    # Decaimento temporal (posts antigos valem menos)
    time_decay = 1 / (1 + age_hours / 24)  # Decay ao longo de 24h

    # Score
    score = (
        post.likes_count * 1 +
        post.comments_count * 3
    ) * time_decay

    return score


# Buscar e ordenar por score
posts = get_feed_posts(user_id)
posts_with_score = [
    (post, calculate_engagement_score(post))
    for post in posts
]
posts_with_score.sort(key=lambda x: x[1], reverse=True)
ranked_posts = [p[0] for p in posts_with_score]
```

**Prós:** Mostra conteúdo popular
**Contras:** "Rich get richer" (posts populares ficam mais populares)

---

### 3. Personalized (Avançado)

```python
def calculate_personalized_score(post: Post, user: User) -> float:
    """
    Score personalizado baseado em interações passadas

    Fatores:
    - Engajamento geral
    - Afinidade com autor (user interage muito com autor?)
    - Tipo de conteúdo preferido
    """
    base_score = calculate_engagement_score(post)

    # Afinidade: quantas vezes user interagiu com autor?
    author_affinity = get_user_affinity(user.id, post.author.id)

    # Preferência por tipo de conteúdo
    content_preference = 1.0
    if post.has_video and user.prefers_video:
        content_preference = 1.5

    # Score final
    score = base_score * (1 + author_affinity) * content_preference

    return score


def get_user_affinity(user_id: int, author_id: int) -> float:
    """
    Calcula afinidade entre usuário e autor

    Baseado em:
    - Likes em posts do autor
    - Comentários em posts do autor
    - Views de posts do autor
    """
    # Buscar interações dos últimos 30 dias
    likes_count = db.query(func.count(Like.id)).join(Post).filter(
        Like.user_id == user_id,
        Post.user_id == author_id,
        Like.created_at > datetime.utcnow() - timedelta(days=30)
    ).scalar()

    comments_count = db.query(func.count(Comment.id)).join(Post).filter(
        Comment.user_id == user_id,
        Post.user_id == author_id,
        Comment.created_at > datetime.utcnow() - timedelta(days=30)
    ).scalar()

    # Normalizar para [0, 1]
    affinity = min((likes_count * 0.1 + comments_count * 0.3), 1.0)

    return affinity
```

**Prós:** Feed personalizado para cada usuário
**Contras:** Complexo, precisa ML, pode criar "filter bubble"

---

## ⚡ Otimizações de Performance

### 1. Cache em Redis

```python
# services/feed_service.py
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

class CachedFeedService:
    """Feed com cache em Redis"""

    def get_feed(self, user_id: int, limit: int = 20) -> list:
        """Buscar feed com cache"""
        cache_key = f"feed:{user_id}"

        # Tentar cache
        cached = redis_client.get(cache_key)
        if cached:
            posts = json.loads(cached)
            return posts[:limit]

        # Cache miss: gerar feed
        posts = self._generate_feed(user_id, limit=100)  # Gerar 100, cachear

        # Cachear por 5 minutos
        redis_client.setex(cache_key, 300, json.dumps(posts))

        return posts[:limit]


    def invalidate_feed_cache(self, user_id: int):
        """Invalidar cache ao criar post, dar like, etc"""
        redis_client.delete(f"feed:{user_id}")
```

---

### 2. Materializar Score

```python
# models.py
class Post(Base):
    __tablename__ = "posts"

    # ... outros campos

    # Score pré-calculado (atualizado periodicamente)
    engagement_score = Column(Float, default=0.0, index=True)
    score_updated_at = Column(DateTime)


# tasks/score_calculation.py
@celery_app.task(name='tasks.update_scores')
def update_engagement_scores():
    """
    Atualizar scores de posts ativos

    Rodar a cada 15 minutos
    Atualiza apenas posts dos últimos 7 dias
    """
    cutoff = datetime.utcnow() - timedelta(days=7)

    posts = db.query(Post).filter(
        Post.created_at > cutoff
    ).all()

    for post in posts:
        score = calculate_engagement_score(post)
        post.engagement_score = score
        post.score_updated_at = datetime.utcnow()

    db.commit()


# Feed query (muito rápida)
posts = db.query(Post).filter(
    Post.id.in_(feed_post_ids)
).order_by(
    Post.engagement_score.desc()  # Já indexado!
).all()
```

---

## 📊 Comparação de Estratégias

| Estratégia | Escrita | Leitura | Storage | Usado por |
|------------|---------|---------|---------|-----------|
| **Pull** | Rápida | Lenta | Baixo | LinkedIn (early), Tumblr |
| **Push** | Lenta | Rápida | Alto | Facebook, Instagram |
| **Hybrid** | Média | Rápida | Médio | **Twitter, Instagram** |

---

## 🧪 Testes

```python
# tests/test_feed.py
def test_follow_user(client, auth_headers, other_user):
    """Testa seguir usuário"""
    response = client.post(
        f"/users/{other_user['id']}/follow",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["following"] == True


def test_feed_shows_followed_users_posts(client, auth_headers, db):
    """Testa que feed mostra posts de quem você segue"""
    # User1 segue User2
    # User2 cria post
    # Feed de User1 deve conter post de User2

    # Seguir
    client.post(f"/users/{user2.id}/follow", headers=auth_headers)

    # User2 cria post
    post = create_post(user2.id, "Hello from User2")

    # Buscar feed de User1
    response = client.get("/feed", headers=auth_headers)

    posts = response.json()["posts"]
    assert len(posts) > 0
    assert posts[0]["id"] == post.id


def test_feed_ranking(client, auth_headers):
    """Testa que feed está ordenado por score"""
    response = client.get("/feed?algorithm=engagement", headers=auth_headers)

    posts = response.json()["posts"]

    # Verificar ordenação (score decrescente)
    for i in range(len(posts) - 1):
        assert posts[i]["score"] >= posts[i + 1]["score"]
```

---

## 🎯 Conceitos Aprendidos

1. ✅ **Pull vs Push**: trade-offs de cada estratégia
2. ✅ **Fanout**: distribuir post para seguidores
3. ✅ **Hybrid approach**: combinar pull e push
4. ✅ **Ranking algorithms**: chronological, engagement, personalized
5. ✅ **Time decay**: posts antigos valem menos
6. ✅ **Affinity**: medir afinidade entre usuários
7. ✅ **Materialized scores**: pré-calcular para performance
8. ✅ **Cache invalidation**: quando invalidar feed cache

---

## 📚 Próximos Passos

- **Exercício 08**: Notificações em tempo real (WebSocket)
- **Exercício 09**: Search e recomendações (Elasticsearch)
- **Exercício 10**: Analytics e métricas

---

**Seu feed está pronto para escalar! 📱🚀**
