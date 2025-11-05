# 🚀 Guia Completo de CI/CD

> Continuous Integration e Continuous Deployment para aplicações backend.

---

## 📋 Índice

- [O que é CI/CD](#o-que-é-cicd)
- [GitHub Actions](#github-actions)
- [Docker Multi-stage](#docker-multi-stage)
- [Deployment Strategies](#deployment-strategies)
- [Secrets Management](#secrets-management)
- [Monitoring](#monitoring)

---

## 🎯 O que é CI/CD?

### Continuous Integration (CI)

**O quê:** Integrar código frequentemente (várias vezes ao dia)

**Como:**
1. Developer faz push para branch
2. CI roda automaticamente:
   - Linter (código limpo?)
   - Tests (tudo passa?)
   - Build (compila?)
   - Security scan (vulnerabilidades?)

**Benefícios:**
- ✅ Detecta bugs cedo (barato de consertar)
- ✅ Feedback rápido (minutos, não dias)
- ✅ Menos conflitos de merge

---

### Continuous Deployment (CD)

**O quê:** Deploy automático após CI passar

**Como:**
1. CI passa com sucesso
2. Build Docker image
3. Push para registry (Docker Hub, ECR)
4. Deploy para ambiente:
   - Staging (automático)
   - Production (manual approval ou automático)

**Benefícios:**
- ✅ Deploy rápido (minutos, não horas)
- ✅ Menos erro humano
- ✅ Rollback fácil

---

## ⚙️ GitHub Actions

### Estrutura Básica

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest
```

---

### Pipeline Completo

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  DOCKER_IMAGE: myapp/backend

jobs:
  # ========================================================================
  # JOB 1: LINT
  # ========================================================================
  lint:
    name: Lint Code
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install black flake8 isort mypy

      - name: Run Black (formatter)
        run: black --check .

      - name: Run Flake8 (linter)
        run: flake8 app tests --max-line-length=100

      - name: Run isort (import sorter)
        run: isort --check-only app tests

      - name: Run mypy (type checker)
        run: mypy app --ignore-missing-imports

  # ========================================================================
  # JOB 2: SECURITY SCAN
  # ========================================================================
  security:
    name: Security Scan
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Run Bandit (security linter)
        run: |
          pip install bandit
          bandit -r app -f json -o bandit-report.json

      - name: Run Safety (dependency check)
        run: |
          pip install safety
          safety check --json

      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            bandit-report.json

  # ========================================================================
  # JOB 3: TESTS
  # ========================================================================
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    # Services (databases, cache, etc)
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        run: |
          pytest tests/unit -v \
            --cov=app \
            --cov-report=xml \
            --cov-report=term-missing

      - name: Run integration tests
        run: |
          pytest tests/integration -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0

      - name: Run E2E tests
        run: |
          pytest tests/e2e -v --maxfail=5
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

  # ========================================================================
  # JOB 4: BUILD DOCKER IMAGE
  # ========================================================================
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [lint, security, test]  # Só roda se testes passarem

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.DOCKER_IMAGE }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.DOCKER_IMAGE }}:buildcache
          cache-to: type=registry,ref=${{ env.DOCKER_IMAGE }}:buildcache,mode=max

  # ========================================================================
  # JOB 5: DEPLOY TO STAGING
  # ========================================================================
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'  # Só deploy de develop
    environment: staging  # Proteção de environment

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to staging server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /app
            docker-compose pull
            docker-compose up -d
            docker-compose exec -T app python manage.py migrate

      - name: Run smoke tests
        run: |
          sleep 10
          curl -f https://staging.myapp.com/health || exit 1

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Staging deployment completed'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

  # ========================================================================
  # JOB 6: DEPLOY TO PRODUCTION
  # ========================================================================
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'  # Só deploy de main
    environment:
      name: production
      url: https://myapp.com

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to production (Blue-Green)
        run: |
          # Lógica de blue-green deployment
          # Ver seção "Deployment Strategies"

      - name: Run smoke tests
        run: |
          sleep 30
          curl -f https://myapp.com/health || exit 1

      - name: Notify team
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: '🚀 Production deployment completed!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 🐳 Docker Multi-stage Build

### Dockerfile Otimizado

```dockerfile
# syntax=docker/dockerfile:1

# ============================================================================
# STAGE 1: Builder (instalar dependências)
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python em /install
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# STAGE 2: Runtime (imagem final)
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Copiar apenas dependências compiladas (não build tools)
COPY --from=builder /root/.local /root/.local

# Copiar código da aplicação
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# Criar user não-root (segurança)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# PATH para acessar dependências
ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Benefícios:**
- ✅ Imagem final pequena (~200MB vs ~1GB)
- ✅ Sem build tools em produção (segurança)
- ✅ Cache de layers (build rápido)

---

### docker-compose para CI/CD

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: myapp/backend:${TAG:-latest}
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s

  db:
    image: postgres:15
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

  redis:
    image: redis:alpine
    restart: always
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

---

## 🎯 Deployment Strategies

### 1. Rolling Deployment (Padrão)

```yaml
# Atualiza instâncias uma por vez
# Downtime: Nenhum
# Rollback: Fácil

- name: Rolling deployment
  run: |
    for i in {1..3}; do
      ssh server$i "docker-compose pull && docker-compose up -d"
      sleep 30  # Esperar health check
    done
```

---

### 2. Blue-Green Deployment

```yaml
# Duas versões completas: Blue (atual) e Green (nova)
# Switch instantâneo via load balancer
# Downtime: Zero
# Rollback: Instantâneo

- name: Blue-Green deployment
  run: |
    # Deploy para ambiente green
    ssh green-server "docker-compose up -d"

    # Esperar health check
    sleep 30
    curl -f https://green.myapp.com/health

    # Switch load balancer: Blue → Green
    aws elbv2 modify-target-group \
      --target-group-arn $TG_ARN \
      --health-check-path /health

    # Esperar 5 min para garantir estabilidade
    sleep 300

    # Desligar blue (manter para rollback rápido)
    # ssh blue-server "docker-compose down"
```

---

### 3. Canary Deployment

```yaml
# Deploy gradual: 5% → 25% → 50% → 100%
# Monitora métricas em cada etapa
# Rollback automático se métricas ruins

- name: Canary deployment
  run: |
    # 5% do tráfego para nova versão
    kubectl set image deployment/app app=myapp:$TAG
    kubectl scale deployment/app-canary --replicas=1

    # Monitorar por 10 min
    sleep 600
    ERROR_RATE=$(curl metrics/error_rate)

    if [ $ERROR_RATE -gt 1 ]; then
      echo "Error rate too high! Rolling back..."
      kubectl rollout undo deployment/app-canary
      exit 1
    fi

    # 50% do tráfego
    kubectl scale deployment/app-canary --replicas=5

    # Monitorar...
    # 100%: Promover canary para stable
```

---

## 🔐 Secrets Management

### GitHub Secrets

```yaml
# Configurar em: Settings → Secrets and variables → Actions

secrets:
  - DOCKER_USERNAME
  - DOCKER_PASSWORD
  - DATABASE_URL
  - SECRET_KEY
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
```

### Usar Secrets no Workflow

```yaml
- name: Deploy
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
    SECRET_KEY: ${{ secrets.SECRET_KEY }}
  run: |
    docker-compose up -d
```

### Vault (Produção)

```yaml
# HashiCorp Vault para produção
- name: Get secrets from Vault
  uses: hashicorp/vault-action@v2
  with:
    url: https://vault.myapp.com
    token: ${{ secrets.VAULT_TOKEN }}
    secrets: |
      secret/data/prod/db password | DATABASE_PASSWORD
      secret/data/prod/api key | API_KEY
```

---

## 📊 Monitoring no CI/CD

### Métricas Importantes

```yaml
- name: Check deployment metrics
  run: |
    # Error rate
    ERROR_RATE=$(curl -s https://myapp.com/metrics | \
      grep error_rate | awk '{print $2}')

    if [ $(echo "$ERROR_RATE > 0.01" | bc) -eq 1 ]; then
      echo "Error rate too high: $ERROR_RATE"
      exit 1
    fi

    # Response time P95
    P95=$(curl -s https://myapp.com/metrics | \
      grep response_time_p95 | awk '{print $2}')

    if [ $(echo "$P95 > 1000" | bc) -eq 1 ]; then
      echo "P95 latency too high: ${P95}ms"
      exit 1
    fi
```

### Notificações

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: |
      ❌ Deployment failed!
      Branch: ${{ github.ref }}
      Commit: ${{ github.sha }}
      Author: ${{ github.actor }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}

- name: Notify on success
  if: success()
  run: |
    curl -X POST https://api.pagerduty.com/incidents \
      -H "Authorization: Token ${{ secrets.PAGERDUTY_TOKEN }}" \
      -d '{"incident": {"type": "incident", "title": "Deployment successful"}}'
```

---

## 🎯 Best Practices

### ✅ DO

1. **Rodar CI em todos os PRs**
```yaml
on:
  pull_request:
    branches: [main, develop]
```

2. **Fail fast**
```yaml
jobs:
  test:
    strategy:
      fail-fast: true  # Parar todos se um falhar
```

3. **Cache dependencies**
```yaml
- uses: actions/setup-python@v4
  with:
    cache: 'pip'  # Cache automático
```

4. **Matrix testing**
```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
    os: [ubuntu-latest, macos-latest]
```

5. **Environments com approval**
```yaml
environment:
  name: production
  # Requer aprovação manual
```

6. **Rollback automático**
```yaml
- name: Rollback on failure
  if: failure()
  run: |
    kubectl rollout undo deployment/app
```

---

### ❌ DON'T

1. **Secrets em código**
```yaml
# ❌ NUNCA
env:
  SECRET_KEY: "hardcoded-secret-key-123"

# ✅ USE
env:
  SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

2. **Deploy sem testes**
```yaml
# ❌ Deploy direto
deploy:
  steps: ...

# ✅ Testes antes
deploy:
  needs: [lint, test]  # Só deploy se passar
```

3. **Builds longos**
```yaml
# ❌ Rebuild tudo sempre (lento)

# ✅ Use cache
- uses: docker/build-push-action@v4
  with:
    cache-from: type=registry,ref=myapp:buildcache
```

---

## 📊 Pipeline Stages Típicas

```
┌──────────┐
│  Commit  │
└────┬─────┘
     │
     ▼
┌──────────┐
│   Lint   │  ~30s  - Black, Flake8, isort, mypy
└────┬─────┘
     │
     ▼
┌──────────┐
│ Security │  ~1min - Bandit, Safety, SAST
└────┬─────┘
     │
     ▼
┌──────────┐
│  Tests   │  ~3min - Unit, Integration, E2E
└────┬─────┘
     │
     ▼
┌──────────┐
│  Build   │  ~2min - Docker image
└────┬─────┘
     │
     ▼
┌──────────┐
│  Deploy  │  ~5min - Blue-green, Health checks
└────┬─────┘
     │
     ▼
┌──────────┐
│ Monitor  │  ~10min - Observar métricas
└──────────┘

Total: ~20min (main → production)
```

---

## 🎓 Exemplo Completo

Ver:
- `.github/workflows/ci-cd.yml` (neste repo)
- `Dockerfile` (multi-stage build)
- `docker-compose.prod.yml` (produção)
- `k8s/` (Kubernetes manifests)

---

## 📚 Recursos

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [The Twelve-Factor App](https://12factor.net/)
- [Google SRE Book](https://sre.google/books/)

---

**Deploy com confiança! 🚀✨**
