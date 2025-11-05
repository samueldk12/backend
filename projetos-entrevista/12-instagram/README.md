# 📸 Projeto 12: Instagram (System Design)

> Photo sharing - aparece em 80% das entrevistas de social media systems

---

## 📋 Problema

**Design de plataforma de compartilhamento de fotos para 1B usuários.**

**Estimativas:**
```
Usuários: 1B total, 500M daily active
Posts: 100M fotos/dia = 1,150 posts/segundo
Stories: 500M stories/dia = 5,800 stories/segundo
Likes: 4B likes/dia = 46k likes/segundo

Storage:
- Fotos: 100M/dia * 365 * 5 anos * 2MB = 365PB
- Thumbnails: 100M/dia * 365 * 5 anos * 50KB = 9PB
- Total: ~400PB em 5 anos

Feed: Read-heavy (100:1 read/write ratio)
- 500M users * 50 feed views/dia = 25B feed loads/dia
- 25B * 30 posts/feed = 750B post views/dia (!)
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INSTAGRAM FLOW                       │
│                                                         │
│  Upload → Process → Store → Feed → Display             │
│     │        │        │       │       │                │
│   Mobile  Resize    S3/CDN  Redis  Client              │
│           Filters            Cache                      │
└─────────────────────────────────────────────────────────┘

SERVICES:
- Media Service: Upload, resize, filter
- Feed Service: Timeline generation (hybrid fanout)
- User Service: Profiles, follow/unfollow
- Like Service: Likes com atomic counters
- Comment Service: Nested comments
- Story Service: Ephemeral content (24h)
- Search Service: Users, hashtags (ElasticSearch)
- Notification Service: Real-time (WebSocket)
```

---

## 🗄️ Schema

```sql
-- Posts
CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    caption TEXT,
    location VARCHAR(255),

    -- Media URLs (S3/CloudFront)
    image_url TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,

    -- Metadata
    width INTEGER,
    height INTEGER,
    filter_applied VARCHAR(50),

    -- Stats (denormalized para performance)
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_created (created_at DESC)
);

-- Feed (pre-computed timeline)
CREATE TABLE feed (
    user_id BIGINT NOT NULL,
    post_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    score FLOAT, -- Ranking score (ML-based)

    PRIMARY KEY (user_id, created_at, post_id),
    INDEX idx_user_score (user_id, score DESC)
);

-- Likes (sem foreign key para performance)
CREATE TABLE likes (
    user_id BIGINT NOT NULL,
    post_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (user_id, post_id),
    INDEX idx_post (post_id),
    INDEX idx_user (user_id)
);

-- Comments
CREATE TABLE comments (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    parent_id BIGINT REFERENCES comments(id), -- Nested comments
    content TEXT NOT NULL,
    likes_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_post_created (post_id, created_at DESC),
    INDEX idx_parent (parent_id)
);

-- Stories (ephemeral, TTL 24h)
CREATE TABLE stories (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    media_url TEXT NOT NULL,
    media_type VARCHAR(20), -- 'photo' or 'video'
    views_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours',

    INDEX idx_user_expires (user_id, expires_at)
);

-- Story views
CREATE TABLE story_views (
    story_id BIGINT NOT NULL,
    viewer_id BIGINT NOT NULL,
    viewed_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (story_id, viewer_id)
);

-- Hashtags (para trending)
CREATE TABLE hashtags (
    id BIGSERIAL PRIMARY KEY,
    tag VARCHAR(100) UNIQUE NOT NULL,
    post_count INTEGER DEFAULT 0,

    INDEX idx_tag (tag),
    INDEX idx_count (post_count DESC)
);

CREATE TABLE post_hashtags (
    post_id BIGINT NOT NULL,
    hashtag_id BIGINT NOT NULL,

    PRIMARY KEY (post_id, hashtag_id),
    INDEX idx_hashtag (hashtag_id)
);
```

---

## 📷 Photo Upload & Processing

