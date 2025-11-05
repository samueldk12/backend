"""
Exemplo: Observability - Logs, Metrics, Traces

Execute: uvicorn 01_observability:app --reload

Demonstra os 3 pilares de observabilidade.
"""

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi.responses import Response
import structlog
import time
import random
from datetime import datetime
import uvicorn

# ============================================
# STRUCTURED LOGGING
# ============================================

# Configurar structlog
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# ============================================
# METRICS (Prometheus)
# ============================================

# Counter: Só aumenta (total de requests, erros, etc)
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram: Distribuição de valores (latency, tamanhos)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Gauge: Valor que sobe/desce (conexões ativas, memória)
active_requests = Gauge(
    'active_requests',
    'Number of active requests'
)

# Business metrics
orders_total = Counter(
    'orders_total',
    'Total orders created',
    ['status']
)

order_value_dollars = Histogram(
    'order_value_dollars',
    'Order value in dollars'
)

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(title="Observability Demo")

# ============================================
# MIDDLEWARE - AUTOMATIC INSTRUMENTATION
# ============================================

@app.middleware("http")
async def observe_requests(request: Request, call_next):
    """
    Middleware que automaticamente:
    1. Loga todas requests
    2. Coleta métricas
    3. Adiciona trace context
    """

    # 1. LOG: Request started
    logger.info(
        "request.started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )

    # 2. METRIC: Increment active requests
    active_requests.inc()

    # 3. METRIC: Measure duration
    start_time = time.time()

    try:
        # Call actual endpoint
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # 4. METRICS: Record
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        # 5. LOG: Request completed
        logger.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=duration
        )

        return response

    except Exception as exc:
        # 6. LOG: Request failed
        logger.error(
            "request.failed",
            method=request.method,
            path=request.url.path,
            error=str(exc),
            exc_info=True
        )

        # Increment error metric
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=500
        ).inc()

        raise

    finally:
        # 7. METRIC: Decrement active requests
        active_requests.dec()


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
def root():
    """Root endpoint"""
    logger.info("root_endpoint.called")
    return {"message": "Observability Demo", "timestamp": datetime.now().isoformat()}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    """
    Get user endpoint

    Demonstra:
    - Structured logging com contexto
    - Métricas automáticas via middleware
    """

    # LOG com contexto
    log = logger.bind(user_id=user_id)
    log.info("get_user.started")

    # Simula query no database
    time.sleep(random.uniform(0.1, 0.5))

    # Simula erro ocasional (10% chance)
    if random.random() < 0.1:
        log.error("get_user.not_found")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    user = {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }

    log.info("get_user.success", user_name=user["name"])

    return user


@app.post("/orders")
def create_order(item: str, quantity: int, price: float):
    """
    Create order endpoint

    Demonstra:
    - Business metrics (orders_total, order_value)
    - Structured logging com dados de negócio
    """

    order_id = random.randint(1000, 9999)
    total = quantity * price

    # LOG estruturado
    log = logger.bind(order_id=order_id)
    log.info(
        "order.created",
        item=item,
        quantity=quantity,
        price=price,
        total=total
    )

    # METRICS de negócio
    orders_total.labels(status="created").inc()
    order_value_dollars.observe(total)

    # Simula processamento
    time.sleep(0.2)

    # 90% sucesso, 10% falha
    if random.random() < 0.9:
        orders_total.labels(status="completed").inc()
        log.info("order.completed")
        status = "completed"
    else:
        orders_total.labels(status="failed").inc()
        log.error("order.failed", reason="payment_declined")
        status = "failed"

    return {
        "order_id": order_id,
        "status": status,
        "total": total
    }


@app.get("/slow")
def slow_endpoint():
    """
    Slow endpoint para demonstrar métricas de latência

    Histograms mostram distribuição (p50, p95, p99)
    """

    logger.info("slow_endpoint.started")

    # Simula operação lenta
    duration = random.uniform(1.0, 3.0)
    time.sleep(duration)

    logger.info("slow_endpoint.completed", duration=duration)

    return {"message": f"Took {duration:.2f}s"}


@app.get("/error")
def error_endpoint():
    """
    Endpoint que sempre falha

    Para demonstrar logs de erro
    """

    logger.error(
        "error_endpoint.intentional_error",
        reason="This is a test error"
    )

    raise Exception("Intentional error for demo")


# ============================================
# METRICS ENDPOINT
# ============================================

