# 🎬 Projeto 10: Netflix (System Design)

> Video streaming - aparece em 75% das entrevistas de media systems

---

## 📋 Problema

**Design de plataforma de streaming de vídeo para 200M usuários.**

**Estimativas:**
```
Usuários: 200M subscribers, 100M concurrent viewers (peak)
Catálogo: 10k títulos, cada com múltiplas resoluções
Storage:
  - 1 filme (2h) em 4K = ~50GB
  - Com todas resoluções (480p-4K) = ~80GB
  - 10k títulos * 80GB = 800TB de conteúdo

Bandwidth:
  - 100M viewers * 5 Mbps (1080p) = 500 Tbps (!!!)
  - Custo: ~$1M/dia em CDN

Encoding:
  - 1 filme → encode para 6 resoluções = ~6 horas de CPU
  - 100 novos títulos/semana = 2,400 horas CPU/semana
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      VIDEO PIPELINE                         │
│                                                             │
│  Upload → Transcode → Package → CDN → Player               │
│    │         │          │        │       │                 │
│    S3      FFmpeg     HLS/DASH  Edge   Adaptive            │
│           (6 res.)   Manifest  Cache   Bitrate             │
└─────────────────────────────────────────────────────────────┘

COMPONENTS:
- Origin Storage: S3 (master videos)
- Encoding: AWS MediaConvert / FFmpeg workers
- CDN: CloudFront / Akamai (95% of traffic)
- Metadata DB: PostgreSQL/DynamoDB
- Recommendation: ML service (Spark/TensorFlow)
- User Service: Auth, profiles, watch history
```

---

## 🎥 Video Encoding Pipeline

```python
"""
Adaptive Bitrate Streaming (ABR)

Concept: Encode vídeo em múltiplas resoluções, player escolhe baseado em bandwidth

Resoluções:
- 4K (2160p): 15-25 Mbps
- 1080p: 5-8 Mbps
- 720p: 3-5 Mbps
- 480p: 1-2 Mbps
- 360p: 0.5-1 Mbps
- 240p: 0.3-0.5 Mbps (mobile low bandwidth)
"""

import boto3
import subprocess

s3 = boto3.client('s3')

RESOLUTIONS = [
    {'name': '4K', 'width': 3840, 'height': 2160, 'bitrate': '20M'},
    {'name': '1080p', 'width': 1920, 'height': 1080, 'bitrate': '6M'},
    {'name': '720p', 'width': 1280, 'height': 720, 'bitrate': '4M'},
    {'name': '480p', 'width': 854, 'height': 480, 'bitrate': '1.5M'},
    {'name': '360p', 'width': 640, 'height': 360, 'bitrate': '0.8M'},
]


@app.post("/videos/upload")
async def upload_video(
    file: UploadFile,
    title: str,
    duration_seconds: int
):
    """
    Upload vídeo

    Flow:
    1. Upload para S3 (master)
    2. Trigger encoding pipeline (assíncrono)
    """
    # Upload master file
    video_id = str(uuid.uuid4())
    s3_key = f"masters/{video_id}/original.mp4"

    s3.upload_fileobj(
        file.file,
        'netflix-videos',
        s3_key
    )

    # Criar metadata
    video = create_video_metadata(
        video_id=video_id,
        title=title,
        duration=duration_seconds,
        status='processing'
    )

    # Trigger encoding (Kafka)
    kafka_producer.send('video_encoding', {
        'video_id': video_id,
        's3_key': s3_key
    })

    return {
        'video_id': video_id,
        'status': 'processing',
        'estimated_time': f'{len(RESOLUTIONS) * 2} hours'
    }


# Encoding worker (Celery/Kafka)
def encoding_worker():
    """
    Worker para encoding de vídeos

    Usa FFmpeg para transcode
    """
    consumer = KafkaConsumer('video_encoding')

    for message in consumer:
        data = message.value
        video_id = data['video_id']
        s3_key = data['s3_key']

        # Download master do S3
        local_path = f"/tmp/{video_id}_master.mp4"
        s3.download_file('netflix-videos', s3_key, local_path)

        # Encode para cada resolução (paralelo)
        for resolution in RESOLUTIONS:
            encode_video(
                video_id=video_id,
                input_path=local_path,
                resolution=resolution
            )

        # Gerar HLS manifest
        generate_hls_manifest(video_id)

        # Marcar como complete
        update_video_status(video_id, 'ready')


def encode_video(video_id: str, input_path: str, resolution: dict):
    """
    Encode vídeo para resolução específica usando FFmpeg

    Output: HLS segments (10s chunks)
    """
    output_dir = f"/tmp/{video_id}/{resolution['name']}"
    os.makedirs(output_dir, exist_ok=True)

    output_pattern = f"{output_dir}/segment_%03d.ts"
    playlist_file = f"{output_dir}/playlist.m3u8"

    # FFmpeg command
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf', f"scale={resolution['width']}:{resolution['height']}",
        '-c:v', 'libx264',  # H.264 codec
        '-b:v', resolution['bitrate'],
        '-c:a', 'aac',
        '-b:a', '128k',
        '-hls_time', '10',  # 10s segments
        '-hls_list_size', '0',
        '-hls_segment_filename', output_pattern,
        playlist_file
    ]

    subprocess.run(cmd, check=True)

    # Upload segments para S3
    for segment in os.listdir(output_dir):
        s3.upload_file(
            f"{output_dir}/{segment}",
            'netflix-videos',
            f"videos/{video_id}/{resolution['name']}/{segment}"
        )

    print(f"✓ Encoded {video_id} to {resolution['name']}")


def generate_hls_manifest(video_id: str):
    """
    Gerar master playlist (HLS)

    Master playlist lista todas resoluções disponíveis
    """
    manifest = "#EXTM3U\n#EXT-X-VERSION:3\n\n"

    for resolution in RESOLUTIONS:
        manifest += f"#EXT-X-STREAM-INF:BANDWIDTH={resolution['bitrate']},RESOLUTION={resolution['width']}x{resolution['height']}\n"
        manifest += f"{resolution['name']}/playlist.m3u8\n\n"

    # Upload master playlist
    s3.put_object(
        Bucket='netflix-videos',
        Key=f"videos/{video_id}/master.m3u8",
        Body=manifest,
        ContentType='application/x-mpegURL'
    )
```

