# Backend Best Practices - Guia Completo

> Consolidação das melhores práticas de desenvolvimento backend, do básico ao avançado.

---

## 📚 Índice

1. [Arquitetura e Design](#1-arquitetura-e-design)
2. [Banco de Dados](#2-banco-de-dados)
3. [APIs e Endpoints](#3-apis-e-endpoints)
4. [Performance](#4-performance)
5. [Segurança](#5-segurança)
6. [Testes](#6-testes)
7. [Código Limpo](#7-código-limpo)
8. [DevOps e Deploy](#8-devops-e-deploy)
9. [Monitoramento](#9-monitoramento)
10. [Escalabilidade](#10-escalabilidade)

---

## 1. Arquitetura e Design

### 1.1 Estrutura de Projetos

```
✅ BOM - Separação clara de responsabilidades
app/
├── api/              # Controllers/Endpoints
├── models/           # Database models
├── schemas/          # Pydantic/validation
├── repositories/     # Data access
├── services/         # Business logic
├── core/             # Config, security, utils
└── tests/            # Testes

❌ RUIM - Tudo misturado
app/
├── main.py           # 2000 linhas com tudo
├── utils.py          # 1000 linhas de funções random
└── models.py         # Models + logic + API
```

### 1.2 Separação de Responsabilidades

```python
# ✅ BOM - Camadas bem definidas

# Repository: Acesso a dados
class UserRepository:
    def get_by_email(self, email: str) -> User:
        return db.query(User).filter(User.email == email).first()

# Service: Lógica de negócio
class UserService:
    def create_user(self, data: UserCreate) -> User:
        # Validações de negócio
        if self.repository.exists_by_email(data.email):
            raise ValueError("Email já existe")

        # Criar usuário
        return self.repository.create(data)

# Controller: HTTP handling
@router.post("/users")
def create_user_endpoint(data: UserCreate):
    try:
        user = user_service.create_user(data)
        return user
    except ValueError as e:
        raise HTTPException(400, str(e))


# ❌ RUIM - Tudo no endpoint
@router.post("/users")
def create_user(data: dict):
    # Validação
    if not "@" in data["email"]:
        return {"error": "Email inválido"}

    # Verificar duplicata
    existing = db.query(User).filter(User.email == data["email"]).first()
    if existing:
        return {"error": "Email existe"}

    # Hash senha
    hashed = bcrypt.hash(data["password"])

    # Criar
    user = User(email=data["email"], password=hashed)
    db.add(user)
    db.commit()

    return user
```

### 1.3 Dependency Injection

```python
# ✅ BOM - Dependências injetadas (testável)
class UserService:
    def __init__(self, repository: UserRepository, email_service: EmailService):
        self.repository = repository
        self.email_service = email_service

    def create_user(self, data: UserCreate):
        user = self.repository.create(data)
        self.email_service.send_welcome(user.email)
        return user

# Teste fácil
def test_create_user():
    mock_repo = Mock()
    mock_email = Mock()
    service = UserService(mock_repo, mock_email)
    # Testar sem banco real!


# ❌ RUIM - Dependências hardcoded (não testável)
class UserService:
    def create_user(self, data: UserCreate):
        repository = UserRepository()  # Hard-coded!
        email_service = EmailService()  # Hard-coded!
        # Impossível testar sem banco e email reais
```

---

## 2. Banco de Dados

### 2.1 Evite N+1 Queries

```python
# ❌ RUIM - N+1 queries
posts = db.query(Post).limit(10).all()
for post in posts:
    print(post.author.name)  # Query para cada post!
# Total: 11 queries (1 + 10)

# ✅ BOM - Eager loading
posts = db.query(Post).options(
    joinedload(Post.author)
).limit(10).all()
for post in posts:
    print(post.author.name)  # Sem query adicional!
# Total: 1 query
```

### 2.2 Indexes Sempre em Foreign Keys

```python
# ✅ BOM - Index em FK
class Post(Base):
    user_id = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (
        Index('idx_posts_user_id', 'user_id'),  # Index!
    )

# ❌ RUIM - Sem index
class Post(Base):
    user_id = Column(Integer, ForeignKey("users.id"))
    # Queries WHERE user_id = X serão lentas!
```

### 2.3 Use Cursor-based Pagination

```python
# ❌ RUIM - OFFSET (lento em páginas altas)
posts = db.query(Post).offset(10000).limit(20).all()
# Lê 10020 linhas e descarta 10000!

# ✅ BOM - Cursor-based
posts = db.query(Post).filter(
    Post.id > last_id  # Cursor
).limit(20).all()
# Lê apenas 20 linhas!
```

### 2.4 Connection Pooling

```python
# ✅ BOM - Pool configurado
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # 20 conexões reutilizáveis
    max_overflow=10,        # Até 30 no total
    pool_pre_ping=True,     # Valida antes de usar
    pool_recycle=3600,      # Recicla após 1h
)

# ❌ RUIM - Nova conexão por request
def get_user(user_id):
    engine = create_engine(DATABASE_URL)  # Lento!
    # ...
```

### 2.5 Transactions

```python
# ✅ BOM - Transaction para operações relacionadas
def transfer_money(from_id, to_id, amount):
    with db.begin():  # Transaction
        from_account = db.query(Account).get(from_id)
        to_account = db.query(Account).get(to_id)

        from_account.balance -= amount
        to_account.balance += amount

        db.flush()
        # Se algo der errado, rollback automático

# ❌ RUIM - Sem transaction
def transfer_money(from_id, to_id, amount):
    from_account = db.query(Account).get(from_id)
    from_account.balance -= amount
    db.commit()  # Se falhar aqui, dinheiro sumiu!

    to_account = db.query(Account).get(to_id)
    to_account.balance += amount
    db.commit()
```

---

## 3. APIs e Endpoints

### 3.1 Use Status Codes Corretos

```python
# ✅ BOM - Status codes semânticos
@router.post("/users", status_code=201)  # Created
def create_user(data: UserCreate):
    user = service.create(data)
    return user

@router.get("/users/{user_id}")
def get_user(user_id: int):
    user = service.get(user_id)
    if not user:
        raise HTTPException(404)  # Not Found
    return user

@router.put("/users/{user_id}")
def update_user(user_id: int, data: UserUpdate):
    user = service.update(user_id, data)
    if not user:
        raise HTTPException(404)
    return user  # 200 OK

@router.delete("/users/{user_id}", status_code=204)  # No Content
def delete_user(user_id: int):
    service.delete(user_id)
    return None  # Sem corpo

# ❌ RUIM - Sempre 200
@router.post("/users")
def create_user(data: dict):
    if error:
        return {"error": "Email existe"}  # Deveria ser 400!
    return {"user": user}  # Deveria ser 201!
```

### 3.2 Validação com Pydantic

```python
# ✅ BOM - Validação automática
class UserCreate(BaseModel):
    email: EmailStr  # Valida formato
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)

    @validator('password')
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Precisa de maiúscula')
        return v

@router.post("/users")
def create_user(data: UserCreate):  # Auto-validado!
    # Se chegar aqui, dados são válidos


# ❌ RUIM - Validação manual
@router.post("/users")
def create_user(data: dict):
    if not "@" in data.get("email", ""):
        raise HTTPException(400, "Email inválido")
    if len(data.get("username", "")) < 3:
        raise HTTPException(400, "Username curto")
    # ... muitas validações
```

### 3.3 Versionamento de API

```python
# ✅ BOM - Versão na URL
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(api_v2_router, prefix="/api/v2")

# GET /api/v1/users  → Versão antiga
# GET /api/v2/users  → Versão nova

# ⚠️ Alternativa - Header
# GET /api/users
# Header: Accept: application/vnd.api+json;version=1

# ❌ RUIM - Sem versionamento
# GET /api/users
# (Impossível fazer breaking changes!)
```

### 3.4 Response Padronizado

```python
# ✅ BOM - Formato consistente
{
  "data": {...},
  "meta": {
    "page": 1,
    "total": 100
  }
}

# Erro também padronizado
{
  "error": {
    "code": "EMAIL_EXISTS",
    "message": "Email já está em uso",
    "field": "email"
  }
}

# ❌ RUIM - Formatos inconsistentes
# Sucesso:
{"user": {...}}

# Erro:
{"error": "Email existe"}

# Outro erro:
{"message": "Not found", "code": 404}
```

---

## 4. Performance

### 4.1 Use Async Onde Apropriado

```python
# ✅ BOM - Async para I/O-bound
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await user_service.get(user_id)  # DB async
    posts = await post_service.get_by_user(user_id)  # DB async
    return {"user": user, "posts": posts}

# Para CPU-bound, use multiprocessing
from concurrent.futures import ProcessPoolExecutor
executor = ProcessPoolExecutor()

@router.post("/process-video")
async def process_video(video_id: int):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        heavy_cpu_task,
        video_id
    )
    return result
```

### 4.2 Caching

```python
# ✅ BOM - Cache em queries pesadas
import redis
r = redis.Redis()

def get_user_stats(user_id: int):
    cache_key = f"user_stats:{user_id}"

    # Tentar cache
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # Cache miss → calcular
    stats = calculate_user_stats(user_id)  # Lento!

    # Salvar no cache (1 hora)
    r.setex(cache_key, 3600, json.dumps(stats))

    return stats

# ❌ RUIM - Sem cache
def get_user_stats(user_id: int):
    return calculate_user_stats(user_id)  # Lento toda vez!
```

### 4.3 Rate Limiting

```python
# ✅ BOM - Proteger endpoints
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/upload")
@limiter.limit("10/minute")  # Max 10 requests/min
async def upload_file(file: UploadFile):
    # ...

# ❌ RUIM - Sem rate limit
# (Vulnerável a abuse/DDoS)
```

### 4.4 Compression

```python
# ✅ BOM - Comprimir responses
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
# Responses > 1KB são comprimidos automaticamente

# JSON de 100KB → 20KB após gzip (80% redução)
```

---

## 5. Segurança

### 5.1 NUNCA Armazene Senhas em Plain Text

```python
# ✅ BOM - Hash com bcrypt/argon2
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

def create_user(email, password):
    hashed = pwd_context.hash(password)  # Hash!
    user = User(email=email, password=hashed)
    # ...

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


# ❌ RUIM - Plain text
def create_user(email, password):
    user = User(email=email, password=password)  # NUNCA!
```

### 5.2 Validação de Input

```python
# ✅ BOM - Validar e sanitizar
from pydantic import validator, EmailStr

class UserCreate(BaseModel):
    email: EmailStr  # Valida formato
    name: str

    @validator('name')
    def name_alphanumeric(cls, v):
        if not v.replace(" ", "").isalnum():
            raise ValueError('Apenas letras e números')
        return v.strip()  # Remove espaços

# ❌ RUIM - Aceitar qualquer input
@router.post("/users")
def create_user(data: dict):
    name = data["name"]  # Pode conter SQL injection!
    # INSERT INTO users VALUES ('{name}')  → SQL Injection!
```

### 5.3 Use HTTPS/TLS

```python
# ✅ BOM - Forçar HTTPS
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)
# HTTP → HTTPS redirect automático

# Em produção, configure no nginx/load balancer
```

### 5.4 CORS Restrito

```python
# ✅ BOM - CORS específico
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],  # Domínios específicos
    allow_methods=["GET", "POST"],        # Métodos específicos
    allow_headers=["Authorization"],
)

# ❌ RUIM - CORS aberto
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Qualquer origem!
    allow_methods=["*"],  # Qualquer método!
)
```

### 5.5 Secrets em Variáveis de Ambiente

```python
# ✅ BOM - Secrets em .env
# .env
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=abc123...

# settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()


# ❌ RUIM - Hardcoded
DATABASE_URL = "postgresql://admin:senha123@prod-db/db"  # NUNCA!
SECRET_KEY = "my-secret-key"  # NUNCA no código!
```

---

## 6. Testes

### 6.1 Pirâmide de Testes

```
        ┌─────────┐
        │   E2E   │  ← Poucos (lentos, frágeis)
        ├─────────┤
        │ Integra │  ← Alguns (médios)
       ├──────────┤
       │  Unit    │  ← Muitos (rápidos, confiáveis)
      └───────────┘

70% Unit Tests
20% Integration Tests
10% E2E Tests
```

### 6.2 Testes Unitários

```python
# ✅ BOM - Testar lógica isolada
def test_user_service_create():
    # Arrange
    mock_repo = Mock()
    mock_repo.exists_by_email.return_value = False
    service = UserService(mock_repo)

    # Act
    user = service.create(UserCreate(email="test@test.com"))

    # Assert
    assert user.email == "test@test.com"
    mock_repo.create.assert_called_once()


# ❌ RUIM - Testar com banco real em unit test
def test_user_service_create():
    db = SessionLocal()  # Banco real!
    service = UserService(db)
    # Lento e depende de estado do banco
```

### 6.3 Fixtures

```python
# ✅ BOM - Reutilizar setup
import pytest

@pytest.fixture
def db_session():
    """Database de teste."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def sample_user(db_session):
    """Usuário de teste."""
    user = User(email="test@test.com")
    db_session.add(user)
    db_session.commit()
    return user

def test_get_user(db_session, sample_user):
    # Fixtures injetadas!
    user = db_session.query(User).first()
    assert user.email == "test@test.com"
```

### 6.4 Coverage

```bash
# ✅ BOM - Medir cobertura
pytest --cov=app --cov-report=html
# Alvo: >80% coverage

# Ver relatório
open htmlcov/index.html
```

---

## 7. Código Limpo

### 7.1 Nomenclatura Clara

```python
# ✅ BOM - Nomes descritivos
def calculate_user_monthly_revenue(user_id: int, month: int) -> Decimal:
    orders = get_completed_orders(user_id, month)
    return sum(order.total for order in orders)

# ❌ RUIM - Nomes genéricos
def calc(uid, m):  # Calc o quê?
    o = get_o(uid, m)  # o?
    return sum(x.t for x in o)
```

### 7.2 Funções Pequenas

```python
# ✅ BOM - Funções focadas (< 20 linhas)
def create_user(data: UserCreate):
    validate_user_data(data)
    user = build_user_entity(data)
    save_user(user)
    send_welcome_email(user)
    return user

# ❌ RUIM - Função gigante (100+ linhas)
def create_user(data):
    # Validação (20 linhas)
    # Verificar duplicatas (10 linhas)
    # Hash senha (5 linhas)
    # Criar usuário (10 linhas)
    # Enviar email (20 linhas)
    # Logging (10 linhas)
    # Atualizar estatísticas (15 linhas)
    # ...
```

### 7.3 DRY (Don't Repeat Yourself)

```python
# ✅ BOM - Reutilizar código
def send_email(to: str, template: str, context: dict):
    # Lógica de envio
    pass

def send_welcome_email(user):
    send_email(user.email, "welcome", {"name": user.name})

def send_reset_password_email(user, token):
    send_email(user.email, "reset", {"token": token})


# ❌ RUIM - Copiar e colar
def send_welcome_email(user):
    # SMTP config
    server = smtplib.SMTP(...)
    # Criar mensagem
    msg = MIMEText(...)
    # Enviar
    server.send_message(msg)

def send_reset_password_email(user):
    # SMTP config (DUPLICADO!)
    server = smtplib.SMTP(...)
    # ...
```

### 7.4 Type Hints

```python
# ✅ BOM - Type hints
def get_user(user_id: int) -> Optional[User]:
    return db.query(User).get(user_id)

def calculate_total(items: List[OrderItem]) -> Decimal:
    return sum(item.price * item.quantity for item in items)

# ❌ RUIM - Sem types
def get_user(user_id):  # Retorna o quê?
    return db.query(User).get(user_id)
```

---

## 8. DevOps e Deploy

### 8.1 Docker

```dockerfile
# ✅ BOM - Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]

# Imagem final: ~150MB (vs 800MB sem multi-stage)
```

### 8.2 CI/CD

```yaml
# ✅ BOM - Pipeline automatizado
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest
      - name: Run linters
        run: |
          black --check .
          flake8 .

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          docker build -t myapp .
          docker push myapp
          kubectl set image deployment/app app=myapp:${{ github.sha }}
```

### 8.3 Health Checks

```python
# ✅ BOM - Health checks
@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Verificar DB
        db.execute(text("SELECT 1"))

        # Verificar Redis
        redis_client.ping()

        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503
```

---

## 9. Monitoramento

### 9.1 Logging Estruturado

```python
# ✅ BOM - Structured logging
import structlog

logger = structlog.get_logger()

def create_user(data: UserCreate):
    logger.info(
        "user_creation_started",
        email=data.email,
        username=data.username
    )

    try:
        user = repository.create(data)
        logger.info(
            "user_created",
            user_id=user.id,
            email=user.email
        )
        return user
    except Exception as e:
        logger.error(
            "user_creation_failed",
            email=data.email,
            error=str(e)
        )
        raise

# Output JSON (fácil de parsear):
# {"event": "user_created", "user_id": 123, "email": "...", "timestamp": "..."}


# ❌ RUIM - Print statements
def create_user(data):
    print(f"Creating user {data['email']}")  # Não estruturado
    # Impossível de parsear automaticamente
```

### 9.2 Métricas

```python
# ✅ BOM - Prometheus metrics
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total requests', ['method', 'endpoint'])
request_latency = Histogram('http_request_duration_seconds', 'Request latency')

@router.get("/users")
@request_latency.time()
def get_users():
    request_count.labels(method='GET', endpoint='/users').inc()
    # ...
```

### 9.3 Error Tracking

```python
# ✅ BOM - Sentry para errors
import sentry_sdk

sentry_sdk.init(dsn="your-sentry-dsn")

@router.get("/users/{user_id}")
def get_user(user_id: int):
    try:
        user = repository.get(user_id)
        return user
    except Exception as e:
        sentry_sdk.capture_exception(e)  # Envia para Sentry
        raise
```

---

## 10. Escalabilidade

### 10.1 Stateless Applications

```python
# ✅ BOM - Stateless (pode escalar horizontalmente)
@router.get("/users/{user_id}")
def get_user(user_id: int):
    user = db.query(User).get(user_id)  # Busca do DB
    return user

# Pode rodar múltiplas instâncias sem problemas


# ❌ RUIM - Stateful (não escala)
user_cache = {}  # Estado em memória!

@router.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id in user_cache:
        return user_cache[user_id]

    user = db.query(User).get(user_id)
    user_cache[user_id] = user
    return user

# Se rodar 2 instâncias, cada uma tem cache diferente!
# Solução: Use Redis (cache distribuído)
```

### 10.2 Load Balancing

```nginx
# ✅ BOM - Load balancer
upstream backend {
    least_conn;  # Distribuir para server com menos conexões
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
```

### 10.3 Horizontal Scaling

```yaml
# ✅ BOM - Auto-scaling com K8s
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

# Escala automaticamente baseado em CPU
```

---

## 🎓 Checklist de Produção

Antes de fazer deploy, verifique:

### Código
- [ ] Testes com >80% coverage
- [ ] Linters passando (black, flake8, mypy)
- [ ] Sem hardcoded secrets
- [ ] Type hints em funções públicas
- [ ] Documentação atualizada

### Banco de Dados
- [ ] Indexes em FKs e colunas de busca
- [ ] Migrations versionadas (Alembic)
- [ ] Connection pooling configurado
- [ ] Backups automáticos
- [ ] Evitando N+1 queries

### API
- [ ] Validação com Pydantic
- [ ] Status codes corretos
- [ ] Rate limiting implementado
- [ ] CORS configurado
- [ ] Versionamento (v1, v2)
- [ ] Documentação (Swagger)

### Segurança
- [ ] HTTPS/TLS obrigatório
- [ ] Passwords com hash (bcrypt/argon2)
- [ ] Secrets em env vars
- [ ] Input validation
- [ ] SQL injection protection (ORM)
- [ ] XSS protection

### Performance
- [ ] Caching implementado
- [ ] Queries otimizadas (EXPLAIN)
- [ ] Async para I/O-bound
- [ ] Response compression (gzip)
- [ ] CDN para assets

### Observabilidade
- [ ] Logging estruturado
- [ ] Métricas (Prometheus)
- [ ] Error tracking (Sentry)
- [ ] Health checks
- [ ] Distributed tracing (opcional)

### DevOps
- [ ] Docker configurado
- [ ] CI/CD pipeline
- [ ] Staging environment
- [ ] Blue-green ou canary deploy
- [ ] Rollback plan

---

## 📚 Referências

- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [SQLAlchemy Best Practices](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [The Twelve-Factor App](https://12factor.net/)
- [REST API Best Practices](https://restfulapi.net/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Lembre-se:** Boas práticas não são regras absolutas. Use bom senso e adapte ao seu contexto! 🚀
