# Módulo 07 - Cloud e High-Level Architecture

## 🎯 Objetivo

Desenhar e implementar sistemas distribuídos escaláveis em cloud.

---

## 📚 Conteúdo

### 1. Cloud Providers - Serviços Essenciais

```
┌────────────────────────────────────────────────────────┐
│                   CLOUD SERVICES                       │
├─────────────┬──────────────┬──────────────┬───────────┤
│   AWS       │   GCP        │   Azure      │  Uso      │
├─────────────┼──────────────┼──────────────┼───────────┤
│ EC2         │ Compute Eng. │ VMs          │ Servers   │
│ ECS/EKS     │ GKE          │ AKS          │ K8s       │
│ Lambda      │ Cloud Func.  │ Functions    │ Serverless│
│ RDS         │ Cloud SQL    │ SQL Database │ DB        │
│ S3          │ Cloud Storage│ Blob Storage │ Files     │
│ CloudFront  │ Cloud CDN    │ CDN          │ CDN       │
│ SQS/SNS     │ Pub/Sub      │ Service Bus  │ Queues    │
│ CloudWatch  │ Monitoring   │ Monitor      │ Observ.   │
└─────────────┴──────────────┴──────────────┴───────────┘
```

---

## 2. Containerization - Docker

### Dockerfile para FastAPI

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY ./app ./app

# Criar usuário não-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose (Desenvolvimento)

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./app:/app/app  # Hot reload
    command: uvicorn app.main:app --reload --host 0.0.0.0

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: myapp
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info
    depends_on:
      - redis
      - db

volumes:
  postgres_data:
  redis_data:
```

---

## 3. Kubernetes (K8s)

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3  # 3 instâncias
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: myapp:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer

---
# autoscaling.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 4. CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run linters
        run: |
          black --check .
          isort --check .
          flake8 .

      - name: Run tests
        run: |
          pytest --cov=app tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          docker build -t myapp:${{ github.sha }} .

      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push myapp:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to K8s
        run: |
          kubectl set image deployment/api api=myapp:${{ github.sha }}
          kubectl rollout status deployment/api
```

---

## 5. Observability (Logs, Metrics, Traces)

### Logging Estruturado

```python
import structlog
import logging

# Configurar structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Uso
logger.info(
    "user_created",
    user_id=123,
    email="user@example.com",
    ip="192.168.1.1"
)
# Output: {"event": "user_created", "user_id": 123, "email": "...", "timestamp": "..."}
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import FastAPI, Response

app = FastAPI()

# Métricas
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    with REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).time():
        response = await call_next(request)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Distributed Tracing (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Configurar
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Instrumentar FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Uso manual
tracer = trace.get_tracer(__name__)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    with tracer.start_as_current_span("get_user_from_db"):
        user = await db.get(user_id)

    with tracer.start_as_current_span("fetch_user_posts"):
        posts = await db.get_posts(user_id)

    return {"user": user, "posts": posts}
```

---

## 6. High-Level Architecture Patterns

### Load Balancer + Auto Scaling

```
                  ┌─────────────┐
                  │Load Balancer│
                  │   (Nginx)   │
                  └──────┬──────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐      ┌───▼─────┐     ┌───▼─────┐
   │  API 1  │      │  API 2  │     │  API 3  │
   │ (Pod)   │      │ (Pod)   │     │ (Pod)   │
   └────┬────┘      └────┬────┘     └────┬────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                  ┌──────▼──────┐
                  │  Database   │
                  │ (PostgreSQL)│
                  └─────────────┘
```

### Microservices com Service Mesh

```
┌─────────────────────────────────────────────────┐
│             Service Mesh (Istio)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Users   │  │  Posts   │  │  Media   │     │
│  │ Service  │←→│ Service  │←→│ Service  │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │            │
│  ┌────▼─────┐  ┌───▼──────┐  ┌──▼──────┐     │
│  │ Users DB │  │ Posts DB │  │ S3      │     │
│  └──────────┘  └──────────┘  └─────────┘     │
└─────────────────────────────────────────────────┘

Service Mesh provê:
- Service discovery
- Load balancing
- Circuit breaking
- Retry logic
- Observability
```

### Circuit Breaker

```python
from pybreaker import CircuitBreaker

# Configurar circuit breaker
breaker = CircuitBreaker(
    fail_max=5,           # Abrir após 5 falhas
    timeout_duration=60,  # Tentar novamente após 60s
)

@breaker
def call_external_api():
    response = requests.get("https://api.example.com/data", timeout=5)
    return response.json()

# Uso
try:
    data = call_external_api()
except CircuitBreakerError:
    # Circuit aberto, usar fallback
    data = get_cached_data()
```

