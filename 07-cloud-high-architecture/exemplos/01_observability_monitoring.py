"""
Módulo 07 - Cloud e High Architecture: Observabilidade e Monitoramento

Este exemplo demonstra os 3 pilares da observabilidade:
1. LOGS: O que aconteceu? (events)
2. METRICS: Com que frequência? Quanto? (numbers)
3. TRACES: Onde gastou tempo? (distributed tracing)

Ferramentas:
- Structured Logging (JSON)
- Prometheus (metrics)
- OpenTelemetry (distributed tracing)
- Health checks e liveness probes

Execute:
    # Instale dependências
    pip install prometheus-client opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi

    # Execute a aplicação
    uvicorn 01_observability_monitoring:app --reload

    # Acesse métricas
    curl http://localhost:8000/metrics

    # Acesse traces
    curl http://localhost:8000/users/123
"""

import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
import sys

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import Response
import uvicorn

# Prometheus (metrics)
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# OpenTelemetry (distributed tracing)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


# ============================================================================
# PILAR 1: STRUCTURED LOGGING
# ============================================================================

class StructuredLogger:
    """
    Structured logging: logs em formato JSON

    Benefícios:
    - Fácil de parsear e buscar
    - Integração com ELK, Datadog, CloudWatch
    - Campos customizados (user_id, request_id, etc)
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Handler para stdout (capturado por Docker/K8s)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._json_formatter())
        self.logger.addHandler(handler)

    def _json_formatter(self):
        """Formata logs como JSON"""
        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                # Adicionar campos extras
                if hasattr(record, "user_id"):
                    log_data["user_id"] = record.user_id
                if hasattr(record, "request_id"):
                    log_data["request_id"] = record.request_id
                if hasattr(record, "duration_ms"):
                    log_data["duration_ms"] = record.duration_ms

                # Adicionar exception se houver
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_data)

        return JsonFormatter()

    def info(self, message: str, **kwargs):
        """Log INFO com campos extras"""
        extra = {k: v for k, v in kwargs.items()}
        self.logger.info(message, extra=extra)

    def error(self, message: str, **kwargs):
        """Log ERROR com campos extras"""
        extra = {k: v for k, v in kwargs.items()}
        self.logger.error(message, extra=extra, exc_info=True)

    def warning(self, message: str, **kwargs):
        """Log WARNING com campos extras"""
        extra = {k: v for k, v in kwargs.items()}
        self.logger.warning(message, extra=extra)


logger = StructuredLogger(__name__)


# ============================================================================
# PILAR 2: METRICS (Prometheus)
# ============================================================================

class AppMetrics:
    """
    Métricas Prometheus para observabilidade

    Tipos de métricas:
    1. Counter: sempre aumenta (ex: total de requests)
    2. Gauge: pode subir/descer (ex: conexões ativas)
    3. Histogram: distribuição de valores (ex: latência)
    4. Summary: similar a histogram, com quantiles
    """

    def __init__(self):
        # Counter: Total de requests
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total de requests HTTP",
            ["method", "endpoint", "status"]
        )

        # Histogram: Latência de requests
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "Duração de requests HTTP em segundos",
            ["method", "endpoint"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)  # Buckets customizados
        )

        # Counter: Erros
        self.http_errors_total = Counter(
            "http_errors_total",
            "Total de erros HTTP",
            ["method", "endpoint", "status"]
        )

        # Gauge: Conexões ativas no banco
        self.db_connections_active = Gauge(
            "db_connections_active",
            "Número de conexões ativas no banco de dados"
        )

        # Histogram: Latência de queries
        self.db_query_duration_seconds = Histogram(
            "db_query_duration_seconds",
            "Duração de queries no banco em segundos",
            ["query_type"]
        )

        # Counter: Cache hits/misses
        self.cache_hits_total = Counter(
            "cache_hits_total",
            "Total de cache hits"
        )

        self.cache_misses_total = Counter(
            "cache_misses_total",
            "Total de cache misses"
        )

        # Gauge: Uso de memória (simulated)
        self.memory_usage_bytes = Gauge(
            "memory_usage_bytes",
            "Uso de memória em bytes"
        )

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Registra métricas de uma request"""
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        self.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

        if status >= 400:
            self.http_errors_total.labels(method=method, endpoint=endpoint, status=status).inc()

    @contextmanager
    def track_db_query(self, query_type: str):
        """Context manager para rastrear latência de queries"""
        self.db_connections_active.inc()
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.db_query_duration_seconds.labels(query_type=query_type).observe(duration)
            self.db_connections_active.dec()


