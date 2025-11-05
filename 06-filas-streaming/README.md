# 06 - Filas e Streaming

## Índice

1. [Message Queues](#message-queues)
2. [Celery](#celery)
3. [Kafka](#kafka)
4. [Saga Pattern](#saga-pattern)

---

## Message Queues

### Por que usar?

**Desacoplamento**: Producer e Consumer independentes
**Async Processing**: Não bloqueia request
**Retry**: Reprocessa em caso de falha
**Load Leveling**: Absorve picos de carga

```
HTTP Request → API → Queue → Worker
    (sync)         (async)
```

---

## Celery

### Setup

```python
# celery_app.py
from celery import Celery

app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

@app.task
def enviar_email(email, assunto, corpo):
    # Task assíncrona
    send_email_smtp(email, assunto, corpo)
    return f"Email enviado para {email}"

@app.task(bind=True, max_retries=3)
def processar_video(self, video_id):
    try:
        video = get_video(video_id)
        compress_video(video)
        upload_to_cdn(video)
    except Exception as exc:
        # Retry com exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### Usando Tasks

```python
from fastapi import FastAPI
from celery_app import enviar_email, processar_video

app = FastAPI()

@app.post("/users")
def create_user(user: User):
    # Salva user no DB (rápido)
    db.save(user)

    # Envia email ASYNC (não bloqueia)
    enviar_email.delay(user.email, "Welcome!", "...")

    return {"id": user.id}  # Retorna imediatamente

@app.post("/videos")
def upload_video(video: Video):
    # Salva video no storage
    save_video(video)

    # Processa ASYNC (pode demorar minutos!)
    processar_video.delay(video.id)

    return {"id": video.id, "status": "processing"}
```

### Monitoramento

```bash
# Flower - Web UI para Celery
pip install flower
celery -A celery_app flower

# http://localhost:5555
```

---

## Kafka

### Conceitos

**Topic**: Canal de mensagens
**Partition**: Topic dividido em partições (paralelismo)
**Consumer Group**: Consumers que dividem trabalho
**Offset**: Posição no log

```
Topic: "orders"
├── Partition 0 [msg1, msg2, msg3]
├── Partition 1 [msg4, msg5, msg6]
└── Partition 2 [msg7, msg8, msg9]

Consumer Group A
├── Consumer 1 → Partition 0
├── Consumer 2 → Partition 1
└── Consumer 3 → Partition 2
```

### Producer

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Enviar mensagem
def create_order(order_data):
    # Salva no DB
    order = db.save_order(order_data)

    # Publica evento
    producer.send('orders', {
        'order_id': order.id,
        'user_id': order.user_id,
        'total': order.total,
        'timestamp': time.time()
    })

    producer.flush()
```

### Consumer

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='inventory-service',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# Consome mensagens
for message in consumer:
    order = message.value

    # Processa
    reserve_inventory(order['order_id'])

    # Commit offset
    consumer.commit()
```

---

## Saga Pattern

### Problema

Transações distribuídas entre múltiplos serviços.

**Cenário**: Criar pedido
1. Order Service: Cria order
2. Payment Service: Cobra cartão
3. Inventory Service: Reserva estoque
4. Shipping Service: Agenda entrega

Se Payment falhar? Precisa desfazer order!

### Solução: Choreography-based Saga

```python
# Order Service
@event_bus.subscribe("order.requested")
async def handle_order_requested(event):
    order = create_order(event)
    await event_bus.publish("order.created", order)

# Payment Service
@event_bus.subscribe("order.created")
async def handle_order_created(event):
    try:
        charge_payment(event['order_id'], event['total'])
        await event_bus.publish("payment.completed", event)
    except PaymentFailed:
        await event_bus.publish("payment.failed", event)

# Order Service (compensation)
@event_bus.subscribe("payment.failed")
async def handle_payment_failed(event):
    # Desfaz order
    cancel_order(event['order_id'])
    await event_bus.publish("order.cancelled", event)

# Inventory Service
@event_bus.subscribe("payment.completed")
async def handle_payment_completed(event):
    try:
        reserve_inventory(event['order_id'])
        await event_bus.publish("inventory.reserved", event)
    except OutOfStock:
        await event_bus.publish("inventory.failed", event)
        # Payment service precisa fazer refund!
```

### Solução: Orchestration-based Saga

```python
class OrderSaga:
    def __init__(self, order_id):
        self.order_id = order_id
        self.steps_completed = []

    async def execute(self):
        try:
            # Step 1: Create order
            await self.create_order()
            self.steps_completed.append('order')

            # Step 2: Charge payment
            await self.charge_payment()
            self.steps_completed.append('payment')

            # Step 3: Reserve inventory
            await self.reserve_inventory()
            self.steps_completed.append('inventory')

            # Step 4: Schedule shipping
            await self.schedule_shipping()

            return "success"

        except Exception as e:
            # Compensate (rollback)
            await self.compensate()
            raise

    async def compensate(self):
        # Rollback in reverse order
        if 'inventory' in self.steps_completed:
            await self.release_inventory()

        if 'payment' in self.steps_completed:
            await self.refund_payment()

        if 'order' in self.steps_completed:
            await self.cancel_order()
```

---

## Próximo Módulo

➡️ [07 - Cloud e High Architecture](../07-cloud-high-architecture/README.md)