---

## 📺 Video Playback (Adaptive Bitrate)

```python
"""
Player usa HLS/DASH para adaptive bitrate

Flow:
1. Fetch master playlist
2. Medir bandwidth do cliente
3. Escolher resolução apropriada
4. Download segments (10s chunks)
5. Ajustar resolução dinamicamente
"""

@app.get("/videos/{video_id}/play")
async def play_video(video_id: str, user_id: int):
    """
    Endpoint de playback

    Retorna:
    - Manifest URL (HLS)
    - CDN URL (edge location mais próxima)
    - DRM license (Widevine/FairPlay)
    """
    # Verificar permissão (subscription ativa)
    if not user_has_active_subscription(user_id):
        raise HTTPException(403, "Subscription required")

    # CDN URL (CloudFront signed URL)
    cdn_url = generate_signed_cdn_url(video_id, ttl=3600)

    # DRM license
    drm_license = generate_drm_license(video_id, user_id)

    return {
        'manifest_url': f"{cdn_url}/master.m3u8",
        'drm_license': drm_license,
        'thumbnail_url': f"https://cdn.netflix.com/thumbnails/{video_id}.jpg"
    }


def generate_signed_cdn_url(video_id: str, ttl: int) -> str:
    """
    Gerar CloudFront signed URL

    Previne hotlinking e piracy
    """
    from botocore.signers import CloudFrontSigner
    import rsa

    cloudfront_signer = CloudFrontSigner(
        key_id='APKA...',
        rsa_signer=lambda message: rsa.sign(message, private_key, 'SHA-1')
    )

    url = f"https://d123.cloudfront.net/videos/{video_id}"

    signed_url = cloudfront_signer.generate_presigned_url(
        url,
        date_less_than=datetime.now() + timedelta(seconds=ttl)
    )

    return signed_url
```