---

## 7. Deployment Strategies

### Blue-Green Deployment

```
┌─────────────────────────────────────┐
│  Load Balancer                      │
└───────┬─────────────────────────────┘
        │
        ├──> Blue (v1.0) - 100% tráfego
        │    ┌────────┐ ┌────────┐
        │    │ Pod v1 │ │ Pod v1 │
        │    └────────┘ └────────┘
        │
        └──> Green (v2.0) - 0% tráfego
             ┌────────┐ ┌────────┐
             │ Pod v2 │ │ Pod v2 │
             └────────┘ └────────┘

Deploy: Switch tráfego para Green
Rollback: Switch de volta para Blue
```

### Canary Release

```yaml
# 90% tráfego para v1, 10% para v2
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  selector:
    app: api
  ports:
  - port: 80

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-v1
spec:
  replicas: 9  # 90%
  template:
    metadata:
      labels:
        app: api
        version: v1

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-v2
spec:
  replicas: 1  # 10%
  template:
    metadata:
      labels:
        app: api
        version: v2
```

---

## 8. Infrastructure as Code (Terraform)

```hcl
# main.tf
provider "aws" {
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "my-cluster"
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids = aws_subnet.private[*].id
  }
}

# RDS Database
resource "aws_db_instance" "main" {
  identifier        = "mydb"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.medium"
  allocated_storage = 100

  username = var.db_username
  password = var.db_password

  backup_retention_period = 7
  multi_az               = true
}

# S3 Bucket
resource "aws_s3_bucket" "media" {
  bucket = "my-media-bucket"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    enabled = true

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}
```

---

## 🎓 Checklist de Produção

### Security:
- [ ] HTTPS/TLS em todas APIs
- [ ] Secrets gerenciados (AWS Secrets Manager, K8s Secrets)
- [ ] Princípio de menor privilégio (IAM)
- [ ] Network policies (firewalls, security groups)
- [ ] Rate limiting e DDoS protection

### Reliability:
- [ ] Multi-AZ deployment
- [ ] Backups automáticos
- [ ] Health checks configurados
- [ ] Circuit breakers implementados
- [ ] Disaster recovery plan

### Observability:
- [ ] Logging estruturado (ELK, CloudWatch)
- [ ] Métricas (Prometheus, Datadog)
- [ ] Distributed tracing (Jaeger, Zipkin)
- [ ] Alertas configurados
- [ ] Dashboards

### Performance:
- [ ] CDN para assets estáticos
- [ ] Cache distribuído (Redis, CloudFront)
- [ ] Auto-scaling configurado
- [ ] Load balancing
- [ ] Database replication

### DevOps:
- [ ] CI/CD pipeline
- [ ] Infrastructure as Code
- [ ] Blue-green ou canary deployment
- [ ] Rollback automático
- [ ] Feature flags

---

## 🏗️ Arquitetura Exemplo - Rede Social

```
┌─────────────────────────────────────────────────────────────┐
│                    CloudFront CDN                           │
└───────────┬─────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────┐
│                 Application Load Balancer                    │
└───┬───────────────┬──────────────────┬──────────────────────┘
    │               │                  │
┌───▼────┐    ┌────▼─────┐      ┌─────▼──────┐
│ API    │    │ API      │      │ API        │
│ Server │    │ Server   │      │ Server     │
│ (K8s)  │    │ (K8s)    │      │ (K8s)      │
└───┬────┘    └────┬─────┘      └─────┬──────┘
    │              │                   │
    ├──────────────┼───────────────────┤
    │              │                   │
┌───▼──────────────▼───────────────────▼───┐
│           Redis Cluster (Cache)          │
└──────────────────┬───────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
┌───────▼───┐ ┌───▼──────┐ ┌─▼────────┐
│PostgreSQL │ │  S3      │ │ ElasticS.│
│ (Primary) │ │ (Media)  │ │ (Search) │
│           │ │          │ │          │
└─────┬─────┘ └──────────┘ └──────────┘
      │
┌─────▼─────┐
│PostgreSQL │
│ (Replica) │
└───────────┘
```

---

## 📝 Próximos Passos

1. Implementar no **[Projeto Prático - Exercício 12](../../projeto-pratico/exercicio-12-cloud/)**
2. Revisar todos os módulos anteriores
3. Construir seu próprio projeto aplicando todos os conceitos!

---

**Parabéns!** 🎉 Você completou todos os módulos teóricos. Agora é hora de aplicar tudo no projeto prático!
