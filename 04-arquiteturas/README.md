# 04 - Arquiteturas de Software

## Índice

1. [Monolith vs Microservices](#monolith-vs-microservices)
2. [Clean Architecture](#clean-architecture)
3. [Domain-Driven Design (DDD)](#domain-driven-design-ddd)
4. [Event-Driven Architecture](#event-driven-architecture)

---

## Monolith vs Microservices

### Monolith

**Prós:**
- ✅ Simples de desenvolver
- ✅ Simples de deployar (1 aplicação)
- ✅ Simples de testar

**Contras:**
- ❌ Acoplamento alto
- ❌ Deploy = tudo junto (arriscado)
- ❌ Difícil escalar partes específicas

```
┌─────────────────────────────────────┐
│         MONOLITH                    │
│                                     │
│  ┌──────┐  ┌──────┐  ┌──────┐     │
│  │Users │  │Posts │  │Orders│     │
│  └──────┘  └──────┘  └──────┘     │
│                                     │
│         Same Database               │
│         Same Process                │
└─────────────────────────────────────┘
```

### Microservices

**Prós:**
- ✅ Independência de deploy
- ✅ Escala independente
- ✅ Tech stack por serviço

**Contras:**
- ❌ Complexidade operacional
- ❌ Comunicação entre serviços
- ❌ Transações distribuídas

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│ User    │    │  Post   │    │ Order   │
│ Service │────│ Service │────│ Service │
│         │    │         │    │         │
│ DB1     │    │  DB2    │    │  DB3    │
└─────────┘    └─────────┘    └─────────┘
```

**Quando usar Microservices:**
- Times grandes (>50 devs)
- Partes do sistema escalam diferente
- Releases independentes críticas

---

## Clean Architecture

### Camadas

```
┌──────────────────────────────────────┐
│     Controllers (FastAPI routes)     │  ← Frameworks
├──────────────────────────────────────┤
│     Use Cases (Business Logic)       │  ← Application
├──────────────────────────────────────┤
│     Entities (Domain Models)         │  ← Domain
├──────────────────────────────────────┤
│  Repositories (DB, External APIs)    │  ← Infrastructure
└──────────────────────────────────────┘
```

### Exemplo

```python
# Domain Layer
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def change_email(self, new_email: str):
        # Business rule
        if '@' not in new_email:
            raise ValueError("Invalid email")
        self.email = new_email


# Application Layer
class CreateUserUseCase:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def execute(self, name: str, email: str) -> User:
        user = User(name, email)
        self.user_repo.save(user)
        return user


# Interface Layer
from fastapi import FastAPI, Depends

app = FastAPI()

@app.post("/users")
def create_user(
    name: str,
    email: str,
    use_case: CreateUserUseCase = Depends()
):
    return use_case.execute(name, email)
```

**Vantagens:**
- ✅ Testável (mock repositories)
- ✅ Independente de framework
- ✅ Business logic isolada

---

## Domain-Driven Design (DDD)

### Conceitos

**Aggregate**: Cluster de objetos tratados como unidade
```python
class Order:  # Aggregate Root
    def __init__(self):
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING

    def add_item(self, product_id: str, quantity: int):
        # Regra de negócio dentro do aggregate
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed order")

        item = OrderItem(product_id, quantity)
        self.items.append(item)
```

**Value Object**: Objeto sem identidade, comparado por valor
```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

# Comparação por valor
money1 = Money(Decimal('10.00'), 'USD')
money2 = Money(Decimal('10.00'), 'USD')
assert money1 == money2  # True
```

**Repository**: Abstração para persistência
```python
class UserRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: int) -> Optional[User]:
        pass

    @abstractmethod
    def save(self, user: User) -> None:
        pass

# Implementação SQL
class SQLUserRepository(UserRepository):
    def find_by_id(self, id: int) -> Optional[User]:
        row = db.execute("SELECT * FROM users WHERE id = ?", id)
        return User.from_row(row) if row else None
```

---

## Event-Driven Architecture

### Event Sourcing

Ao invés de salvar estado atual, salva eventos.

```python
# ❌ State-based (tradicional)
class Account:
    balance: int = 100

account.balance -= 50  # Estado atual = 50

# ✅ Event-sourced
events = [
    AccountCreated(balance=100),
    MoneyWithdrawn(amount=50),
    MoneyDeposited(amount=20),
]

# Reconstruir estado = replay events
balance = 0
for event in events:
    if isinstance(event, AccountCreated):
        balance = event.balance
    elif isinstance(event, MoneyWithdrawn):
        balance -= event.amount
    elif isinstance(event, MoneyDeposited):
        balance += event.amount

# Estado atual = 70
```

**Vantagens:**
- ✅ Histórico completo (audit log)
- ✅ Time travel (estado em qualquer momento)
- ✅ Event replay (reprocessar)

### Pub/Sub Pattern

```python
# Service A: Publica evento
async def create_order(order_data):
    order = Order(**order_data)
    db.save(order)

    # Publica evento
    await event_bus.publish("order.created", {
        "order_id": order.id,
        "user_id": order.user_id,
        "total": order.total
    })


# Service B: Consome evento (inventory)
@event_bus.subscribe("order.created")
async def handle_order_created(event):
    for item in event['items']:
        inventory.reserve(item['product_id'], item['quantity'])


# Service C: Consome evento (email)
@event_bus.subscribe("order.created")
async def handle_order_created(event):
    user = users.get(event['user_id'])
    send_email(user.email, "Order confirmed!")
```

---

## Próximo Módulo

➡️ [05 - Performance e Concorrência](../05-performance-concorrencia/README.md)
