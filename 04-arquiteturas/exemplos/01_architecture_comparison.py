"""
Exemplo 01: Comparação de Arquiteturas

Implementa a MESMA feature (CRUD de usuários) em 4 arquiteturas diferentes:
1. Monolith Simples (Procedural)
2. Layered Architecture (MVC-style)
3. Clean Architecture (Hexagonal)
4. Domain-Driven Design (DDD)

Mostra prós, contras e quando usar cada uma.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime

# ============================================================================
# SETUP COMUM
# ============================================================================

# Simulação de banco de dados
USERS_DB = []


@dataclass
class UserData:
    """Data class para representar usuário."""
    id: Optional[int] = None
    email: str = ""
    name: str = ""
    created_at: Optional[datetime] = None


# ============================================================================
# ARQUITETURA 1: MONOLITH SIMPLES (Procedural)
# ============================================================================

print("=" * 70)
print("ARQUITETURA 1: MONOLITH SIMPLES (PROCEDURAL)")
print("=" * 70)

"""
Estrutura:
  app.py  ← TUDO aqui (routes + logic + data access)

✅ Prós:
  • Muito simples
  • Rápido de desenvolver (MVP)
  • Fácil de entender
  • Bom para projetos pequenos

❌ Contras:
  • Código cresce desordenado
  • Difícil de testar (acoplado ao DB)
  • Difícil de reutilizar
  • Não escala (code-wise)

🎯 Quando usar:
  • MVP / Protótipo
  • Projeto pessoal pequeno
  • Scripts e ferramentas internas
"""

# Tudo em um arquivo!
from fastapi import FastAPI, HTTPException

app_simple = FastAPI()


@app_simple.post("/users")
def create_user_simple(email: str, name: str):
    """
    Criar usuário (forma mais simples possível).

    Problema: Lógica, validação e DB no mesmo lugar!
    """
    # Validação inline
    if not "@" in email:
        raise HTTPException(400, "Email inválido")

    if len(name) < 3:
        raise HTTPException(400, "Nome muito curto")

    # Verificar duplicata
    for user in USERS_DB:
        if user.get("email") == email:
            raise HTTPException(400, "Email já existe")

    # Criar usuário
    user = {
        "id": len(USERS_DB) + 1,
        "email": email,
        "name": name,
        "created_at": datetime.now()
    }

    # Salvar
    USERS_DB.append(user)

    return user


@app_simple.get("/users/{user_id}")
def get_user_simple(user_id: int):
    """Buscar usuário."""
    for user in USERS_DB:
        if user.get("id") == user_id:
            return user

    raise HTTPException(404, "Usuário não encontrado")


@app_simple.get("/users")
def list_users_simple():
    """Listar usuários."""
    return USERS_DB


print("""
Exemplo de uso:
  POST /users
    { "email": "joao@example.com", "name": "João" }

Características:
  • Todo código no endpoint
  • Sem separação de camadas
  • Difícil de testar (precisa fazer HTTP request)
  • Bom para: MVP, protótipos, scripts

Linhas de código: ~50
Arquivos: 1
Complexidade: Muito baixa
Testabilidade: Baixa (acoplado)
""")


# ============================================================================
# ARQUITETURA 2: LAYERED ARCHITECTURE (MVC-style)
# ============================================================================

print("\n" + "=" * 70)
print("ARQUITETURA 2: LAYERED ARCHITECTURE (MVC-STYLE)")
print("=" * 70)

"""
Estrutura:
  controllers/    ← HTTP handling (routes)
  services/       ← Business logic
  repositories/   ← Data access
  models/         ← Data models

Fluxo:
  Controller → Service → Repository → Database

✅ Prós:
  • Organizado em camadas
  • Separação de responsabilidades
  • Fácil de entender
  • Padrão da indústria

❌ Contras:
  • Pode virar "god service"
  • Lógica de negócio pode vazar
  • Ainda acoplado ao framework

🎯 Quando usar:
  • Projetos médios (maioria dos casos)
  • Times com experiência em MVC
  • CRUD com alguma lógica de negócio