metrics = AppMetrics()


# ============================================================================
# PILAR 3: DISTRIBUTED TRACING (OpenTelemetry)
# ============================================================================

# Configurar OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Exportar spans para console (em produção: Jaeger, Zipkin, etc)
span_processor = BatchSpanProcessor(ConsoleSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)


def trace_operation(operation_name: str):
    """Decorator para adicionar tracing a funções"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(operation_name) as span:
                # Adicionar atributos ao span
                span.set_attribute("function", func.__name__)
                span.set_attribute("timestamp", datetime.utcnow().isoformat())

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(title="Observability Demo")

# Instrumentar FastAPI com OpenTelemetry
FastAPIInstrumentor.instrument_app(app)


# Middleware para rastrear todas as requests
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """
    Middleware que adiciona observabilidade a todas as requests

    - Gera request_id único
    - Registra log estruturado
    - Coleta métricas
    - Rastreia latência
    """
    import uuid

    # Gerar request_id (ou usar header X-Request-ID)
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Adicionar ao request state (disponível em toda a request)
    request.state.request_id = request_id

    # Log início da request
    logger.info(
        f"{request.method} {request.url.path}",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        user_agent=request.headers.get("user-agent")
    )

    # Medir latência
    start_time = time.time()

    # Processar request
    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Registrar métricas
        metrics.record_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration
        )

        # Log fim da request
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            request_id=request_id,
            status=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )

        # Adicionar headers de observabilidade
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response

    except Exception as e:
        duration = time.time() - start_time

        # Log erro
        logger.error(
            f"{request.method} {request.url.path} - ERROR",
            request_id=request_id,
            error=str(e),
            duration_ms=round(duration * 1000, 2)
        )

        # Métricas de erro
        metrics.record_request(
            method=request.method,
            endpoint=request.url.path,
            status=500,
            duration=duration
        )

        raise


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Endpoint raiz"""
    return {"message": "Observability Demo", "version": "1.0.0"}


@app.get("/users/{user_id}")
@trace_operation("get_user")
def get_user(user_id: int, request: Request):
    """
    Busca usuário (com tracing e metrics)

    Demonstra:
    - Distributed tracing com OpenTelemetry
    - Query tracking com métricas
    - Cache hit/miss metrics
    """
    request_id = request.state.request_id

    logger.info(f"Buscando usuário {user_id}", user_id=user_id, request_id=request_id)

    # Simular cache check
    cached_user = check_cache(user_id)
    if cached_user:
        metrics.cache_hits_total.inc()
        logger.info(f"Cache HIT para user {user_id}", user_id=user_id)
        return cached_user

    metrics.cache_misses_total.inc()
    logger.info(f"Cache MISS para user {user_id}", user_id=user_id)

    # Buscar no banco (com tracing)
    user = fetch_user_from_db(user_id)

    if not user:
        logger.warning(f"Usuário {user_id} não encontrado", user_id=user_id)
        raise HTTPException(404, "User not found")

    # Cachear resultado
    save_to_cache(user_id, user)

    return user


@trace_operation("check_cache")
def check_cache(user_id: int) -> Optional[Dict[str, Any]]:
    """Verifica cache (simulado)"""
    time.sleep(0.01)  # Simular latência do Redis

    # Simular: 70% cache hit
    import random
    if random.random() < 0.7:
        return {"id": user_id, "name": f"User {user_id}", "source": "cache"}

    return None


