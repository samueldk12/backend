# Exercício 01 - Setup e Estrutura Inicial

## 🎯 Objetivo

Configurar o ambiente de desenvolvimento completo para nossa rede social, incluindo FastAPI, Docker, banco de dados e ferramentas de desenvolvimento.

---

## 📋 O que vamos construir?

Uma estrutura inicial profissional que inclui:
- ✅ FastAPI configurado
- ✅ Docker e Docker Compose
- ✅ PostgreSQL como banco principal
- ✅ Redis para cache
- ✅ Migrations (Alembic)
- ✅ Testes (Pytest)
- ✅ Linting e formatação (Black, isort, flake8)
- ✅ Variáveis de ambiente
- ✅ Logging estruturado

---

## 🗂️ Estrutura do Projeto

```
social-network/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point FastAPI
│   ├── config.py            # Configurações
│   ├── database.py          # Conexão com DB
│   ├── models/              # SQLAlchemy models
│   │   └── __init__.py
│   ├── schemas/             # Pydantic schemas
│   │   └── __init__.py
│   ├── api/                 # Endpoints
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependências
│   │   └── v1/              # Versão 1 da API
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           └── health.py
│   ├── core/                # Funcionalidades core
│   │   ├── __init__.py
│   │   └── security.py
│   └── utils/               # Utilitários
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures pytest
│   └── test_health.py
├── alembic/                 # Migrations
│   ├── versions/
│   └── env.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml           # Configurações de ferramentas
├── alembic.ini
└── README.md
```

---

## 🚀 Passo a Passo

### 1. Criar estrutura de diretórios

```bash
mkdir -p social-network/{app/{api/v1/endpoints,core,models,schemas,utils},tests,docker,alembic/versions}
cd social-network
touch app/{__init__.py,main.py,config.py,database.py}
touch app/api/{__init__.py,deps.py}
touch app/api/v1/{__init__.py}
touch app/api/v1/endpoints/{__init__.py,health.py}
touch tests/{__init__.py,conftest.py,test_health.py}
```

### 2. Requirements

**requirements.txt:**
```txt
# FastAPI e servidor
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1

# Redis
redis==5.0.1

# Validação e configuração
pydantic==2.5.3
pydantic-settings==2.1.0
email-validator==2.1.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Utilitários
python-dotenv==1.0.0
```

**requirements-dev.txt:**
```txt
-r requirements.txt

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0

# Linting e formatação
black==23.12.1
isort==5.13.2
flake8==7.0.0
mypy==1.8.0

# Pre-commit
pre-commit==3.6.0
```

### 3. Configuração (app/config.py)

```python
"""
Configurações da aplicação usando Pydantic Settings.
Carrega variáveis de ambiente de forma type-safe.
"""
from functools import lru_cache
from typing import Optional
from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configurações da aplicação.

    Variáveis de ambiente são carregadas automaticamente:
    - Do arquivo .env
    - Das variáveis de ambiente do sistema

    Precedência: env vars > .env > valores padrão
    """

    # API
    APP_NAME: str = "Social Network API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False  # Auto-reload no desenvolvimento

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "social_network"

    @property
    def DATABASE_URL(self) -> str:
        """Constrói URL do PostgreSQL."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        """Constrói URL do Redis."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Security
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"  # Gerar com: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]  # Frontend

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna configurações (cached).

    @lru_cache garante que Settings é instanciado apenas uma vez,
    economizando leitura repetida de .env
    """
    return Settings()


# Instância global para facilitar imports
settings = get_settings()
```

### 4. Database (app/database.py)

```python
"""
Configuração do banco de dados.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexão antes de usar
    pool_size=5,         # Pool de 5 conexões
    max_overflow=10,     # Até 15 conexões no total
    echo=settings.DEBUG, # Log SQL queries em debug
)

# Session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para models
Base = declarative_base()


def get_db():
    """
    Dependência FastAPI para obter sessão do banco.

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 5. Main App (app/main.py)

```python
"""
Entry point da aplicação FastAPI.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.api.v1 import api_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia lifecycle da aplicação.

    Executado ao iniciar e encerrar a aplicação.
    """
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📊 Database: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    logger.info(f"🔴 Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

    yield

    # Shutdown
    logger.info("👋 Shutting down...")


# Criar app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para rede social de vídeos e textos",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc",    # ReDoc
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )
```

### 6. Health Check (app/api/v1/endpoints/health.py)

```python
"""
Endpoints de health check.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis

from app.config import settings
from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check básico.

    Retorna status da API.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/db")
async def health_check_db(db: Session = Depends(get_db)):
    """
    Health check do banco de dados.

    Verifica se consegue conectar e fazer query.
    """
    try:
        # Query simples para testar conexão
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/health/redis")
async def health_check_redis():
    """
    Health check do Redis.

    Verifica se consegue conectar.
    """
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}
```

### 7. API Router (app/api/v1/__init__.py)

```python
"""
Router principal da API v1.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

# Include routers
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Futuros routers serão adicionados aqui:
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
```

### 8. Docker Setup

**docker/docker-compose.yml:**
```yaml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    container_name: social_network_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: social_network
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: social_network_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # FastAPI (opcional, para produção)
  # api:
  #   build:
  #     context: ..
  #     dockerfile: docker/Dockerfile
  #   container_name: social_network_api
  #   ports:
  #     - "8000:8000"
  #   environment:
  #     POSTGRES_HOST: postgres
  #     REDIS_HOST: redis
  #   depends_on:
  #     postgres:
  #       condition: service_healthy
  #     redis:
  #       condition: service_healthy
  #   volumes:
  #     - ../app:/app/app
  #   command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
  redis_data:
```

### 9. Environment Variables

**.env.example:**
```env
# Application
APP_NAME="Social Network API"
DEBUG=True
RELOAD=True

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=social_network

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]
```

### 10. Pyproject.toml

```toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

---

## 🧪 Testando

### 1. Instalar dependências

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. Iniciar serviços

```bash
cd docker
docker-compose up -d
```

### 3. Rodar aplicação

```bash
# Copiar .env
cp .env.example .env

# Rodar FastAPI
python -m app.main
# ou
uvicorn app.main:app --reload
```

### 4. Testar endpoints

```bash
# Health check
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/api/v1/health/db

# Swagger UI
open http://localhost:8000/docs
```

---

## ✅ Checklist

- [ ] Estrutura de diretórios criada
- [ ] Dependencies instaladas
- [ ] Docker containers rodando
- [ ] FastAPI iniciando sem erros
- [ ] Endpoint /health retornando 200
- [ ] Endpoint /health/db conectando ao PostgreSQL
- [ ] Endpoint /health/redis conectando ao Redis
- [ ] Swagger UI acessível em /docs

---

## 🎯 Próximos Passos

- **[Exercício 02](../exercicio-02-usuarios/)**: CRUD de usuários
- Implementar models com SQLAlchemy
- Criar schemas com Pydantic
- Endpoints de criação, leitura, atualização e deleção

---

## 📚 Conceitos Aplicados

✅ **Módulo 01 - Fundamentos:**
- Async/await (FastAPI assíncrono)
- Process management (Uvicorn workers)

✅ **Módulo 02 - Protocolos:**
- HTTP/2 (via Uvicorn)
- REST API design
- JSON serialization

✅ **Módulo 03 - Banco de Dados:**
- PostgreSQL connection
- Connection pooling
- Redis para cache

Esta é a base sólida sobre a qual construiremos toda a aplicação!