"""


# Repository Layer (Data Access)
class UserRepository:
    """Isolamento do acesso a dados."""

    def __init__(self, db: list):
        self.db = db

    def find_by_id(self, user_id: int) -> Optional[dict]:
        """Buscar por ID."""
        return next((u for u in self.db if u["id"] == user_id), None)

    def find_by_email(self, email: str) -> Optional[dict]:
        """Buscar por email."""
        return next((u for u in self.db if u["email"] == email), None)

    def find_all(self) -> List[dict]:
        """Listar todos."""
        return self.db

    def save(self, user: dict) -> dict:
        """Salvar usuário."""
        user["id"] = len(self.db) + 1
        user["created_at"] = datetime.now()
        self.db.append(user)
        return user


# Service Layer (Business Logic)
class UserService:
    """Lógica de negócio centralizada."""

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def create_user(self, email: str, name: str) -> dict:
        """
        Criar usuário com validações de negócio.

        Regras:
        - Email deve ser único
        - Nome deve ter pelo menos 3 caracteres
        - Email deve ser válido
        """
        # Validações de negócio
        if not "@" in email:
            raise ValueError("Email inválido")

        if len(name) < 3:
            raise ValueError("Nome deve ter pelo menos 3 caracteres")

        # Verificar duplicata
        if self.repository.find_by_email(email):
            raise ValueError("Email já está em uso")

        # Criar usuário
        user = {
            "email": email,
            "name": name
        }

        return self.repository.save(user)

    def get_user(self, user_id: int) -> Optional[dict]:
        """Buscar usuário."""
        return self.repository.find_by_id(user_id)

    def list_users(self) -> List[dict]:
        """Listar usuários."""
        return self.repository.find_all()


# Controller Layer (HTTP Handling)
app_layered = FastAPI()

# Dependency injection (manual neste exemplo)
user_repository = UserRepository(USERS_DB)
user_service = UserService(user_repository)


@app_layered.post("/users")
def create_user_layered(email: str, name: str):
    """Controller apenas lida com HTTP."""
    try:
        user = user_service.create_user(email, name)
        return user
    except ValueError as e:
        raise HTTPException(400, str(e))


@app_layered.get("/users/{user_id}")
def get_user_layered(user_id: int):
    """Buscar usuário."""
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return user


@app_layered.get("/users")
def list_users_layered():
    """Listar usuários."""
    return user_service.list_users()


print("""
Camadas:
  1. Controller: HTTP handling (FastAPI endpoints)
  2. Service: Business logic (validações, regras)
  3. Repository: Data access (queries, CRUD)

Benefícios:
  • Código organizado
  • Fácil de testar cada camada
  • Reutilizável (service pode ser usado por CLI, jobs, etc)
  • Padrão conhecido (MVC)

Linhas de código: ~120
Arquivos: 3 (controller, service, repository)
Complexidade: Média
Testabilidade: Alta
""")


# ============================================================================
# ARQUITETURA 3: CLEAN ARCHITECTURE (Hexagonal)
# ============================================================================

print("\n" + "=" * 70)
print("ARQUITETURA 3: CLEAN ARCHITECTURE (HEXAGONAL)")
print("=" * 70)

"""
Estrutura:
  domain/         ← Entities (lógica de negócio pura)
  use_cases/      ← Application logic
  adapters/       ← Interface adapters (DB, HTTP, etc)
  infrastructure/ ← Frameworks (FastAPI, SQLAlchemy)

Princípio: Dependências sempre apontam para dentro

  Infrastructure → Adapters → Use Cases → Domain

✅ Prós:
  • Testável (sem framework)
  • Independente de DB/Framework
  • Lógica de negócio isolada
  • Fácil de trocar implementações

❌ Contras:
  • Mais código (boilerplate)
  • Curva de aprendizado
  • Pode ser overkill para CRUD simples

🎯 Quando usar:
  • Projetos complexos
  • Lógica de negócio rica
  • Precisa trocar DB/framework
  • Time sênior