```python
from PIL import Image
import boto3
from io import BytesIO

s3 = boto3.client('s3')


@app.post("/posts/upload")
async def upload_post(
    file: UploadFile,
    user_id: int,
    caption: str = None,
    filter: str = None,
    location: str = None
):
    """
    Upload de foto

    Flow:
    1. Validar imagem
    2. Resize múltiplas versões (original, large, medium, thumbnail)
    3. Aplicar filtro (se solicitado)
    4. Upload para S3
    5. Criar post no DB
    6. Fanout para feed (assíncrono)
    """
    # 1. Validar
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "Invalid file type")

    MAX_SIZE = 20 * 1024 * 1024  # 20MB
    file_content = await file.read()

    if len(file_content) > MAX_SIZE:
        raise HTTPException(400, "File too large")

    # 2. Processar imagem
    image = Image.open(BytesIO(file_content))

    # Obter dimensões originais
    width, height = image.size

    # Aplicar filtro (se solicitado)
    if filter:
        image = apply_filter(image, filter)

    # 3. Gerar múltiplas versões
    post_id = str(uuid.uuid4())
    versions = {}

    # Original (max 2048px)
    if max(width, height) > 2048:
        image.thumbnail((2048, 2048), Image.LANCZOS)

    versions['original'] = upload_image_to_s3(image, f"posts/{post_id}/original.jpg")

    # Thumbnail (640x640)
    thumbnail = image.copy()
    thumbnail.thumbnail((640, 640), Image.LANCZOS)
    versions['thumbnail'] = upload_image_to_s3(thumbnail, f"posts/{post_id}/thumbnail.jpg")

    # 4. Extrair hashtags do caption
    hashtags = extract_hashtags(caption) if caption else []

    # 5. Criar post
    post = Post(
        id=uuid.UUID(post_id),
        user_id=user_id,
        caption=caption,
        location=location,
        image_url=versions['original'],
        thumbnail_url=versions['thumbnail'],
        width=width,
        height=height,
        filter_applied=filter
    )

    db.add(post)

    # Salvar hashtags
    for tag in hashtags:
        hashtag = get_or_create_hashtag(tag)

        db.add(PostHashtag(post_id=post.id, hashtag_id=hashtag.id))

        # Incrementar contador
        db.execute("""
            UPDATE hashtags SET post_count = post_count + 1 WHERE id = ?
        """, (hashtag.id,))

    db.commit()

    # 6. Fanout assíncrono
    kafka_producer.send('post_fanout', {
        'post_id': str(post.id),
        'user_id': user_id
    })

    return {
        'post_id': str(post.id),
        'image_url': versions['original'],
        'thumbnail_url': versions['thumbnail']
    }


def upload_image_to_s3(image: Image, key: str) -> str:
    """Upload imagem para S3 e retornar CloudFront URL"""
    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=85, optimize=True)
    buffer.seek(0)

    s3.upload_fileobj(
        buffer,
        'instagram-media',
        key,
        ExtraArgs={'ContentType': 'image/jpeg'}
    )

    # CloudFront URL
    return f"https://cdn.instagram.com/{key}"


def apply_filter(image: Image, filter_name: str) -> Image:
    """
    Aplicar filtro Instagram

    Filters populares:
    - Clarendon: Brighten + saturate
    - Gingham: Vintage + sepia
    - Juno: Boost warm tones
    - Lark: Desaturate + brighten
    """
    from PIL import ImageEnhance

    if filter_name == 'clarendon':
        # Aumentar contraste e saturação
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)

        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.2)

    elif filter_name == 'gingham':
        # Sepia tone
        image = image.convert('L')  # Grayscale
        image = image.convert('RGB')

    elif filter_name == 'lark':
        # Desaturar e brightening
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(0.7)

        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.2)

    return image


def extract_hashtags(caption: str) -> List[str]:
    """Extrair hashtags do caption (#python #coding)"""
    import re

    hashtags = re.findall(r'#(\w+)', caption)
    return [tag.lower() for tag in hashtags]
```

---

## 📱 Feed Generation (Hybrid Fanout)

