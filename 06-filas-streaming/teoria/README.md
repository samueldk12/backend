# Módulo 06 - Filas e Streaming

## 🎯 Objetivo

Dominar processamento assíncrono com filas e streaming de dados em tempo real.

---

## 📚 Conteúdo

### 1. Message Queues vs Event Streams

```
MESSAGE QUEUE (RabbitMQ, Redis Queue)
Producer → [Queue] → Consumer
- Mensagem consumida uma vez
- Desaparece após processamento
- Uso: Tasks assíncronas

EVENT STREAM (Kafka, Kinesis)
Producer → [Log] → Consumer1
              ↓  → Consumer2
              ↓  → Consumer3
- Evento permanece (TTL configurável)
- Múltiplos consumidores
- Replay possível
- Uso: Event sourcing, analytics
```

---

## 2. Celery (Task Queue)

### Setup

```python
# celery_app.py
from celery import Celery

app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Task
@app.task(bind=True, max_retries=3)
def process_video(self, video_id: int):
    try:
        video = Video.get(video_id)
        # Processar vídeo (encoding, thumbnails, etc)
        video.encode()
        video.generate_thumbnails()
        video.status = 'ready'
        video.save()
    except Exception as exc:
        # Retry com backoff exponencial
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

# Enviar task
from tasks import process_video
result = process_video.delay(video_id=123)
```

### Patterns

```python
# Chain (uma após a outra)
from celery import chain
chain(
    download_video.s(url),
    encode_video.s(),
    upload_to_cdn.s()
).apply_async()

# Group (paralelo)
from celery import group
group(
    process_video.s(1),
    process_video.s(2),
    process_video.s(3)
).apply_async()

# Chord (group + callback)
from celery import chord
chord(
    group(process_video.s(i) for i in range(10))
)(aggregate_results.s()).apply_async()

# Periodic tasks
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'tasks.cleanup',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM
    },
}
```

---

## 3. Apache Kafka

### Conceitos

```
Topic: user-events
├── Partition 0: [msg1, msg2, msg3, ...]
├── Partition 1: [msg4, msg5, msg6, ...]
└── Partition 2: [msg7, msg8, msg9, ...]

Producer → escreve em partições
Consumer Groups → cada grupo lê todas mensagens
  Group A:
    - Consumer 1 → Partition 0
    - Consumer 2 → Partition 1, 2
  Group B:
    - Consumer 1 → Partition 0, 1, 2
```

### Producer

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # Aguarda confirmação de todas as réplicas
    retries=3
)

# Enviar evento
producer.send('user-events', {
    'event_type': 'UserCreated',
    'user_id': 123,
    'timestamp': datetime.now().isoformat()
})

# Com key (garante ordem por user_id)
producer.send(
    'user-events',
    key=str(user_id).encode('utf-8'),
    value={'event': 'UserUpdated', ...}
)
```

### Consumer

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers=['localhost:9092'],
    group_id='email-service',  # Consumer group
    auto_offset_reset='earliest',  # Começar do início
    enable_auto_commit=False,  # Commit manual
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    try:
        event = message.value
        process_event(event)

        # Commit manual (garante processamento)
        consumer.commit()
    except Exception as e:
        logger.error(f"Error: {e}")
        # Não faz commit, vai reprocessar
```

---

## 4. RabbitMQ

### Exchange Types

```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# 1. Direct Exchange (routing key exata)
channel.exchange_declare(exchange='logs', exchange_type='direct')
channel.basic_publish(
    exchange='logs',
    routing_key='error',  # Apenas consumers com 'error'
    body='Error message'
)

# 2. Fanout (broadcast para todos)
channel.exchange_declare(exchange='broadcasts', exchange_type='fanout')
channel.basic_publish(exchange='broadcasts', routing_key='', body='Message')

# 3. Topic (pattern matching)
channel.exchange_declare(exchange='topics', exchange_type='topic')
channel.basic_publish(
    exchange='topics',
    routing_key='user.created.br',  # Matches: user.*, *.created.*, user.created.*
    body='User created'
)

# Consumer
def callback(ch, method, properties, body):
    print(f"Received: {body}")
    ch.basic_ack(delivery_tag=method.delivery_tag)  # ACK manual

channel.basic_consume(queue='task_queue', on_message_callback=callback)
channel.start_consuming()
```