"""


# Domain Layer (Core - Sem dependências!)
class User:
    """
    Entity: Lógica de negócio pura.

    Não depende de framework, DB, nada!
    """

    def __init__(self, email: str, name: str, id: Optional[int] = None):
        self._id = id
        self._email = email
        self._name = name
        self._created_at = datetime.now()

        # Validações no domínio
        if not "@" in email:
            raise ValueError("Email inválido")

        if len(name) < 3:
            raise ValueError("Nome deve ter pelo menos 3 caracteres")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def email(self) -> str:
        return self._email

    @property
    def name(self) -> str:
        return self._name

    def to_dict(self) -> dict:
        """Converter para dict (persistência)."""
        return {
            "id": self._id,
            "email": self._email,
            "name": self._name,
            "created_at": self._created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Criar de dict (reconstituição)."""
        user = cls.__new__(cls)
        user._id = data["id"]
        user._email = data["email"]
        user._name = data["name"]
        user._created_at = data["created_at"]
        return user


# Port (Interface que repositório deve implementar)
class UserRepositoryPort(Protocol):
    """Interface para repository (independente de implementação)."""

    def find_by_id(self, user_id: int) -> Optional[User]:
        ...

    def find_by_email(self, email: str) -> Optional[User]:
        ...

    def save(self, user: User) -> User:
        ...

    def find_all(self) -> List[User]:
        ...


# Use Case Layer (Application Logic)
class CreateUserUseCase:
    """
    Use case: Criar usuário.

    Orquestra lógica de aplicação (não de negócio!).
    Lógica de negócio está na Entity.
    """

    def __init__(self, repository: UserRepositoryPort):
        self.repository = repository

    def execute(self, email: str, name: str) -> User:
        """
        Executar use case.

        Regras:
        1. Email deve ser único (lógica de aplicação)
        2. Validações de negócio (na Entity)
        3. Persistir
        """
        # Verificar unicidade (lógica de aplicação)
        if self.repository.find_by_email(email):
            raise ValueError("Email já está em uso")

        # Criar entity (validações de negócio aqui)
        user = User(email=email, name=name)

        # Persistir
        return self.repository.save(user)


class GetUserUseCase:
    """Use case: Buscar usuário."""

    def __init__(self, repository: UserRepositoryPort):
        self.repository = repository

    def execute(self, user_id: int) -> Optional[User]:
        return self.repository.find_by_id(user_id)


# Adapter Layer (Implementação concreta)
class InMemoryUserRepository:
    """
    Adapter: Implementação do repositório.

    Pode ser trocado por PostgresRepository, MongoRepository, etc.
    """

    def __init__(self, db: list):
        self.db = db

    def find_by_id(self, user_id: int) -> Optional[User]:
        data = next((u for u in self.db if u["id"] == user_id), None)
        return User.from_dict(data) if data else None

    def find_by_email(self, email: str) -> Optional[User]:
        data = next((u for u in self.db if u["email"] == email), None)
        return User.from_dict(data) if data else None

    def save(self, user: User) -> User:
        data = user.to_dict()
        data["id"] = len(self.db) + 1
        self.db.append(data)
        return User.from_dict(data)

    def find_all(self) -> List[User]:
        return [User.from_dict(u) for u in self.db]


# Infrastructure Layer (FastAPI)
app_clean = FastAPI()

# Setup (Dependency Injection)
clean_repository = InMemoryUserRepository(USERS_DB)
create_user_use_case = CreateUserUseCase(clean_repository)
get_user_use_case = GetUserUseCase(clean_repository)


@app_clean.post("/users")
def create_user_clean(email: str, name: str):
    """
    Controller apenas adapta HTTP para use case.

    Sem lógica de negócio aqui!
    """
    try:
        user = create_user_use_case.execute(email, name)
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(400, str(e))


@app_clean.get("/users/{user_id}")
def get_user_clean(user_id: int):
    user = get_user_use_case.execute(user_id)
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return user.to_dict()