```python
"""
Instagram Feed Strategy: Hybrid Fanout

Normal users (<10k followers): Push (write fanout)
Celebrities (>10k followers): Pull (read fanout)
"""

CELEBRITY_THRESHOLD = 10_000


# Fanout worker
def post_fanout_worker():
    """
    Worker para fanout de posts

    Push: Escrever no feed de cada follower
    """
    consumer = KafkaConsumer('post_fanout')

    for message in consumer:
        data = message.value

        post_id = data['post_id']
        author_id = data['user_id']

        # Verificar se é celebridade
        author = get_user(author_id)

        if author.followers_count >= CELEBRITY_THRESHOLD:
            # Celebrity: Não fazer fanout (pull on read)
            print(f"✓ Post {post_id} from celebrity {author_id} - no fanout")
            continue

        # Normal user: Fanout para followers
        followers = get_followers(author_id, limit=10_000)

        # Calcular ranking score (ML)
        score = calculate_post_score(post_id, author_id)

        # Inserir no feed de cada follower (batch)
        for follower_id in followers:
            db.execute("""
                INSERT INTO feed (user_id, post_id, author_id, created_at, score)
                VALUES (?, ?, ?, NOW(), ?)
            """, (follower_id, post_id, author_id, score))

        # Invalidar cache
        for follower_id in followers:
            redis_client.delete(f"feed:{follower_id}")

        print(f"✓ Fanout completed: {post_id} to {len(followers)} followers")


@app.get("/feed")
async def get_feed(user_id: int, page: int = 1, per_page: int = 30):
    """
    Buscar feed do usuário

    Hybrid approach:
    1. Buscar posts pré-computados (push)
    2. Buscar posts de celebridades (pull)
    3. Merge + rank com ML
    """
    # Cache
    cache_key = f"feed:{user_id}:page:{page}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # 1. Buscar posts pré-computados
    pre_computed = db.execute("""
        SELECT post_id, author_id, created_at, score
        FROM feed
        WHERE user_id = ?
        ORDER BY score DESC, created_at DESC
        LIMIT ? OFFSET ?
    """, (user_id, per_page * 2, (page - 1) * per_page)).fetchall()

    # 2. Buscar posts de celebridades
    celebrity_followees = get_celebrity_followees(user_id)

    celebrity_posts = []

    for celebrity_id in celebrity_followees:
        posts = db.execute("""
            SELECT id, user_id, created_at
            FROM posts
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (celebrity_id,)).fetchall()

        for post in posts:
            score = calculate_post_score(post.id, post.user_id, user_id)
            celebrity_posts.append({
                'post_id': post.id,
                'author_id': post.user_id,
                'created_at': post.created_at,
                'score': score
            })

    # 3. Merge e rank
    all_posts = list(pre_computed) + celebrity_posts
    all_posts.sort(key=lambda p: (p['score'], p['created_at']), reverse=True)

    # 4. Limit
    feed_posts = all_posts[:per_page]

    # 5. Enriquecer com dados do post
    enriched = enrich_feed_posts(feed_posts)

    # Cache 5 minutos
    redis_client.setex(cache_key, 300, json.dumps(enriched))

    return enriched


def calculate_post_score(post_id: int, author_id: int, viewer_id: int = None) -> float:
    """
    Calcular ranking score (ML-based)

    Fatores:
    - Engagement (likes, comments)
    - Recency (posts mais novos)
    - Relationship (amigos próximos)
    - Content type (photo vs video)
    - User preferences (historical engagement)
    """
    post = get_post(post_id)

    # Base score: engagement
    engagement_score = (
        post.likes_count * 1.0 +
        post.comments_count * 3.0  # Comments valem mais
    )

    # Recency decay (exponential)
    age_hours = (datetime.utcnow() - post.created_at).total_seconds() / 3600
    recency_score = math.exp(-age_hours / 24)  # Decay over 24h

    # Relationship score (se viewer_id fornecido)
    relationship_score = 1.0

    if viewer_id:
        # User já interagiu com author antes?
        interactions = count_user_interactions(viewer_id, author_id)
        relationship_score = min(interactions / 10.0, 3.0)  # Max 3x boost

    # Combine scores
    total_score = (
        engagement_score * 0.5 +
        recency_score * 100 +
        relationship_score * 50
    )

    return total_score
```

---

## ❤️ Likes (High Throughput)

```python
@app.post("/posts/{post_id}/like")
async def like_post(post_id: int, user_id: int):
    """
    Curtir post

    Desafio: 46k likes/segundo!

    Solução:
    1. Write to Redis (fast cache)
    2. Async batch write to PostgreSQL
    3. Atomic increment counter
    """
    # Idempotência: verificar se já curtiu
    like_key = f"like:{post_id}:{user_id}"

    if redis_client.exists(like_key):
        return {"status": "already_liked"}

    # Adicionar ao Redis (cache)
    redis_client.setex(like_key, 86400, '1')  # TTL 24h

    # Incrementar contador (Redis)
    counter_key = f"post:{post_id}:likes_count"
    new_count = redis_client.incr(counter_key)

    # Async write to DB (Kafka)
    kafka_producer.send('likes', {
        'post_id': post_id,
        'user_id': user_id,
        'created_at': time.time()
    })

    # Notificação (se não é self-like)
    post = get_post(post_id)

    if post.user_id != user_id:
        notify_user(post.user_id, f"{get_username(user_id)} liked your post")

    return {
        'status': 'liked',
        'likes_count': new_count
    }


# Batch writer (Kafka consumer)
def likes_batch_writer():
    """
    Consumir likes do Kafka e escrever em batch no PostgreSQL

    Batch de 1000 likes ou 5 segundos (o que vier primeiro)
    """
    consumer = KafkaConsumer('likes')

    batch = []
    last_flush = time.time()

    for message in consumer:
        batch.append(message.value)

        # Flush conditions
        should_flush = (
            len(batch) >= 1000 or
            time.time() - last_flush > 5
        )

        if should_flush:
            # Bulk insert
            values = [(like['user_id'], like['post_id'], like['created_at']) for like in batch]

            db.execute("""
                INSERT INTO likes (user_id, post_id, created_at)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, values)

            # Update counters
            post_counts = {}

            for like in batch:
                post_id = like['post_id']
                post_counts[post_id] = post_counts.get(post_id, 0) + 1

            for post_id, count in post_counts.items():
                db.execute("""
                    UPDATE posts
                    SET likes_count = likes_count + ?
                    WHERE id = ?
                """, (count, post_id))

            db.commit()

            print(f"✓ Flushed {len(batch)} likes to DB")

            batch.clear()
            last_flush = time.time()
```

