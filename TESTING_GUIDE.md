# 🧪 Guia Completo de Testes

> Como testar aplicações backend de forma eficiente e profissional.

---

## 📋 Índice

- [Pirâmide de Testes](#pirâmide-de-testes)
- [Configuração](#configuração)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [End-to-End Tests](#e2e-tests)
- [Fixtures e Mocking](#fixtures-e-mocking)
- [Coverage](#coverage)
- [Continuous Testing](#continuous-testing)

---

## 🔺 Pirâmide de Testes

```
        ┌─────────┐
        │   E2E   │  10%  - Poucos, lentos, custosos
        ├─────────┤
        │ Integr. │  20%  - Médios, testa integrações
        ├─────────┤
        │  Unit   │  70%  - Muitos, rápidos, isolados
        └─────────┘
```

### Regra 70/20/10

- **70% Unit Tests**: Rápidos, isolados, testam lógica
- **20% Integration Tests**: Testam componentes juntos (DB, cache, etc)
- **10% E2E Tests**: Testam fluxo completo da aplicação

**Por quê?**
- Unit tests: rápidos de executar (segundos)
- E2E tests: lentos (minutos)
- Feedback rápido > feedback lento

---

## ⚙️ Configuração

### Instalar Dependências

```bash
pip install pytest pytest-asyncio pytest-cov httpx faker freezegun
```

### Estrutura de Diretórios

```
backend/
├── app/
│   ├── models/
│   ├── services/
│   └── routes/
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Fixtures compartilhadas
│   ├── unit/
│   │   ├── test_services.py
│   │   └── test_utils.py
│   ├── integration/
│   │   ├── test_database.py
│   │   └── test_api.py
│   └── e2e/
│       └── test_user_flow.py
└── pytest.ini
```

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Asyncio
asyncio_mode = auto

# Markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (DB, external services)
    e2e: End-to-end tests (complete flows)
    slow: Slow tests (>1s)

# Coverage
addopts =
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --strict-markers
    -v
```

---

## 🔬 Unit Tests

**O que testar:**
- Lógica de negócio
- Funções puras
- Validações
- Cálculos

**Características:**
- ✅ Rápidos (<1ms cada)
- ✅ Isolados (sem DB, sem rede)
- ✅ Determinísticos (sempre mesmo resultado)

### Exemplo: Testar Lógica de Negócio

```python
# app/services/post_service.py
def calculate_engagement_score(post) -> float:
    """
    Calcula score de engajamento

    Score = (likes * 1 + comments * 3) * time_decay
    """
    age_hours = (datetime.utcnow() - post.created_at).total_seconds() / 3600
    time_decay = 1 / (1 + age_hours / 24)

    score = (post.likes_count * 1 + post.comments_count * 3) * time_decay
    return score


# tests/unit/test_post_service.py
import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time
from app.services.post_service import calculate_engagement_score


class FakePost:
    """Fake object para testes (não precisa do DB)"""
    def __init__(self, likes_count, comments_count, created_at):
        self.likes_count = likes_count
        self.comments_count = comments_count
        self.created_at = created_at


def test_engagement_score_new_post():
    """Post novo (0h) deve ter time_decay = 1.0"""
    with freeze_time("2024-01-01 12:00:00"):
        post = FakePost(
            likes_count=10,
            comments_count=5,
            created_at=datetime(2024, 1, 1, 12, 0, 0)  # Agora
        )

        score = calculate_engagement_score(post)

        # Score = (10 * 1 + 5 * 3) * 1.0 = 25
        assert score == 25.0


def test_engagement_score_old_post():
    """Post antigo (24h) deve ter time_decay = 0.5"""
    with freeze_time("2024-01-02 12:00:00"):
        post = FakePost(
            likes_count=10,
            comments_count=5,
            created_at=datetime(2024, 1, 1, 12, 0, 0)  # 24h atrás
        )

        score = calculate_engagement_score(post)

        # Score = (10 * 1 + 5 * 3) * 0.5 = 12.5
        assert score == 12.5


def test_engagement_score_comments_weight_more():
    """Comentários devem ter peso 3x maior que likes"""
    with freeze_time("2024-01-01 12:00:00"):
        post1 = FakePost(10, 0, datetime(2024, 1, 1, 12, 0, 0))
        post2 = FakePost(0, 3, datetime(2024, 1, 1, 12, 0, 0))

        # 10 likes = 10 pontos
        # 3 comments = 9 pontos
        assert calculate_engagement_score(post1) > calculate_engagement_score(post2)


@pytest.mark.parametrize("likes,comments,expected", [
    (0, 0, 0),
    (10, 0, 10),
    (0, 5, 15),
    (10, 5, 25),
])
def test_engagement_score_parametrized(likes, comments, expected):
    """Testa múltiplos cenários com parametrize"""
    with freeze_time("2024-01-01 12:00:00"):
        post = FakePost(likes, comments, datetime(2024, 1, 1, 12, 0, 0))
        assert calculate_engagement_score(post) == expected
```

---

## 🔗 Integration Tests

**O que testar:**
- Integração com banco de dados
- APIs externas
- Cache (Redis)
- Filas (Celery)

**Características:**
- ⚠️ Mais lentos (~100ms cada)
- ⚠️ Requerem setup (test DB, test Redis)
- ✅ Testam componentes reais

### Configuração: Test Database

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.main import app

# Test database URL
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/test_db"


@pytest.fixture(scope="session")
def engine():
    """Criar engine de teste"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)  # Criar tabelas
    yield engine
    Base.metadata.drop_all(engine)  # Limpar após testes


@pytest.fixture(scope="function")
def db_session(engine):
    """
    Criar sessão de teste com rollback

    Cada teste roda em uma transação que é revertida ao final
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Cliente de teste FastAPI"""
    from fastapi.testclient import TestClient

    # Override dependency
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
```

### Exemplo: Testar CRUD com Banco

```python
# tests/integration/test_user_repository.py
import pytest
from app.models.user import User
from app.repositories.user_repository import UserRepository


def test_create_user(db_session):
    """Testa criar usuário no banco"""
    repo = UserRepository(db_session)

    user = repo.create(
        username="joao",
        email="joao@example.com",
        password_hash="hashed123"
    )

    assert user.id is not None
    assert user.username == "joao"

    # Verificar que foi salvo
    db_session.commit()
    found = db_session.query(User).filter(User.id == user.id).first()
    assert found is not None


def test_get_user_by_email(db_session):
    """Testa buscar usuário por email"""
    repo = UserRepository(db_session)

    # Criar usuário
    user = repo.create(
        username="maria",
        email="maria@example.com",
        password_hash="hashed456"
    )
    db_session.commit()

    # Buscar
    found = repo.get_by_email("maria@example.com")

    assert found is not None
    assert found.id == user.id
    assert found.username == "maria"


def test_duplicate_username_fails(db_session):
    """Testa que username duplicado falha"""
    repo = UserRepository(db_session)

    # Criar primeiro usuário
    repo.create(username="pedro", email="pedro1@example.com", password_hash="hash")
    db_session.commit()

    # Tentar criar segundo com mesmo username
    with pytest.raises(Exception):  # IntegrityError
        repo.create(username="pedro", email="pedro2@example.com", password_hash="hash")
        db_session.commit()
```

### Exemplo: Testar API Endpoints

```python
# tests/integration/test_auth_api.py
import pytest


def test_register_user(client):
    """Testa registro de usuário"""
    response = client.post("/auth/register", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "SecurePass123!"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert "password" not in data  # Não retornar senha


def test_register_duplicate_username(client):
    """Testa que username duplicado retorna 400"""
    # Criar usuário
    client.post("/auth/register", json={
        "username": "duplicate",
        "email": "user1@example.com",
        "password": "Pass123!"
    })

    # Tentar criar outro com mesmo username
    response = client.post("/auth/register", json={
        "username": "duplicate",
        "email": "user2@example.com",
        "password": "Pass123!"
    })

    assert response.status_code == 400
    assert "username" in response.json()["detail"].lower()


def test_login_success(client):
    """Testa login com sucesso"""
    # Registrar
    client.post("/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "MyPass123!"
    })

    # Login
    response = client.post("/auth/login", json={
        "username": "loginuser",
        "password": "MyPass123!"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client):
    """Testa login com senha errada"""
    # Registrar
    client.post("/auth/register", json={
        "username": "wrongpass",
        "email": "wrong@example.com",
        "password": "CorrectPass123!"
    })

    # Login com senha errada
    response = client.post("/auth/login", json={
        "username": "wrongpass",
        "password": "WrongPass123!"
    })

    assert response.status_code == 401
```

---

## 🎭 End-to-End Tests

**O que testar:**
- Fluxos completos de usuário
- Happy path + edge cases
- Jornada do usuário

**Características:**
- ❌ Lentos (segundos por teste)
- ❌ Frágeis (quebram fácil)
- ✅ Alto valor (testam tudo junto)

### Exemplo: Fluxo Completo

```python
# tests/e2e/test_user_journey.py
import pytest


def test_complete_user_journey(client):
    """
    Testa jornada completa de usuário:
    1. Registrar
    2. Login
    3. Criar post
    4. Curtir post
    5. Comentar post
    6. Ver feed
    """

    # 1. Registrar
    response = client.post("/auth/register", json={
        "username": "journey_user",
        "email": "journey@example.com",
        "password": "Pass123!"
    })
    assert response.status_code == 201

    # 2. Login
    response = client.post("/auth/login", json={
        "username": "journey_user",
        "password": "Pass123!"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Criar post
    response = client.post("/posts",
        json={"content": "Meu primeiro post!"},
        headers=headers
    )
    assert response.status_code == 201
    post_id = response.json()["id"]

    # 4. Curtir post
    response = client.post(f"/posts/{post_id}/like", headers=headers)
    assert response.status_code == 200
    assert response.json()["liked"] == True

    # 5. Comentar post
    response = client.post(f"/posts/{post_id}/comments",
        json={"content": "Ótimo post!"},
        headers=headers
    )
    assert response.status_code == 200

    # 6. Ver feed
    response = client.get("/feed", headers=headers)
    assert response.status_code == 200
    posts = response.json()["posts"]
    assert len(posts) > 0
    assert posts[0]["id"] == post_id


@pytest.mark.slow
def test_social_network_flow(client):
    """
    Testa interação entre usuários:
    1. User A e User B registram
    2. User A segue User B
    3. User B cria post
    4. User A vê post no feed
    5. User A curte e comenta
    6. User B recebe notificações
    """

    # 1. Criar User A
    client.post("/auth/register", json={
        "username": "user_a",
        "email": "a@example.com",
        "password": "Pass123!"
    })
    token_a = client.post("/auth/login", json={
        "username": "user_a", "password": "Pass123!"
    }).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Criar User B
    client.post("/auth/register", json={
        "username": "user_b",
        "email": "b@example.com",
        "password": "Pass123!"
    })
    token_b = client.post("/auth/login", json={
        "username": "user_b", "password": "Pass123!"
    }).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Get user B ID
    user_b = client.get("/users/me", headers=headers_b).json()
    user_b_id = user_b["id"]

    # 3. User A segue User B
    response = client.post(f"/users/{user_b_id}/follow", headers=headers_a)
    assert response.status_code == 200

    # 4. User B cria post
    post_response = client.post("/posts",
        json={"content": "Post de B"},
        headers=headers_b
    )
    post_id = post_response.json()["id"]

    # 5. User A vê post no feed
    feed = client.get("/feed", headers=headers_a).json()
    post_ids = [p["id"] for p in feed["posts"]]
    assert post_id in post_ids

    # 6. User A curte
    client.post(f"/posts/{post_id}/like", headers=headers_a)

    # 7. User B tem notificação
    notifications = client.get("/notifications", headers=headers_b).json()
    assert len(notifications["notifications"]) > 0
    assert notifications["notifications"][0]["type"] == "like"
```

---

## 🎪 Fixtures e Mocking

### Fixtures Reutilizáveis

```python
# tests/conftest.py
import pytest
from faker import Faker

fake = Faker()


@pytest.fixture
def sample_user(db_session):
    """Criar usuário de exemplo"""
    from app.models.user import User
    from app.services.auth_service import hash_password

    user = User(
        username=fake.user_name(),
        email=fake.email(),
        password_hash=hash_password("Pass123!")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def sample_post(db_session, sample_user):
    """Criar post de exemplo"""
    from app.models.post import Post

    post = Post(
        content="Sample post content",
        user_id=sample_user.id
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    return post


@pytest.fixture
def auth_headers(client, sample_user):
    """Headers de autenticação"""
    response = client.post("/auth/login", json={
        "username": sample_user.username,
        "password": "Pass123!"
    })
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# Uso
def test_with_fixtures(client, sample_post, auth_headers):
    """Usar fixtures em testes"""
    response = client.get(f"/posts/{sample_post.id}", headers=auth_headers)
    assert response.status_code == 200
```

### Mocking

```python
# tests/unit/test_external_api.py
import pytest
from unittest.mock import Mock, patch
from app.services.external_api_service import fetch_user_info


def test_fetch_user_info_success():
    """Testar chamada externa com mock"""

    # Mock da resposta HTTP
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 123,
        "name": "John Doe"
    }

    with patch('requests.get', return_value=mock_response):
        result = fetch_user_info(user_id=123)

        assert result["name"] == "John Doe"


def test_fetch_user_info_timeout():
    """Testar timeout em API externa"""

    with patch('requests.get', side_effect=TimeoutError()):
        with pytest.raises(TimeoutError):
            fetch_user_info(user_id=123)


@pytest.mark.asyncio
async def test_async_with_mock():
    """Testar função async com mock"""
    from unittest.mock import AsyncMock

    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar.return_value = {"id": 1, "name": "Test"}

    result = await some_async_function(mock_db)

    assert result["name"] == "Test"
    mock_db.execute.assert_called_once()
```

---

## 📊 Coverage

### Executar Coverage

```bash
# Rodar testes com coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Ver relatório HTML
open htmlcov/index.html
```

### Interpretar Coverage

```
Name                      Stmts   Miss  Cover   Missing
-------------------------------------------------------
app/__init__.py              10      0   100%
app/models/user.py           45      2    96%   23, 45
app/services/auth.py         80     10    88%   45-55, 78
app/routes/users.py          60     15    75%   12-20, 34-40
-------------------------------------------------------
TOTAL                       195     27    86%
```

**Meta de Coverage:**
- 80%+ total
- 90%+ em services (lógica crítica)
- 70%+ em routes (muitas validações)

**O que NÃO precisa 100%:**
- Exception handlers raros
- Código defensivo (edge cases)
- Código de configuração

---

## 🔄 Continuous Testing

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running tests before commit..."

# Rodar unit tests (rápidos)
pytest tests/unit -v

if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed. Commit aborted."
    exit 1
fi

echo "✅ Tests passed!"
exit 0
```

### CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run unit tests
        run: pytest tests/unit -v --cov=app

      - name: Run integration tests
        run: pytest tests/integration -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379

      - name: Run E2E tests
        run: pytest tests/e2e -v --maxfail=1

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 🎯 Best Practices

### ✅ DO

1. **Arrange-Act-Assert pattern**
```python
def test_example():
    # Arrange: setup
    user = create_user(username="test")

    # Act: execute
    result = user.update_email("new@example.com")

    # Assert: verify
    assert result.email == "new@example.com"
```

2. **Nomes descritivos**
```python
# ❌ Ruim
def test_1():
    ...

# ✅ Bom
def test_user_cannot_like_own_post():
    ...
```

3. **Um assert por conceito**
```python
# ❌ Ruim (muitos asserts diferentes)
def test_user():
    assert user.name == "João"
    assert user.email == "joao@example.com"
    assert user.is_active == True
    assert user.posts_count == 0

# ✅ Bom (agrupa asserts relacionados)
def test_user_creation():
    assert user.name == "João"
    assert user.email == "joao@example.com"

def test_user_initial_state():
    assert user.is_active == True
    assert user.posts_count == 0
```

4. **Fixtures para setup repetido**
5. **Parametrize para múltiplos casos**
6. **Mock APIs externas**

### ❌ DON'T

1. **Testes dependentes**
```python
# ❌ test_b depende de test_a
def test_a_create():
    global user
    user = create_user()

def test_b_update():
    user.update()  # Depende de test_a!
```

2. **Sleep em testes**
```python
# ❌ Lento e frágil
time.sleep(5)

# ✅ Use mocks ou freezegun
```

3. **Testar implementação ao invés de comportamento**
```python
# ❌ Testa detalhe de implementação
assert mock_db.query.called_once()

# ✅ Testa resultado
assert result == expected
```

---

## 📚 Resumo

```
┌──────────────────┬─────────┬──────────┬────────────┬──────────────┐
│ Tipo             │ Qtd     │ Tempo    │ Escopo     │ Quando Rodar │
├──────────────────┼─────────┼──────────┼────────────┼──────────────┤
│ Unit             │ 70%     │ <1s      │ Função     │ Sempre       │
│ Integration      │ 20%     │ ~10s     │ Módulo     │ Pre-commit   │
│ E2E              │ 10%     │ ~1min    │ Sistema    │ Pre-push/CI  │
└──────────────────┴─────────┴──────────┴────────────┴──────────────┘

✅ Priorize unit tests (rápido feedback)
✅ Use fixtures para setup
✅ Mock APIs externas
✅ Mantenha 80%+ coverage
✅ Rode em CI/CD
✅ Fix testes quebrados imediatamente
```

---

**Testes são documentação viva do seu código! 📖✨**
