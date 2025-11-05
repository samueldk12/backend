# 07 - Cloud e High Architecture

## Índice

1. [Observability](#observability)
2. [Logs, Metrics, Traces](#logs-metrics-traces)
3. [Distributed Systems](#distributed-systems)
4. [CAP Theorem](#cap-theorem)

---

## Observability

### Os 3 Pilares

```
Logs → O QUE aconteceu
Metrics → QUANTO/QUANDO aconteceu
Traces → POR ONDE passou
```

---

## Logs, Metrics, Traces

### Logs Estruturados

```python
import structlog

logger = structlog.get_logger()

# ❌ Log não estruturado
logging.info(f"User {user_id} purchased item {item_id} for ${price}")

# ✅ Log estruturado (fácil de query)
logger.info(
    "purchase_completed",
    user_id=user_id,
    item_id=item_id,
    price=price,
    currency="USD"
)

# Query no ELK/Splunk:
# user_id:123 AND event:purchase_completed
```

### Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# Counter: só aumenta
requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram: distribuição (latency, size)
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration'
)

# Gauge: valor que sobe/desce (memory, connections)
active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# Uso
@app.get("/users/{user_id}")
@request_duration.time()  # Mede duração
def get_user(user_id: int):
    requests_total.labels(method='GET', endpoint='/users', status=200).inc()
    active_connections.inc()

    try:
        user = db.get_user(user_id)
        return user
    finally:
        active_connections.dec()
```

### Distributed Tracing (Jaeger/Zipkin)

```python
from opentelemetry import trace
from opentelemetry.ext.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

@app.get("/orders/{order_id}")
async def get_order(order_id: int):
    # Span automático para request HTTP

    # Span manual para operação
    with tracer.start_as_current_span("db.query"):
        order = await db.get_order(order_id)

    with tracer.start_as_current_span("inventory.check"):
        inventory = await inventory_service.check(order.items)

    return order

# Trace completo:
# GET /orders/123
#   ├─ db.query (50ms)
#   └─ inventory.check (100ms)
#      └─ GET /inventory/items (80ms)
```

---

## Distributed Systems

### Service Discovery

```python
# Consul/Etcd
import consul

c = consul.Consul()

# Registrar serviço
c.agent.service.register(
    'user-service',
    service_id='user-service-1',
    address='10.0.1.5',
    port=8000
)

# Descobrir serviços
services = c.health.service('user-service', passing=True)
for service in services:
    print(f"{service['Service']['Address']}:{service['Service']['Port']}")
```

### Circuit Breaker

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_external_api():
    response = requests.get('https://api.externa.com/data')
    return response.json()

# Se 5 falhas consecutivas → circuit OPEN (não tenta mais)
# Após 60s → circuit HALF_OPEN (tenta 1 request)
# Se sucesso → circuit CLOSED (volta ao normal)
```

### Retry with Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def call_api():
    return requests.get('https://api.com/data')

# Tentativa 1: imediata
# Tentativa 2: espera 1s
# Tentativa 3: espera 2s
# Desiste após 3 tentativas
```

---

## CAP Theorem

```
C - Consistency:   Todos veem mesmos dados
A - Availability:  Sistema sempre responde
P - Partition Tolerance: Funciona com falha de rede

Só pode ter 2 de 3!
```

### CP (Consistency + Partition Tolerance)

**Exemplo:** MongoDB, HBase

```
Node A ─X─ Node B  (partição de rede)

Write em A → RECUSADO (não pode garantir consistency)

Sistema fica INDISPONÍVEL até rede voltar
```

**Quando usar:** Dados críticos (banco, pagamento)

### AP (Availability + Partition Tolerance)

**Exemplo:** Cassandra, DynamoDB

```
Node A ─X─ Node B  (partição de rede)

Write em A → ACEITO (eventual consistency)
Read de B → Retorna valor antigo

Sistema DISPONÍVEL, mas inconsistente temporariamente
```

**Quando usar:** Alta disponibilidade crítica (cache, sessões)

### CA (Consistency + Availability)

**Exemplo:** PostgreSQL single-node

```
Só funciona SEM partição de rede
(single datacenter, sem replicação distribuída)
```

---

## Próximo Módulo

➡️ [08 - Estruturas de Dados](../08-estruturas-dados/README.md)