---

## 5. Patterns e Best Practices

### Idempotência

```python
# ❌ Problema: Processamento duplicado
def process_payment(order_id, amount):
    charge_credit_card(amount)  # Se reprocessar, cobra 2x!

# ✅ Solução: Idempotente
def process_payment(order_id, amount):
    # Verificar se já processou
    if redis.exists(f"payment:{order_id}"):
        return "Already processed"

    # Processar
    charge_credit_card(amount)

    # Marcar como processado
    redis.setex(f"payment:{order_id}", 3600, "1")
```

### Dead Letter Queue

```python
# Celery
@app.task(bind=True, max_retries=3)
def risky_task(self, data):
    try:
        process(data)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # Enviar para DLQ
            send_to_dead_letter_queue(data, exc)
        raise self.retry(exc=exc)

# RabbitMQ
channel.queue_declare(
    queue='main_queue',
    arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'failed'
    }
)
```

### At-least-once vs Exactly-once

```python
# At-least-once (mais comum e simples)
# - Mensagem pode ser processada múltiplas vezes
# - Requer idempotência
consumer.enable_auto_commit = False
process_message(msg)
consumer.commit()  # Se falhar antes, reprocessa

# Exactly-once (complexo, Kafka Transactions)
producer.init_transactions()
producer.begin_transaction()
producer.send('topic', message)
producer.commit_transaction()
```

### Backpressure

```python
# Limitar taxa de consumo
from celery import Task

class RateLimitedTask(Task):
    rate_limit = '100/m'  # 100 tasks por minuto

@app.task(base=RateLimitedTask)
def slow_task(data):
    process(data)

# Kafka: Limitar batch size
consumer = KafkaConsumer(
    max_poll_records=10,  # Processar 10 por vez
    fetch_max_wait_ms=500
)
```

---

## 6. Casos de Uso Práticos

### Processamento de Vídeo

```python
# 1. Upload
@app.post("/videos/upload")
async def upload_video(file: UploadFile):
    # Salvar arquivo temporário
    video = Video.create(status='uploading')
    save_to_storage(file, video.id)

    # Enviar para fila
    process_video.delay(video.id)

    return {"video_id": video.id, "status": "processing"}

# 2. Worker processa
@celery_app.task
def process_video(video_id):
    video = Video.get(video_id)

    # Tasks em cadeia
    chain(
        encode_video.s(video_id, '720p'),
        encode_video.s(video_id, '1080p'),
        generate_thumbnails.s(video_id),
        upload_to_cdn.s(video_id),
        notify_user.s(video_id)
    ).apply_async()
```

### Notificações em Tempo Real

```python
# Producer: API recebe ação
@app.post("/posts/{post_id}/like")
def like_post(post_id: int, user_id: int):
    post = Post.get(post_id)
    post.likes += 1
    post.save()

    # Publicar evento
    kafka_producer.send('notifications', {
        'type': 'PostLiked',
        'post_id': post_id,
        'user_id': user_id,
        'author_id': post.author_id
    })

# Consumer: Serviço de notificações
for message in kafka_consumer:
    event = message.value
    if event['type'] == 'PostLiked':
        # Enviar notificação via WebSocket
        send_websocket_notification(
            user_id=event['author_id'],
            message=f"User {event['user_id']} liked your post"
        )
```

---

## 🎓 Decisões

### Escolha de Tecnologia

```
Tasks assíncronas simples    → Celery + Redis
Event sourcing / Analytics   → Kafka
Routing complexo             → RabbitMQ
Serverless                   → AWS SQS/SNS
Real-time streaming          → Kafka Streams / Flink
```

### Patterns

```
Fire-and-forget              → Queue sem callback
Request-response             → Queue com result backend
Chain de tasks               → Celery chain
Broadcast                    → Kafka / RabbitMQ fanout
Retry com backoff            → Celery task.retry
```

---

## 📝 Próximos Passos

1. Exemplos em [`../exemplos/`](../exemplos/)
2. Exercícios em [`../exercicios/`](../exercicios/)
3. Avance para **[Módulo 07 - Cloud](../../07-cloud-high-architecture/teoria/README.md)**