---

## 💾 CDN Strategy (95% of Traffic)

```python
"""
Netflix CDN Strategy:

Open Connect: Netflix's own CDN
- Coloca servidores dentro de ISPs (Comcast, AT&T)
- Reduz custo de bandwidth em 95%
- Cache de conteúdo popular

Tiering:
L1: Edge (ISP cache) - 95% hit rate
L2: Regional (AWS CloudFront)
L3: Origin (S3)
"""

class CDNCacheStrategy:
    """
    CDN caching strategy

    Popular content: Cache por 7 dias
    New releases: Pre-warm cache (push)
    Long-tail: Pull on demand
    """

    @staticmethod
    def get_cache_ttl(video_id: str) -> int:
        """
        Calcular TTL baseado em popularidade

        Popular (>10k views/dia): 7 dias
        Medium (1k-10k): 3 dias
        Long-tail (<1k): 1 dia
        """
        views_per_day = get_video_views(video_id, days=1)

        if views_per_day > 10_000:
            return 7 * 24 * 3600  # 7 dias
        elif views_per_day > 1_000:
            return 3 * 24 * 3600  # 3 dias
        else:
            return 1 * 24 * 3600  # 1 dia

    @staticmethod
    def pre_warm_cache(video_id: str, regions: List[str]):
        """
        Pre-warm CDN cache antes de lançamento

        Usado para new releases (Stranger Things, etc)
        Evita thundering herd no launch day
        """
        for region in regions:
            # Trigger cache warming
            requests.get(
                f"https://edge-{region}.netflix.com/videos/{video_id}/master.m3u8",
                headers={'X-Netflix-Cache-Warm': 'true'}
            )
```

---

## 🎯 Recommendation Engine

```python
"""
Netflix Recommendation: 80% do conteúdo assistido vem de recomendações!

Algoritmos:
1. Collaborative Filtering (CF)
2. Content-Based Filtering
3. Matrix Factorization (SVD)
4. Deep Learning (Neural Networks)
"""

from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Netflix").getOrCreate()

def train_recommendation_model():
    """
    Treinar modelo ALS (Alternating Least Squares)

    Input: user_id, video_id, rating (implicit: watch time)
    Output: Predições de rating para (user, video) pairs
    """
    # Carregar watch history
    df = spark.read.jdbc(
        url="jdbc:postgresql://localhost/netflix",
        table="watch_history"
    )

    # Normalizar watch time para rating (0-5)
    df = df.withColumn(
        'rating',
        (df.watch_time_seconds / df.video_duration_seconds) * 5
    )

    # Treinar ALS
    als = ALS(
        maxIter=10,
        regParam=0.1,
        userCol="user_id",
        itemCol="video_id",
        ratingCol="rating",
        coldStartStrategy="drop"
    )

    model = als.fit(df)

    return model


@app.get("/users/{user_id}/recommendations")
async def get_recommendations(user_id: int, limit: int = 20):
    """
    Buscar recomendações personalizadas

    Usa modelo pré-treinado + regras de negócio
    """
    # Carregar recomendações do cache
    cache_key = f"recommendations:{user_id}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # Buscar top recommendations do modelo
    user_recs = model.recommendForUser(user_id, limit * 2)

    # Aplicar regras de negócio
    recommendations = []

    for rec in user_recs:
        video = get_video(rec.video_id)

        # Skip se já assistiu
        if user_watched_video(user_id, rec.video_id):
            continue

        # Skip se não disponível na região
        if not video_available_in_region(rec.video_id, user.country):
            continue

        recommendations.append({
            'video_id': rec.video_id,
            'title': video.title,
            'thumbnail': video.thumbnail_url,
            'score': rec.rating
        })

        if len(recommendations) >= limit:
            break

    # Cache por 1 hora
    redis_client.setex(cache_key, 3600, json.dumps(recommendations))

    return recommendations
```

---

## 📊 Watch Analytics

