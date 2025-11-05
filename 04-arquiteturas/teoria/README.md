# Módulo 04 - Arquiteturas de Software

## 🎯 Objetivo

Entender diferentes padrões arquiteturais e escolher a arquitetura certa para cada projeto.

---

## 📚 Conteúdo

1. [Monolith vs Microservices](#1-monolith-vs-microservices)
2. [Layered Architecture](#2-layered-architecture)
3. [Clean Architecture / Hexagonal](#3-clean-architecture--hexagonal)
4. [Event-Driven Architecture](#4-event-driven-architecture)
5. [CQRS e Event Sourcing](#5-cqrs-e-event-sourcing)
6. [Domain-Driven Design (DDD)](#6-domain-driven-design-ddd)

---

## 1. Monolith vs Microservices

### 1.1 Monolith

```
┌────────────────────────────────────────┐
│         Aplicação Monolítica           │
│  ┌──────────────────────────────────┐  │
│  │ UI (Frontend/Templates)          │  │
│  ├──────────────────────────────────┤  │
│  │ Business Logic                   │  │
│  │ - Users                          │  │
│  │ - Posts                          │  │
│  │ - Comments                       │  │
│  │ - Notifications                  │  │
│  ├──────────────────────────────────┤  │
│  │ Data Access Layer                │  │
│  └──────────────┬───────────────────┘  │
└─────────────────┼──────────────────────┘
                  │
            ┌─────▼──────┐
            │  Database  │
            └────────────┘
```

**Vantagens:**
- ✅ Simples de desenvolver e testar
- ✅ Deploy simples (um único artefato)
- ✅ Performance (sem chamadas de rede)
- ✅ Transactions ACID fáceis

**Desvantagens:**
- ❌ Escala tudo ou nada
- ❌ Difícil de manter quando cresce
- ❌ Deploy arriscado (tudo de uma vez)
- ❌ Tecnologia única

### 1.2 Microservices

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Service    │   │   Service    │   │   Service    │
│    Users     │   │    Posts     │   │  Comments    │
│              │   │              │   │              │
│ ┌──────────┐ │   │ ┌──────────┐ │   │ ┌──────────┐ │
│ │   DB     │ │   │ │   DB     │ │   │ │   DB     │ │
│ └──────────┘ │   │ └──────────┘ │   │ └──────────┘ │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼───────┐
                    │  API Gateway │
                    └──────────────┘
```

**Vantagens:**
- ✅ Escala independente
- ✅ Deploy independente
- ✅ Tecnologias diferentes
- ✅ Times independentes
- ✅ Falhas isoladas

**Desvantagens:**
- ❌ Complexidade operacional
- ❌ Latência de rede
- ❌ Transactions distribuídas
- ❌ Debugging difícil
- ❌ Overhead de infraestrutura

### 1.3 Modular Monolith (Melhor dos dois mundos)

```
┌────────────────────────────────────────┐
│      Aplicação Monolítica              │
│  ┌──────────┐  ┌──────────┐           │
│  │  Module  │  │  Module  │           │
│  │  Users   │  │  Posts   │           │
│  │          │  │          │           │
│  │ ┌──────┐ │  │ ┌──────┐ │           │
│  │ │Logic │ │  │ │Logic │ │           │
│  │ └──────┘ │  │ └──────┘ │           │
│  └──────────┘  └──────────┘           │
│          │            │                │
│          └────────────┼────────────────┤
│                  ┌────▼──────┐         │
│                  │  Database │         │
│                  └───────────┘         │
└────────────────────────────────────────┘
```

**Ideal para:**
- ✅ Startups (simplicidade)
- ✅ Times pequenos
- ✅ Preparação para microservices futuros

---

## 2. Layered Architecture

### 2.1 Estrutura Clássica

```
┌────────────────────────────────────────┐
│  Presentation Layer (FastAPI)          │
│  - Routes                              │
│  - Request/Response handling           │
└────────────┬───────────────────────────┘
             │
┌────────────▼───────────────────────────┐
│  Business Logic Layer                  │
│  - Use cases                           │
│  - Domain logic                        │
│  - Validations                         │
└────────────┬───────────────────────────┘
             │
┌────────────▼───────────────────────────┐
│  Data Access Layer                     │
│  - Repositories                        │
│  - ORM (SQLAlchemy)                    │
└────────────┬───────────────────────────┘
             │
        ┌────▼─────┐
        │ Database │
        └──────────┘
```

**Exemplo FastAPI:**
```python
# Presentation Layer
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, user)

# Business Logic Layer
def create_user(db: Session, user_data: UserCreate) -> User:
    # Validações de negócio
    if user_repository.get_by_email(db, user_data.email):
        raise ValueError("Email já existe")

    # Hash password
    hashed = hash_password(user_data.password)

    # Criar usuário
    return user_repository.create(db, user_data, hashed)

# Data Access Layer
def create(db: Session, user_data: UserCreate, hashed_pwd: str) -> User:
    user = User(
        email=user_data.email,
        name=user_data.name,
        password=hashed_pwd
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

---

## 3. Clean Architecture / Hexagonal

### 3.1 Princípios

```
┌─────────────────────────────────────────────┐
│          External (Frameworks)              │
│  ┌───────────────────────────────────────┐  │
│  │      Interface Adapters              │  │
│  │  ┌─────────────────────────────────┐ │  │
│  │  │   Application Business Rules    │ │  │
│  │  │  ┌───────────────────────────┐  │ │  │
│  │  │  │  Enterprise Business      │  │ │  │
│  │  │  │  Rules (Entities)         │  │ │  │
│  │  │  │                           │  │ │  │
│  │  │  │  - Domain Models          │  │ │  │
│  │  │  │  - Business Logic         │  │ │  │
│  │  │  └───────────────────────────┘  │ │  │
│  │  │  - Use Cases                    │ │  │
│  │  └─────────────────────────────────┘ │  │
│  │  - Controllers, Presenters           │  │
│  └───────────────────────────────────────┘  │
│  - DB, Web, UI, External Services           │
└─────────────────────────────────────────────┘
```

**Regra de dependência:** Fluxo sempre de fora para dentro.
- Camadas externas dependem das internas
- Camadas internas NÃO conhecem as externas

**Exemplo:**
```python
# Entities (Core) - Não depende de NADA
class User:
    def __init__(self, email: str, name: str):
        self.email = email
        self.name = name

    def can_post(self) -> bool:
        return self.is_active and not self.is_banned

# Use Cases (Application) - Depende apenas de Entities
class CreateUserUseCase:
    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository

    def execute(self, email: str, name: str) -> User:
        # Lógica de negócio
        if self.user_repository.exists(email):
            raise ValueError("Email exists")

        user = User(email, name)
        return self.user_repository.save(user)

# Adapters (Interface) - Implementa interfaces do core
class SQLAlchemyUserRepository(UserRepositoryInterface):
    def save(self, user: User) -> User:
        db_user = UserModel(email=user.email, name=user.name)
        self.session.add(db_user)
        self.session.commit()
        return user

# Controllers (External) - Usa use cases
@app.post("/users")
def create_user_endpoint(data: UserCreate):
    use_case = CreateUserUseCase(SQLAlchemyUserRepository())
    return use_case.execute(data.email, data.name)
```

**Benefícios:**
- ✅ Testável (mock interfaces)
- ✅ Independente de frameworks
- ✅ Independente de database
- ✅ Lógica de negócio isolada

---

## 4. Event-Driven Architecture

### 4.1 Comunicação por Eventos

```
┌──────────────┐      Event      ┌──────────────┐
│   Service    │  ─────────────>  │ Event Bus    │
│   Users      │   UserCreated    │ (Kafka/Rabbit)│
└──────────────┘                  └──────┬───────┘
                                         │
                    ┌────────────────────┼────────────────┐
                    │                    │                │
              ┌─────▼─────┐       ┌─────▼─────┐   ┌─────▼─────┐
              │  Service  │       │  Service  │   │  Service  │
              │  Email    │       │  Analytics│   │  Notif.   │
              └───────────┘       └───────────┘   └───────────┘
                    │
          Envia welcome email
```

**Exemplo:**
```python
# Publicar evento
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Quando usuário é criado
def create_user(data):
    user = User.create(data)

    # Publicar evento
    producer.send('user-events', {
        'event': 'UserCreated',
        'user_id': user.id,
        'email': user.email,
        'timestamp': datetime.now().isoformat()
    })

    return user

# Consumir evento (outro serviço)
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    event = message.value
    if event['event'] == 'UserCreated':
        send_welcome_email(event['email'])
```

**Vantagens:**
- ✅ Desacoplamento total
- ✅ Escalabilidade
- ✅ Resiliência (retry automático)

**Desvantagens:**
- ❌ Eventual consistency
- ❌ Debugging complexo
- ❌ Ordem de eventos

---

## 5. CQRS e Event Sourcing

### 5.1 CQRS (Command Query Responsibility Segregation)

**Separar leituras de escritas:**

```
┌─────────────────────────────────────────────┐
│              Application                    │
└───────┬──────────────────────┬──────────────┘
        │                      │
        │ Commands             │ Queries
        │ (Write)              │ (Read)
        │                      │
┌───────▼───────┐      ┌───────▼────────┐
│ Write Model   │      │  Read Model    │
│ (PostgreSQL)  │──────>│ (MongoDB/ES)   │
│ Normalized    │ Sync │ Denormalized   │
└───────────────┘      └────────────────┘
```

**Exemplo:**
```python
# Command (Write)
class CreatePostCommand:
    def execute(self, data):
        post = Post.create(data)
        db.session.add(post)
        db.session.commit()

        # Sincronizar com read model
        sync_to_read_model(post)
        return post

# Query (Read)
class GetPostsQuery:
    def execute(self, filters):
        # Lê do model otimizado
        return elasticsearch.search(
            index='posts',
            body={'query': filters}
        )
```

### 5.2 Event Sourcing

**Armazenar eventos em vez de estado atual:**

```
Estado atual: user.balance = 1000

Event Sourcing:
  - AccountCreated (balance: 0)
  - MoneyDeposited (+500)
  - MoneyDeposited (+700)
  - MoneyWithdrawn (-200)
  = Balance: 1000 (calculado)
```

**Vantagens:**
- ✅ Auditoria completa
- ✅ Time travel (estado em qualquer momento)
- ✅ Replay de eventos

---

## 6. Domain-Driven Design (DDD)

### 6.1 Conceitos

**Bounded Contexts:**
```
┌─────────────────────┐  ┌─────────────────────┐
│  Context: Sales     │  │ Context: Shipping   │
│                     │  │                     │
│  User = Customer    │  │  User = Address     │
│  - name             │  │  - shipping address │
│  - email            │  │  - phone            │
│  - purchase history │  │  - delivery notes   │
└─────────────────────┘  └─────────────────────┘
```

**Agregados:**
```python
# Aggregate Root
class Order:
    def __init__(self):
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING

    def add_item(self, item: OrderItem):
        # Lógica de validação
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed order")
        self.items.append(item)

    def calculate_total(self) -> Decimal:
        return sum(item.price * item.quantity for item in self.items)

# Entity (parte do agregado Order)
class OrderItem:
    def __init__(self, product_id: int, quantity: int, price: Decimal):
        self.product_id = product_id
        self.quantity = quantity
        self.price = price
```

---

## 🎓 Resumo - Quando Usar

### Arquitetura por Tamanho/Fase:

```
MVP / Startup           → Modular Monolith + Layered
Crescimento (10-50 devs)→ Clean Architecture + Monolith
Escala (50+ devs)       → Microservices + DDD
Alta complexidade       → CQRS + Event Sourcing
```

### Por Característica:

```
Simplicidade            → Layered Architecture
Testabilidade           → Clean/Hexagonal
Escalabilidade          → Microservices
Auditoria completa      → Event Sourcing
Múltiplos domínios      → DDD
```

---

## 📝 Próximos Passos

1. Exemplos em [`../exemplos/`](../exemplos/)
2. Exercícios em [`../exercicios/`](../exercicios/)
3. Avance para **[Módulo 05 - Performance](../../05-performance-concorrencia/teoria/README.md)**