print("""
Camadas (dependências sempre para dentro):

  ┌─────────────────────────────────────┐
  │  Infrastructure (FastAPI)           │
  │  ┌───────────────────────────────┐  │
  │  │  Adapters (Repository impl)   │  │
  │  │  ┌─────────────────────────┐  │  │
  │  │  │  Use Cases              │  │  │
  │  │  │  ┌───────────────────┐  │  │  │
  │  │  │  │  Domain (Entity)  │  │  │  │
  │  │  │  └───────────────────┘  │  │  │
  │  │  └─────────────────────────┘  │  │
  │  └───────────────────────────────┘  │
  └─────────────────────────────────────┘

Benefícios:
  • Lógica de negócio testável SEM framework
  • Pode trocar FastAPI por Django sem mudar domínio
  • Pode trocar DB sem mudar use cases
  • Inversão de dependências

Trade-offs:
  • Mais código (interfaces, adapters)
  • Complexidade inicial maior
  • Vale a pena para domínios complexos

Linhas de código: ~200
Arquivos: 5 (entity, use_case, port, adapter, controller)
Complexidade: Alta
Testabilidade: Muito alta (testável sem DB/HTTP)
""")


# ============================================================================
# ARQUITETURA 4: DOMAIN-DRIVEN DESIGN (DDD)
# ============================================================================

print("\n" + "=" * 70)
print("ARQUITETURA 4: DOMAIN-DRIVEN DESIGN (DDD)")
print("=" * 70)

"""
Estrutura:
  domain/
    entities/       ← Objetos com identidade
    value_objects/  ← Objetos sem identidade
    aggregates/     ← Raízes de agregados
    repositories/   ← Interfaces de persistência
    domain_events/  ← Eventos de domínio
  application/
    commands/       ← Comandos (write)
    queries/        ← Queries (read)
  infrastructure/
    ...

✅ Prós:
  • Modelo rico (não anêmico)
  • Lógica de negócio explícita
  • Linguagem ubíqua (terms do negócio)
  • Escalável (bounded contexts)

❌ Contras:
  • Muito complexo
  • Curva de aprendizado íngreme
  • Overkill para CRUD simples
  • Requer experiência

🎯 Quando usar:
  • Domínio complexo
  • Muitas regras de negócio
  • Times grandes
  • Projeto de longa duração
"""


# Value Object (Imutável, sem identidade)
@dataclass(frozen=True)
class Email:
    """Value Object para email."""

    value: str

    def __post_init__(self):
        if not "@" in self.value:
            raise ValueError("Email inválido")

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class UserName:
    """Value Object para nome."""

    value: str

    def __post_init__(self):
        if len(self.value) < 3:
            raise ValueError("Nome deve ter pelo menos 3 caracteres")

    def __str__(self):
        return self.value


# Aggregate Root (Entity com identidade)
class UserAggregate:
    """
    Aggregate Root: Entidade principal do agregado.

    Encapsula lógica de negócio e garante invariantes.
    """

    def __init__(
        self,
        email: Email,
        name: UserName,
        id: Optional[int] = None
    ):
        self._id = id
        self._email = email
        self._name = name
        self._created_at = datetime.now()
        self._is_active = True

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def email(self) -> Email:
        return self._email

    @property
    def name(self) -> UserName:
        return self._name

    @property
    def is_active(self) -> bool:
        return self._is_active

    def deactivate(self):
        """
        Desativar usuário (método de negócio).

        Lógica de negócio: Usuário não pode ser deletado,
        apenas desativado.
        """
        if not self._is_active:
            raise ValueError("Usuário já está inativo")

        self._is_active = False
        # Poderia disparar evento: UserDeactivatedEvent

    def change_email(self, new_email: Email):
        """
        Mudar email (método de negócio).

        Lógica: Email deve ser único (verificado na aplicação).
        """
        if self._email == new_email:
            return

        self._email = new_email
        # Poderia disparar evento: UserEmailChangedEvent


# Application Service (CQRS - Command)
class CreateUserCommand:
    """Command: Intenção de criar usuário."""

    def __init__(self, email: str, name: str):
        self.email = email
        self.name = name