@app.get("/metrics")
def metrics():
    """
    Prometheus metrics endpoint

    Acesse http://localhost:8000/metrics

    Prometheus scrapes este endpoint periodicamente
    """
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
def health():
    """
    Health check endpoint

    Load balancer usa para verificar se app está saudável
    """

    # Checks
    checks = {
        "database": "healthy",  # Checkaria DB aqui
        "cache": "healthy",      # Checkaria Redis aqui
        "disk_space": "healthy",
    }

    all_healthy = all(v == "healthy" for v in checks.values())

    logger.info(
        "health_check",
        status="healthy" if all_healthy else "unhealthy",
        checks=checks
    )

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# DEMONSTRATION SCRIPT
# ============================================

def demo_logs():
    """Demonstra diferentes níveis de log"""
    print("\n" + "="*60)
    print("📝 DEMO: STRUCTURED LOGGING")
    print("="*60)

    log = logger.bind(demo="logging")

    print("\n1. INFO level:")
    log.info("user.login", user_id=123, username="alice")

    print("\n2. WARNING level:")
    log.warning("rate_limit.approaching", user_id=123, requests=95, limit=100)

    print("\n3. ERROR level:")
    log.error("payment.failed", user_id=123, error="card_declined", amount=99.99)

    print("\n💡 Logs are JSON - easy to parse and query!")


def demo_metrics():
    """Demonstra métricas"""
    print("\n" + "="*60)
    print("📊 DEMO: METRICS")
    print("="*60)

    print("\n1. Counter (só aumenta):")
    http_requests_total.labels(method="GET", endpoint="/test", status=200).inc()
    print("   ✅ Incremented http_requests_total")

    print("\n2. Histogram (distribuição):")
    http_request_duration_seconds.labels(method="GET", endpoint="/test").observe(0.5)
    print("   ✅ Recorded request duration: 0.5s")

    print("\n3. Gauge (sobe/desce):")
    active_requests.set(5)
    print("   ✅ Set active_requests: 5")

    print("\n💡 View all metrics at: http://localhost:8000/metrics")


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("="*60)
    print("🔍 OBSERVABILITY DEMO")
    print("="*60)
    print()
    print("The 3 Pillars:")
    print("  1. 📝 LOGS   - What happened (events)")
    print("  2. 📊 METRICS - How much/how fast (numbers)")
    print("  3. 🔗 TRACES - Where it went (flow)")
    print()
    print("="*60)
    print()

    # Run demos
    demo_logs()
    demo_metrics()

    print("\n" + "="*60)
    print("🚀 STARTING API")
    print("="*60)
    print()
    print("Endpoints:")
    print("  GET  /              - Root")
    print("  GET  /users/{id}    - Get user (with logs)")
    print("  POST /orders        - Create order (with business metrics)")
    print("  GET  /slow          - Slow endpoint (latency metrics)")
    print("  GET  /error         - Error endpoint (error logs)")
    print("  GET  /metrics       - Prometheus metrics")
    print("  GET  /health        - Health check")
    print()
    print("Try it:")
    print("  curl http://localhost:8000/users/123")
    print("  curl -X POST http://localhost:8000/orders?item=book&quantity=2&price=19.99")
    print("  curl http://localhost:8000/metrics")
    print()
    print("📖 API Docs: http://localhost:8000/docs")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
OBSERVABILITY BEST PRACTICES:

1. LOGS:
   ✅ Use structured logging (JSON)
   ✅ Include context (user_id, request_id, etc)
   ✅ Log events, not states
   ✅ Use proper log levels
   ❌ Don't log sensitive data (passwords, tokens)

2. METRICS:
   ✅ Counter for totals (requests, errors)
   ✅ Histogram for distributions (latency)
   ✅ Gauge for current values (memory, connections)
   ✅ Add labels for dimensions
   ❌ Don't create metrics with high cardinality labels

3. TRACES:
   ✅ Trace requests across services
   ✅ Include trace_id in logs
   ✅ Sample traces (don't trace everything)
   ✅ Use OpenTelemetry standard

TOOLS:

Logs:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Loki + Grafana
- Datadog
- Splunk

Metrics:
- Prometheus + Grafana
- Datadog
- New Relic
- CloudWatch

Traces:
- Jaeger
- Zipkin
- Datadog APM
- New Relic

ALL-IN-ONE:
- Datadog
- New Relic
- Dynatrace
- Elastic APM
"""
