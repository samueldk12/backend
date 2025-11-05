"""
Exemplo: Clean Architecture em Prática

Execute: uvicorn 01_clean_architecture:app --reload

Este exemplo demonstra Clean Architecture com camadas bem separadas.
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Protocol
from abc import ABC, abstractmethod
from datetime import datetime
import uvicorn

# ============================================
# DOMAIN LAYER (Entities & Business Rules)
# ============================================

class User:
    """
    Entity: Representa um usuário no domínio

    Contém APENAS lógica de negócio pura, sem dependências externas
    """
    def __init__(self, id: int, email: str, name: str, is_active: bool = True):
        self.id = id
        self.email = email
        self.name = name
        self.is_active = is_active
        self.created_at = datetime.now()

    def deactivate(self):
        """Regra de negócio: desativar usuário"""
        if not self.is_active:
            raise ValueError("User is already inactive")
        self.is_active = False

    def activate(self):
        """Regra de negócio: ativar usuário"""
        if self.is_active:
            raise ValueError("User is already active")
        self.is_active = True

    def change_email(self, new_email: str):
        """Regra de negócio: trocar email com validação"""
        if '@' not in new_email:
            raise ValueError("Invalid email format")
        if new_email == self.email:
            raise ValueError("New email must be different")
        self.email = new_email

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }


# ============================================
# PORTS (Interfaces/Protocols)
# ============================================

class IUserRepository(ABC):
    """
    Port: Interface para repositório de usuários

    Define O QUE precisa ser feito, não COMO
    """
    @abstractmethod
    def find_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def find_all(self) -> List[User]:
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        pass

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        pass


class IEmailService(ABC):
    """Port: Interface para serviço de email"""
    @abstractmethod
    def send_welcome_email(self, email: str, name: str) -> bool:
        pass


# ============================================
# USE CASES (Application Layer)
# ============================================

class CreateUserUseCase:
    """
    Use Case: Criar usuário

    Contém lógica de aplicação (orquestração)
    Depende apenas de abstrações (interfaces)
    """
    def __init__(self, user_repository: IUserRepository, email_service: IEmailService):
        self.user_repository = user_repository
        self.email_service = email_service

    def execute(self, email: str, name: str) -> User:
        # 1. Validação: email já existe?
        existing_user = self.user_repository.find_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        # 2. Criar entity (domínio)
        new_user = User(
            id=self._generate_id(),
            email=email,
            name=name
        )

        # 3. Persistir
        saved_user = self.user_repository.save(new_user)

        # 4. Side effect: enviar email de boas-vindas
        self.email_service.send_welcome_email(saved_user.email, saved_user.name)

        return saved_user

    def _generate_id(self) -> int:
        # Simplificado: na prática viria do DB
        return len(self.user_repository.find_all()) + 1


class DeactivateUserUseCase:
    """Use Case: Desativar usuário"""
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def execute(self, user_id: int) -> User:
        # 1. Buscar usuário
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # 2. Aplicar regra de negócio (domínio)
        user.deactivate()

        # 3. Persistir
        return self.user_repository.save(user)


class ListActiveUsersUseCase:
    """Use Case: Listar usuários ativos"""
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def execute(self) -> List[User]:
        all_users = self.user_repository.find_all()
        return [u for u in all_users if u.is_active]


# ============================================
# ADAPTERS (Infrastructure Layer)
# ============================================

class InMemoryUserRepository(IUserRepository):
    """
    Adapter: Implementação em memória do repositório

    Implementa a interface (port) definida no domínio
    Poderia ser substituído por PostgreSQLUserRepository, etc.
    """
    def __init__(self):
        self._users: dict[int, User] = {}

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def find_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def find_all(self) -> List[User]:
        return list(self._users.values())

    def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def delete(self, user_id: int) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False


class FakeEmailService(IEmailService):
    """
    Adapter: Implementação fake do serviço de email

    Em produção seria SendGridEmailService, SESEmailService, etc.
    """
    def send_welcome_email(self, email: str, name: str) -> bool:
        print(f"📧 [FAKE EMAIL] Sending welcome to {name} at {email}")
        return True


# ============================================
# INTERFACE LAYER (Controllers/API)
# ============================================

# Dependency Injection Container
def get_user_repository() -> IUserRepository:
    """DI: Fornece instância do repositório"""
    if not hasattr(get_user_repository, "_instance"):
        get_user_repository._instance = InMemoryUserRepository()
    return get_user_repository._instance


def get_email_service() -> IEmailService:
    """DI: Fornece instância do serviço de email"""
    if not hasattr(get_email_service, "_instance"):
        get_email_service._instance = FakeEmailService()
    return get_email_service._instance


# DTOs (Data Transfer Objects)
class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    created_at: str


# FastAPI Application
app = FastAPI(title="Clean Architecture Example")


@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    request: CreateUserRequest,
    user_repo: IUserRepository = Depends(get_user_repository),
    email_service: IEmailService = Depends(get_email_service)
):
    """
    Endpoint: Criar usuário

    Controller delega para Use Case
    """
    use_case = CreateUserUseCase(user_repo, email_service)

    try:
        user = use_case.execute(request.email, request.name)
        return UserResponse(**user.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users", response_model=List[UserResponse])
def list_active_users(
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Endpoint: Listar usuários ativos"""
    use_case = ListActiveUsersUseCase(user_repo)
    users = use_case.execute()
    return [UserResponse(**u.to_dict()) for u in users]