class CreateUserCommandHandler:
    """Handler para comando de criação."""

    def __init__(self, repository: UserRepositoryPort):
        self.repository = repository

    def handle(self, command: CreateUserCommand) -> UserAggregate:
        """
        Executar comando.

        1. Criar value objects (validação)
        2. Verificar regras de negócio
        3. Criar aggregate
        4. Persistir
        """
        # Value objects (validação automática)
        email = Email(command.email)
        name = UserName(command.name)

        # Verificar unicidade
        if self.repository.find_by_email(email.value):
            raise ValueError("Email já está em uso")

        # Criar aggregate
        user = UserAggregate(email=email, name=name)

        # Persistir
        return self.repository.save(user)


print("""
Conceitos DDD:

1. Value Objects (Email, UserName)
   • Imutáveis
   • Sem identidade
   • Validação no construtor

2. Entities (User)
   • Tem identidade (ID)
   • Mutável
   • Lógica de negócio encapsulada

3. Aggregates (UserAggregate)
   • Root entity
   • Garante invariantes
   • Boundary transacional

4. Commands (CreateUserCommand)
   • Intenção de mudança
   • Linguagem ubíqua
   • CQRS pattern

5. Domain Events (UserCreatedEvent)
   • Comunicação entre agregados
   • Event sourcing (opcional)

Benefícios:
  • Modelo rico (não anêmico)
  • Invariantes garantidas
  • Linguagem ubíqua
  • Evolução do modelo

Quando usar:
  • Domínio complexo (não CRUD simples)
  • Muitas regras de negócio
  • Bounded contexts
  • Time experiente

Linhas de código: ~250+
Arquivos: 10+ (muitos conceitos)
Complexidade: Muito alta
Testabilidade: Muito alta
""")


# ============================================================================
# COMPARAÇÃO FINAL
# ============================================================================

print("\n" + "=" * 70)
print("COMPARAÇÃO FINAL")
print("=" * 70)

print("""
┌─────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Aspecto         │ Simple   │ Layered  │ Clean    │ DDD      │
├─────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Linhas código   │ ~50      │ ~120     │ ~200     │ ~250+    │
│ Arquivos        │ 1        │ 3        │ 5        │ 10+      │
│ Complexidade    │ ⭐       │ ⭐⭐     │ ⭐⭐⭐   │ ⭐⭐⭐⭐  │
│ Testabilidade   │ ⭐       │ ⭐⭐⭐   │ ⭐⭐⭐⭐  │ ⭐⭐⭐⭐  │
│ Manutenibilidade│ ⭐       │ ⭐⭐⭐   │ ⭐⭐⭐⭐  │ ⭐⭐⭐⭐  │
│ Velocidade dev  │ ⭐⭐⭐⭐  │ ⭐⭐⭐   │ ⭐⭐     │ ⭐       │
│ Escalabilidade  │ ⭐       │ ⭐⭐⭐   │ ⭐⭐⭐⭐  │ ⭐⭐⭐⭐  │
└─────────────────┴──────────┴──────────┴──────────┴──────────┘

🎯 QUANDO USAR CADA UMA:

┌─────────────────────────────────────────────────────────────┐
│  Simple (Procedural)                                        │
├─────────────────────────────────────────────────────────────┤
│  ✅ MVP / Protótipo                                         │
│  ✅ Script / Ferramenta interna                             │
│  ✅ Projeto pessoal pequeno                                 │
│  ✅ Time de 1 pessoa                                        │
│  ❌ Projeto comercial que vai crescer                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Layered Architecture (MVC)                                 │
├─────────────────────────────────────────────────────────────┤
│  ✅ Maioria dos projetos (80% dos casos)                   │
│  ✅ CRUD com lógica de negócio moderada                     │
│  ✅ Times pequenos a médios (2-10 devs)                     │
│  ✅ Prazos apertados                                        │
│  ✅ Padrão conhecido pela indústria                         │
│  ❌ Domínio muito complexo                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Clean Architecture (Hexagonal)                             │
├─────────────────────────────────────────────────────────────┤
│  ✅ Lógica de negócio complexa                              │
│  ✅ Precisa trocar DB/framework no futuro                   │
│  ✅ Testabilidade é prioridade                              │
│  ✅ Times médios a grandes (5-20 devs)                      │
│  ✅ Projeto de longa duração (5+ anos)                      │
│  ❌ CRUD simples (overkill)                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Domain-Driven Design (DDD)                                 │
├─────────────────────────────────────────────────────────────┤
│  ✅ Domínio MUITO complexo                                  │
│  ✅ Muitas regras de negócio                                │
│  ✅ Times grandes (20+ devs)                                │
│  ✅ Bounded contexts (microsserviços)                       │
│  ✅ Time sênior experiente                                  │
│  ❌ CRUD simples (overkill extremo)                         │
│  ❌ Prazos apertados                                        │
│  ❌ Time júnior                                             │
└─────────────────────────────────────────────────────────────┘

💡 REGRA DE OURO:

  "Comece simples, refatore quando necessário"

  MVP → Simple
  Cresce → Layered
  Complexo → Clean
  Muito complexo → DDD

  Não use DDD para TODO list!
  Não use Simple para e-commerce!

📈 EVOLUÇÃO NATURAL:

  Simple → Layered → Clean → DDD
    ↓        ↓        ↓       ↓
  1 mês   6 meses  1 ano   2+ anos

🎓 RECOMENDAÇÃO:

  • 90% dos projetos: Layered Architecture
  • 5% dos projetos: Clean Architecture
  • 3% dos projetos: DDD
  • 2% dos projetos: Simple (protótipos)

  Não siga hype! Use o que resolve seu problema.
""")