@trace_operation("fetch_user_from_db")
def fetch_user_from_db(user_id: int) -> Optional[Dict[str, Any]]:
    """Busca usuário no banco (simulado)"""

    # Rastrear query com métricas
    with metrics.track_db_query("select_user"):
        # Simular query lenta
        time.sleep(0.1)

        # Adicionar atributos ao span atual
        span = trace.get_current_span()
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", f"SELECT * FROM users WHERE id = {user_id}")
        span.set_attribute("db.operation", "SELECT")

        # Simular resultado
        if user_id < 1000:
            return {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}

        return None


@trace_operation("save_to_cache")
def save_to_cache(user_id: int, user: Dict[str, Any]):
    """Salva no cache (simulado)"""
    time.sleep(0.01)

    span = trace.get_current_span()
    span.set_attribute("cache.key", f"user:{user_id}")
    span.set_attribute("cache.ttl", 300)


@app.get("/slow")
def slow_endpoint():
    """Endpoint lento para demonstrar histogramas"""
    import random
    time.sleep(random.uniform(0.1, 3.0))  # 100ms a 3s
    return {"message": "This was slow"}


@app.get("/error")
def error_endpoint():
    """Endpoint que gera erro para demonstrar error tracking"""
    logger.error("Erro intencional para demonstração", extra={"intentional": True})
    raise HTTPException(500, "Intentional error for demo")


# ============================================================================
# HEALTH CHECKS
# ============================================================================

@app.get("/health")
def health_check():
    """
    Health check básico (liveness probe)

    Kubernetes usa isso para saber se pod está vivo
    Se retornar 200: pod OK
    Se retornar 500: reiniciar pod
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
def readiness_check():
    """
    Readiness check (readiness probe)

    Kubernetes usa isso para saber se pod pode receber tráfego
    Checks:
    - Banco conectado?
    - Cache conectado?
    - Dependências respondendo?
    """
    checks = {
        "database": check_database(),
        "cache": check_cache_connection(),
        "external_api": check_external_api()
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return Response(
        content=json.dumps({
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }),
        status_code=status_code,
        media_type="application/json"
    )


def check_database() -> bool:
    """Verifica se banco está respondendo"""
    # Em produção: executar SELECT 1
    return True


def check_cache_connection() -> bool:
    """Verifica se cache está respondendo"""
    # Em produção: executar PING no Redis
    return True


def check_external_api() -> bool:
    """Verifica se APIs externas estão respondendo"""
    # Em produção: fazer request com timeout curto
    return True


# ============================================================================
# METRICS ENDPOINT
# ============================================================================

@app.get("/metrics")
def metrics_endpoint():
    """
    Endpoint de métricas Prometheus

    Prometheus faz scrape desse endpoint a cada X segundos
    Formato: texto plano com métricas

    Configure Prometheus:
      scrape_configs:
        - job_name: 'fastapi'
          static_configs:
            - targets: ['localhost:8000']
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ============================================================================
# DASHBOARD SIMULADO
# ============================================================================

@app.get("/dashboard")
def dashboard():
    """
    Dashboard simulado mostrando métricas em tempo real

    Em produção: use Grafana com Prometheus datasource
    """
    import psutil

    # Coletar métricas do sistema
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Atualizar gauge de memória
    metrics.memory_usage_bytes.set(memory.used)

    dashboard_data = {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        },
        "application": {
            "active_db_connections": metrics.db_connections_active._value.get(),
        },
        "links": {
            "metrics": "/metrics",
            "health": "/health",
            "readiness": "/health/ready"
        }
    }

    return dashboard_data


# ============================================================================
# ALERTING (Conceitual)
# ============================================================================