@app.post("/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Endpoint: Desativar usuário"""
    use_case = DeactivateUserUseCase(user_repo)

    try:
        user = use_case.execute(user_id)
        return UserResponse(**user.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================
# TESTS (fácil de testar!)
# ============================================

def test_create_user_use_case():
    """
    Teste unitário puro do Use Case

    Não precisa de DB, API, nada externo!
    """
    # Arrange
    repo = InMemoryUserRepository()
    email_service = FakeEmailService()
    use_case = CreateUserUseCase(repo, email_service)

    # Act
    user = use_case.execute("test@example.com", "Test User")

    # Assert
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.is_active == True
    print("✅ Test passed: Create user use case")


def test_deactivate_user_business_rule():
    """Teste da regra de negócio do domínio"""
    # Arrange
    user = User(1, "test@example.com", "Test", is_active=True)

    # Act
    user.deactivate()

    # Assert
    assert user.is_active == False

    # Act again (should raise error)
    try:
        user.deactivate()
        assert False, "Should have raised error"
    except ValueError as e:
        assert "already inactive" in str(e)

    print("✅ Test passed: Deactivate business rule")


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🏗️  CLEAN ARCHITECTURE EXAMPLE")
    print("=" * 60)
    print()
    print("Layers:")
    print("  1. Domain    → User entity (business rules)")
    print("  2. Use Cases → CreateUser, DeactivateUser")
    print("  3. Adapters  → InMemoryRepository, FakeEmailService")
    print("  4. Interface → FastAPI controllers")
    print()
    print("Benefits:")
    print("  ✅ Testable (no external dependencies)")
    print("  ✅ Flexible (swap implementations easily)")
    print("  ✅ Maintainable (clear separation of concerns)")
    print()
    print("=" * 60)
    print()

    # Run tests
    test_create_user_use_case()
    test_deactivate_user_business_rule()

    print()
    print("🚀 Starting API...")
    print("📖 Docs: http://localhost:8000/docs")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
ARCHITECTURE DIAGRAM:

┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                          │
│  (FastAPI Controllers, DTOs, Dependency Injection)          │
│                                                             │
│  POST /users        → CreateUserUseCase                    │
│  GET  /users        → ListActiveUsersUseCase               │
│  POST /users/:id/.. → DeactivateUserUseCase                │
└────────────────────┬────────────────────────────────────────┘
                     │ depends on (abstraction)
┌────────────────────▼────────────────────────────────────────┐
│                  APPLICATION LAYER                          │
│           (Use Cases - Application Logic)                   │
│                                                             │
│  CreateUserUseCase(repo, email_service)                    │
│  DeactivateUserUseCase(repo)                               │
│  ListActiveUsersUseCase(repo)                              │
└────────────────────┬────────────────────────────────────────┘
                     │ uses
┌────────────────────▼────────────────────────────────────────┐
│                    DOMAIN LAYER                             │
│          (Entities - Business Rules)                        │
│                                                             │
│  User                                                       │
│    - deactivate()  ← Business Rule                        │
│    - activate()    ← Business Rule                        │
│    - change_email() ← Business Rule                       │
└─────────────────────────────────────────────────────────────┘
                     △ implements
┌────────────────────┴────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                        │
│        (Adapters - External Implementations)                │
│                                                             │
│  InMemoryUserRepository implements IUserRepository         │
│  FakeEmailService implements IEmailService                 │
│                                                             │
│  (Could be: PostgreSQLRepo, SendGridEmail, etc.)          │
└─────────────────────────────────────────────────────────────┘

DEPENDENCY RULE:
→ Outer layers depend on Inner layers
→ Inner layers NEVER depend on Outer layers
→ All dependencies point INWARD
"""