# ============================================================================
# EXEMPLO PRÁTICO: QUANDO REFATORAR
# ============================================================================

print("\n" + "=" * 70)
print("SINAIS DE QUE PRECISA REFATORAR ARQUITETURA")
print("=" * 70)

print("""
🚨 Simple → Layered:
  • Endpoints com 100+ linhas
  • Lógica duplicada em múltiplos endpoints
  • Difícil adicionar testes
  • "God file" com 1000+ linhas

🚨 Layered → Clean:
  • Services viram "god classes" (1000+ linhas)
  • Difícil testar sem mockar DB/HTTP
  • Lógica de negócio espalhada
  • Quer trocar FastAPI por Django

🚨 Clean → DDD:
  • Domínio com 10+ entidades relacionadas
  • Muitas regras de negócio complexas
  • Invariantes difíceis de garantir
  • Time discute modelagem semanalmente

📊 MÉTRICAS:

  Linhas por arquivo:
    < 200 linhas → OK
    200-500 → Considere refatorar
    > 500 → Refatore urgente!

  Complexidade ciclomática:
    < 10 → OK
    10-20 → Complexo
    > 20 → Refatore urgente!

  Test coverage:
    > 80% → Boa arquitetura
    50-80% → OK
    < 50% → Arquitetura dificulta testes

⏱️ TEMPO DE REFATORAÇÃO:

  Simple → Layered: 1-2 semanas
  Layered → Clean: 1-2 meses
  Clean → DDD: 3-6 meses

  Vale a pena? Depende do projeto!
""")

print("\n" + "=" * 70)
print("CONCLUSÃO")
print("=" * 70)

print("""
Não existe "melhor arquitetura". Existe arquitetura
apropriada para o contexto.

Fatores decisórios:
  • Tamanho do projeto
  • Complexidade do domínio
  • Tamanho do time
  • Experiência do time
  • Prazo
  • Orçamento

🏆 Para a MAIORIA dos projetos:
   → Layered Architecture (Repository + Service + Controller)

   Simples o suficiente para ser produtivo.
   Complexo o suficiente para escalar.

🚀 Comece simples, refatore quando doer!
""")

if __name__ == "__main__":
    print("\n\n📝 Execute este script para ver todas as comparações!")