def print_alerting_examples():
    """
    Exemplos de alertas Prometheus

    Alertas são definidos em prometheus.yml e avaliados pelo Alertmanager
    """
    alerts = """
═══════════════════════════════════════════════════════════════════════════
                          EXEMPLOS DE ALERTAS
═══════════════════════════════════════════════════════════════════════════

# prometheus/alerts.yml

groups:
  - name: application_alerts
    interval: 30s
    rules:

      # Alert: Taxa de erro alta
      - alert: HighErrorRate
        expr: |
          sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Taxa de erro acima de 5%"
          description: "{{ $value | humanizePercentage }} dos requests estão falhando"

      # Alert: Latência alta
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Latência P95 acima de 1 segundo"
          description: "P95 latency is {{ $value }}s"

      # Alert: Banco de dados lento
      - alert: SlowDatabaseQueries
        expr: |
          histogram_quantile(0.95, db_query_duration_seconds_bucket) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Queries lentas detectadas"
          description: "P95 query time is {{ $value }}s"

      # Alert: Muitas conexões no banco
      - alert: HighDatabaseConnections
        expr: db_connections_active > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Muitas conexões ativas no banco"
          description: "{{ $value }} conexões ativas (max: 100)"

      # Alert: Cache miss rate alto
      - alert: HighCacheMissRate
        expr: |
          rate(cache_misses_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Taxa de cache miss acima de 50%"
          description: "Cache pode estar ineficiente ou Redis pode estar com problemas"

      # Alert: Serviço não saudável
      - alert: ServiceDown
        expr: up{job="fastapi"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Serviço não está respondendo"
          description: "Prometheus não consegue fazer scrape do /metrics"

      # Alert: Alto uso de memória
      - alert: HighMemoryUsage
        expr: memory_usage_bytes / 1024 / 1024 / 1024 > 8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Uso de memória acima de 8GB"
          description: "Aplicação usando {{ $value }}GB de memória"

═══════════════════════════════════════════════════════════════════════════
                    ALERTMANAGER CONFIGURATION
═══════════════════════════════════════════════════════════════════════════

# alertmanager.yml

global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'slack'

  routes:
    # Alertas críticos vão para PagerDuty + Slack
    - match:
        severity: critical
      receiver: 'pagerduty'

    # Warnings só Slack
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\\n{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'

═══════════════════════════════════════════════════════════════════════════
"""
    return alerts


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║          MÓDULO 07: OBSERVABILIDADE E MONITORAMENTO                      ║
║     3 Pilares: Logs, Metrics, Traces (OpenTelemetry + Prometheus)       ║
╚══════════════════════════════════════════════════════════════════════════╝

🚀 Iniciando servidor FastAPI com observabilidade...

📊 ENDPOINTS DISPONÍVEIS:

1. Aplicação:
   - GET  http://localhost:8000/
   - GET  http://localhost:8000/users/123
   - GET  http://localhost:8000/slow       (latência variável)
   - GET  http://localhost:8000/error      (gera erro)

2. Observabilidade:
   - GET  http://localhost:8000/metrics    (Prometheus metrics)
   - GET  http://localhost:8000/dashboard  (métricas em tempo real)

3. Health Checks:
   - GET  http://localhost:8000/health       (liveness probe)
   - GET  http://localhost:8000/health/ready (readiness probe)

💡 TESTANDO:

# Gerar tráfego
for i in {1..100}; do curl http://localhost:8000/users/$i; done

# Ver métricas Prometheus
curl http://localhost:8000/metrics

# Ver dashboard
curl http://localhost:8000/dashboard | jq

═══════════════════════════════════════════════════════════════════════════

📚 3 PILARES DA OBSERVABILIDADE:

1️⃣  LOGS (O QUE aconteceu?)
   - Structured logging (JSON)
   - Campos contextuais (request_id, user_id)
   - Níveis: DEBUG, INFO, WARNING, ERROR
   - Integração: ELK, Datadog, CloudWatch

2️⃣  METRICS (COM QUE FREQUÊNCIA? QUANTO?)
   - Counter: sempre aumenta (total requests)
   - Gauge: pode subir/descer (conexões ativas)
   - Histogram: distribuição (latência)
   - Prometheus + Grafana

3️⃣  TRACES (ONDE gastou tempo?)
   - Distributed tracing
   - Spans: unidade de trabalho
   - Visualizar fluxo de requests
   - Jaeger, Zipkin, Tempo

═══════════════════════════════════════════════════════════════════════════
""")

    print("\n🔍 Exemplos de alertas:")
    print(print_alerting_examples())

    print("\n🚀 Iniciando servidor...\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