---

## 📖 Stories (Ephemeral Content)

```python
@app.post("/stories")
async def create_story(
    user_id: int,
    file: UploadFile,
    media_type: str = 'photo'
):
    """
    Criar story (desaparece em 24h)

    Stories são read-heavy: 5,800 stories/s posted, 500k views/s
    """
    # Upload mídia
    story_id = str(uuid.uuid4())
    media_url = upload_to_s3(file, f"stories/{story_id}")

    # Criar story
    story = Story(
        id=story_id,
        user_id=user_id,
        media_url=media_url,
        media_type=media_type,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.add(story)
    db.commit()

    # Notificar followers
    notify_followers(user_id, "posted a new story")

    return {
        'story_id': story_id,
        'expires_at': story.expires_at
    }


@app.get("/stories/feed")
async def get_stories_feed(user_id: int):
    """
    Buscar stories de quem você segue

    Ordenado por:
    1. Amigos próximos (alta interação)
    2. Não visualizados
    3. Mais recentes
    """
    # Buscar followees
    followees = get_followees(user_id)

    # Buscar stories (não expiradas)
    stories = db.execute("""
        SELECT s.*, u.username, u.avatar_url,
               EXISTS(SELECT 1 FROM story_views WHERE story_id = s.id AND viewer_id = ?) as viewed
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.user_id IN (?)
          AND s.expires_at > NOW()
        ORDER BY viewed ASC, s.created_at DESC
    """, (user_id, followees)).fetchall()

    # Agrupar por user
    by_user = {}

    for story in stories:
        if story.user_id not in by_user:
            by_user[story.user_id] = []

        by_user[story.user_id].append(story)

    return by_user


# Cleanup worker (delete expired stories)
def cleanup_expired_stories():
    """Deletar stories expiradas (cron job a cada hora)"""
    deleted = db.execute("""
        DELETE FROM stories
        WHERE expires_at < NOW()
    """)

    print(f"✓ Deleted {deleted.rowcount} expired stories")
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Como escalar likes para 46k/segundo?"

**Você:** "Problema: Writes são bottleneck no PostgreSQL.

Solução - Write buffering:
1. **Redis cache**: Write imediatamente em Redis (in-memory, rápido)
2. **Kafka queue**: Enfileirar like event
3. **Batch writer**: Consumir Kafka e escrever em batch no PostgreSQL (1000 likes por query)
4. **Async counter update**: Atualizar `likes_count` em batch

Resultado: 46k writes/s viram 46 batch writes/s (1000x redução!)"

---

**Interviewer:** "Como garantir feed relevante (não apenas cronológico)?"

**Você:** "Instagram usa ML ranking:

Features:
- **Engagement**: Likes, comments, saves (signal forte)
- **Recency**: Decaimento exponencial (posts velhos penalizados)
- **Relationship**: Frequência de interação com author
- **Content type**: Photo vs video (alguns users preferem um tipo)
- **User preferences**: Historical engagement patterns

Model: Gradient Boosted Trees (LightGBM/XGBoost)

Treinamento: Offline com Spark, deployment online com model serving (TensorFlow Serving)"

---

## ✅ Checklist

- [ ] Photo upload e processing (resize, filters)
- [ ] Feed generation (hybrid fanout)
- [ ] Likes com high throughput (Redis + batch writes)
- [ ] Comments (nested)
- [ ] Stories (ephemeral, 24h TTL)
- [ ] Hashtags e trending
- [ ] ML-based ranking
- [ ] CDN para media delivery

---

**Photo sharing design muito comum! 📸**