```python
"""
Tracking de visualização para analytics e billing

Events:
- video_started
- video_progress (a cada 10s)
- video_completed
- video_paused
- video_seek
"""

@app.post("/analytics/video_event")
async def track_video_event(
    user_id: int,
    video_id: str,
    event_type: str,
    timestamp_seconds: int
):
    """
    Track viewing event

    High volume: 100M users * 1 event/10s = 10M events/second!

    Solução: Batch + async
    """
    # Kafka para processing assíncrono
    kafka_producer.send('video_events', {
        'user_id': user_id,
        'video_id': video_id,
        'event_type': event_type,
        'timestamp': timestamp_seconds,
        'created_at': time.time()
    })

    return {'status': 'tracked'}


# Analytics worker (Spark Streaming)
def analytics_worker():
    """
    Processar eventos com Spark Streaming

    Agregações:
    - Total watch time por vídeo
    - Completion rate
    - Drop-off points (onde users param de assistir)
    """
    from pyspark.streaming.kafka import KafkaUtils

    ssc = StreamingContext(spark.sparkContext, 60)  # 60s batch

    kafka_stream = KafkaUtils.createDirectStream(
        ssc,
        ['video_events'],
        {'bootstrap.servers': 'kafka:9092'}
    )

    # Processar events
    events = kafka_stream.map(lambda x: json.loads(x[1]))

    # Agregar: total watch time por vídeo
    watch_time = events \
        .filter(lambda e: e['event_type'] == 'video_progress') \
        .map(lambda e: (e['video_id'], 10))  # 10s per event \
        .reduceByKey(lambda a, b: a + b)

    # Salvar no DB
    watch_time.foreachRDD(save_watch_time_to_db)

    ssc.start()
    ssc.awaitTermination()
```

---

## 🔐 DRM (Digital Rights Management)

```python
"""
Proteger conteúdo contra piracy

DRM providers:
- Widevine (Google/Android)
- FairPlay (Apple)
- PlayReady (Microsoft)

Encryption: CENC (Common Encryption)
"""

def generate_drm_license(video_id: str, user_id: int) -> str:
    """
    Gerar license token para DRM

    Token contém:
    - user_id
    - video_id
    - expiration (1 hora)
    - device_id (bind para device específico)
    """
    import jwt

    payload = {
        'user_id': user_id,
        'video_id': video_id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'device_id': request.headers.get('X-Device-ID')
    }

    token = jwt.encode(payload, DRM_SECRET_KEY, algorithm='HS256')

    return token
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Como escalar para 100M viewers simultâneos?"

**Você:** "Desafio: 100M * 5 Mbps = 500 Tbps de bandwidth!

Soluções:
1. **CDN multi-tier**: 95% do tráfego servido por edge (ISP cache)
2. **Open Connect**: Netflix coloca servidores dentro de ISPs (Comcast, Verizon)
3. **Pre-warming**: Cache popular content antes do peak
4. **Adaptive bitrate**: Reduzir qualidade quando bandwidth é limitado
5. **P2P streaming**: WebRTC para compartilhar entre users próximos (experimental)

Custo: ~$1M/dia mesmo com otimizações!"

---

**Interviewer:** "Como garantir qualidade de streaming?"

**Você:** "Métricas críticas:
- **Startup time** <2s: Pre-load primeiro segment
- **Buffering ratio** <1%: Adaptive bitrate + prefetching
- **Bitrate**: Medir bandwidth e ajustar resolução dinamicamente

Técnicas:
1. Multiple CDN providers (failover)
2. TCP BBR (better congestion control)
3. QUIC protocol (HTTP/3)
4. Client-side buffer (30s ahead)"

---

## ✅ Checklist

- [ ] Video upload e encoding pipeline
- [ ] HLS/DASH adaptive bitrate
- [ ] CDN strategy (multi-tier caching)
- [ ] Playback com DRM
- [ ] Recommendation engine
- [ ] Watch analytics (Spark Streaming)
- [ ] Bandwidth optimization

---

**Video streaming é caso de estudo clássico! 🎬**
