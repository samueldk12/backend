# Exercício 02 - CRUD de Usuários

## 🎯 Objetivo

Implementar um CRUD completo de usuários mostrando **múltiplas formas** de fazer cada operação e explicando **qual é a melhor e por quê**.

---

## 📚 O que vamos aprender

1. **3 formas de estruturar models** (qual escolher?)
2. **2 formas de validação** (Pydantic vs custom)
3. **3 formas de hash de senha** (bcrypt vs argon2 vs scrypt)
4. **2 formas de estruturar endpoints** (procedural vs service layer)
5. **3 formas de tratamento de erros**
6. **2 formas de pagination**

---

## 🗂️ Estrutura de Arquivos

```
exercicio-02-usuarios/
├── README.md                    # Este arquivo
├── app/
│   ├── models/
│   │   └── user.py              # SQLAlchemy model
│   ├── schemas/
│   │   └── user.py              # Pydantic schemas
│   ├── repositories/            # Data access layer
│   │   └── user_repository.py
│   ├── services/                # Business logic
│   │   └── user_service.py
│   ├── api/v1/endpoints/
│   │   ├── users_simple.py      # Forma 1: Simples/Procedural
│   │   ├── users_layered.py     # Forma 2: Layered Architecture
│   │   └── users_repository.py  # Forma 3: Repository Pattern
│   └── core/
│       └── security.py          # Password hashing
├── tests/
│   └── test_users.py
└── comparacao.md                # Comparação das abordagens
```

---

## 📝 PARTE 1: Models

### Forma 1: Model Anêmico (apenas dados)

```python
# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    """
    Model anêmico: apenas campos, sem lógica.

    ✅ Prós:
      • Simples
      • Fácil de entender
      • Bom para CRUD simples

    ❌ Contras:
      • Lógica espalha pelo código
      • Difícil de manter quando cresce
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Forma 2: Active Record (model com métodos)

```python
class User(Base):
    """
    Active Record: model com lógica.

    ✅ Prós:
      • Lógica próxima dos dados
      • Conveniente (user.save())
      • Usado no Ruby on Rails

    ❌ Contras:
      • Viola Single Responsibility
      • Dificulta testes (mock database)
      • Acopla model ao ORM
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    # ... outros campos

    def save(self, db):
        """Salvar usuário."""
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    def delete(self, db):
        """Deletar usuário."""
        db.delete(self)
        db.commit()

    def is_password_valid(self, password: str) -> bool:
        """Verificar senha."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.hashed_password)

    @classmethod
    def get_by_email(cls, db, email: str):
        """Buscar por email."""
        return db.query(cls).filter(cls.email == email).first()
```

### Forma 3: Domain Model (recomendado para projetos complexos)

```python
class User(Base):
    """
    Domain Model: model com lógica de negócio, mas sem acesso a DB.

    ✅ Prós:
      • Lógica de negócio encapsulada
      • Testável (sem mock de DB)
      • Segue DDD

    ❌ Contras:
      • Mais código
      • Curva de aprendizado
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    # ... outros campos

    def change_email(self, new_email: str):
        """
        Mudar email (lógica de negócio).

        Regras:
        - Email deve ser único (validado no repository)
        - Deve enviar email de confirmação
        """
        # Validação básica
        if not "@" in new_email:
            raise ValueError("Email inválido")

        self.email = new_email
        # Repository vai lidar com persistência
        # Service vai lidar com envio de email

    def deactivate(self):
        """Desativar conta."""
        if not self.is_active:
            raise ValueError("Usuário já está inativo")

        self.is_active = False
        # Pode adicionar lógica: cancelar assinaturas, etc

    @property
    def is_email_verified(self) -> bool:
        """Verificar se email foi confirmado."""
        return hasattr(self, 'email_verified_at') and self.email_verified_at is not None
```

### 🎯 Qual Usar?

```
Projeto pequeno/MVP        → Forma 1 (Anêmico)
Projeto médio              → Forma 1 ou 3
Projeto grande/complexo    → Forma 3 (Domain Model)
Time sem experiência       → Forma 1
```

---

## 📝 PARTE 2: Schemas (Pydantic)

```python
# app/schemas/user.py

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

# Base comum
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)

    @validator('username')
    def username_alphanumeric(cls, v):
        """Username deve ser alfanumérico."""
        if not v.isalnum():
            raise ValueError('Username deve conter apenas letras e números')
        return v

# Criação (o que cliente envia)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @validator('password')
    def password_strength(cls, v):
        """Validar força da senha."""
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve conter maiúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve conter número')
        return v

# Atualização (campos opcionais)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)

# Resposta (o que API retorna)
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True  # Permite criar de SQLAlchemy model

# Resposta com dados sensíveis (para admin)
class UserResponseAdmin(UserResponse):
    hashed_password: str  # Admin pode ver hash
```

---

## 📝 PARTE 3: Security (Password Hashing)

```python
# app/core/security.py

from passlib.context import CryptContext
import bcrypt
import hashlib

# ============================================================================
# FORMA 1: BCRYPT (Mais usado)
# ============================================================================

pwd_context_bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password_bcrypt(password: str) -> str:
    """
    Hash com bcrypt.

    ✅ Prós:
      • Padrão da indústria
      • Amplamente testado
      • Resistente a rainbow tables
      • Configurável (rounds)

    ❌ Contras:
      • Limitado a 72 caracteres
      • Mais lento que argon2 (mas isso é bom!)

    Recomendado: SIM (padrão)
    """
    return pwd_context_bcrypt.hash(password)

def verify_password_bcrypt(plain_password: str, hashed_password: str) -> bool:
    """Verificar senha com bcrypt."""
    return pwd_context_bcrypt.verify(plain_password, hashed_password)


# ============================================================================
# FORMA 2: ARGON2 (Mais moderno)
# ============================================================================

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def hash_password_argon2(password: str) -> str:
    """
    Hash com argon2.

    ✅ Prós:
      • Vencedor do Password Hashing Competition (2015)
      • Resistente a ataques GPU/ASIC
      • Mais seguro que bcrypt teoricamente
      • Sem limite de caracteres

    ❌ Contras:
      • Menos adotado (ainda)
      • Requer biblioteca C

    Recomendado: SIM (para novos projetos)
    """
    return ph.hash(password)

def verify_password_argon2(plain_password: str, hashed_password: str) -> bool:
    """Verificar senha com argon2."""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


# ============================================================================
# FORMA 3: PBKDF2 (Django usa)
# ============================================================================

import hashlib
import os
import base64

def hash_password_pbkdf2(password: str, iterations: int = 390000) -> str:
    """
    Hash com PBKDF2.

    ✅ Prós:
      • Padrão NIST
      • Implementado em stdlib (sem dependência)
      • Usado no Django

    ❌ Contras:
      • Mais vulnerável a GPU attacks que bcrypt/argon2
      • Precisa armazenar salt separado

    Recomendado: NÃO (prefira bcrypt ou argon2)
    """
    salt = os.urandom(32)
    hash_value = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations
    )
    # Armazenar salt + hash
    storage = salt + hash_value
    return base64.b64encode(storage).decode('utf-8')

def verify_password_pbkdf2(plain_password: str, hashed_password: str, iterations: int = 390000) -> bool:
    """Verificar senha com PBKDF2."""
    storage = base64.b64decode(hashed_password.encode('utf-8'))
    salt = storage[:32]
    stored_hash = storage[32:]

    new_hash = hashlib.pbkdf2_hmac(
        'sha256',
        plain_password.encode('utf-8'),
        salt,
        iterations
    )

    return new_hash == stored_hash


# ============================================================================
# COMPARAÇÃO
# ============================================================================

"""
┌──────────────────┬──────────┬────────────┬─────────────┬────────────┐
│ Algoritmo        │ Segurança│ Performance│ Adoção      │ Recomendado│
├──────────────────┼──────────┼────────────┼─────────────┼────────────┤
│ bcrypt           │ ★★★★☆    │ Lento      │ Muito alta  │ ✅ SIM     │
│ argon2           │ ★★★★★    │ Lento      │ Crescendo   │ ✅ SIM     │
│ PBKDF2           │ ★★★☆☆    │ Médio      │ Média       │ ⚠️ Evitar  │
│ SHA256 (sozinho) │ ★☆☆☆☆    │ Rápido     │ -           │ ❌ NUNCA   │
└──────────────────┴──────────┴────────────┴─────────────┴────────────┘

🎯 ESCOLHA:

Novo projeto    → argon2 (mais seguro)
Compatibilidade → bcrypt (padrão da indústria)
Django existente→ PBKDF2 (já usa)

❌ NUNCA USE:
  • MD5 (quebrado)
  • SHA1 (quebrado)
  • SHA256 sozinho (rápido demais, rainbow tables)
  • Senha em plain text (óbvio!)
"""

# Usar bcrypt por padrão (mais compatível)
hash_password = hash_password_bcrypt
verify_password = verify_password_bcrypt
```

---

## 📝 PARTE 4: Repository Pattern

```python
# app/repositories/user_repository.py

from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password

class UserRepository:
    """
    Repository Pattern: Isola acesso ao banco de dados.

    Vantagens:
    - Testável (mock repository)
    - Troca de banco fica mais fácil
    - Lógica de query centralizada
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Buscar usuário por ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Buscar usuário por email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """Buscar usuário por username."""
        return self.db.query(User).filter(User.username == username).first()

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[User]:
        """Listar usuários com paginação."""
        query = self.db.query(User)

        if active_only:
            query = query.filter(User.is_active == True)

        return query.offset(skip).limit(limit).all()

    def create(self, user_create: UserCreate) -> User:
        """Criar novo usuário."""
        # Hash da senha
        hashed_password = hash_password(user_create.password)

        # Criar objeto
        db_user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
        )

        # Salvar no banco
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def update(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Atualizar usuário."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            return None

        # Atualizar apenas campos fornecidos
        update_data = user_update.dict(exclude_unset=True)

        # Hash nova senha se fornecida
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(db_user, field, value)

        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def delete(self, user_id: int) -> bool:
        """Deletar usuário."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            return False

        self.db.delete(db_user)
        self.db.commit()

        return True

    def exists_by_email(self, email: str) -> bool:
        """Verificar se email já existe."""
        return self.db.query(User.id).filter(User.email == email).first() is not None

    def exists_by_username(self, username: str) -> bool:
        """Verificar se username já existe."""
        return self.db.query(User.id).filter(User.username == username).first() is not None
```

---

## 📝 PARTE 5: Endpoints

### Forma 1: Simples/Procedural (bom para MVPs)

```python
# app/api/v1/endpoints/users_simple.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.security import hash_password

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Criar usuário (forma simples).

    ✅ Prós:
      • Código direto e fácil de entender
      • Rápido de escrever
      • Bom para protótipos/MVPs

    ❌ Contras:
      • Lógica no endpoint (hard to test)
      • Duplicação de código
      • Dificulta reutilização
    """
    # Verificar se email já existe
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está em uso"
        )

    # Hash senha
    hashed_password = hash_password(user.password)

    # Criar usuário
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Buscar usuário por ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return user


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Listar usuários."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users
```

### Forma 2: Repository Pattern (recomendado)

```python
# app/api/v1/endpoints/users_repository.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Dependency para obter repository."""
    return UserRepository(db)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    repository: UserRepository = Depends(get_user_repository)
):
    """
    Criar usuário (com repository pattern).

    ✅ Prós:
      • Lógica isolada e testável
      • Reutilizável
      • Fácil de mockar em testes
      • Troca de DB facilitada

    ❌ Contras:
      • Mais código
      • Mais arquivos
    """
    # Verificar duplicatas
    if repository.exists_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está em uso"
        )

    if repository.exists_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já está em uso"
        )

    # Criar usuário
    db_user = repository.create(user)

    return db_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    repository: UserRepository = Depends(get_user_repository)
):
    """Buscar usuário por ID."""
    user = repository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return user


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    repository: UserRepository = Depends(get_user_repository)
):
    """Listar usuários."""
    users = repository.get_multi(skip=skip, limit=limit, active_only=active_only)
    return users


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserUpdate,
    repository: UserRepository = Depends(get_user_repository)
):
    """Atualizar usuário."""
    db_user = repository.update(user_id, user)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    repository: UserRepository = Depends(get_user_repository)
):
    """Deletar usuário."""
    success = repository.delete(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return None
```

---

## 🎯 COMPARAÇÃO FINAL E RECOMENDAÇÃO

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUAL ABORDAGEM USAR?                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ MVP / Prototipo              → Forma 1 (Simple/Procedural)     │
│ Startup pequena (1-3 devs)  → Forma 1                          │
│ Projeto médio (3-10 devs)   → Forma 2 (Repository)             │
│ Projeto grande (10+ devs)   → Forma 2 + Service Layer          │
│ Sistema complexo             → Forma 2 + DDD                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

🏆 RECOMENDAÇÃO GERAL: **Repository Pattern** (Forma 2)

Por quê?
✅ Testável
✅ Organizado
✅ Escalável
✅ Não adiciona muita complexidade
✅ Facilita evolução do código

Evolução natural:
  Simple → Repository → Repository + Service → DDD
```

---

## 📋 Checklist de Implementação

- [ ] Models SQLAlchemy criados
- [ ] Indexes em email e username
- [ ] Schemas Pydantic com validação
- [ ] Password hashing com bcrypt
- [ ] Repository implementado
- [ ] Endpoints CRUD completos
- [ ] Testes unitários (repository)
- [ ] Testes de integração (endpoints)
- [ ] Documentação no Swagger
- [ ] Tratamento de erros padronizado

---

## 🧪 Testando

```bash
# Rodar servidor
uvicorn app.main:app --reload

# Criar usuário
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "joao@example.com",
    "username": "joaosilva",
    "full_name": "João Silva",
    "password": "SenhaForte123"
  }'

# Listar usuários
curl "http://localhost:8000/api/v1/users/"

# Buscar usuário
curl "http://localhost:8000/api/v1/users/1"

# Atualizar usuário
curl -X PUT "http://localhost:8000/api/v1/users/1" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "João Silva Santos"}'

# Deletar usuário
curl -X DELETE "http://localhost:8000/api/v1/users/1"
```

---

## 📚 Conceitos Aplicados

✅ **Módulo 01**: Não usado diretamente (sem threads/async aqui)
✅ **Módulo 02**: REST API, JSON, HTTP status codes
✅ **Módulo 03**: SQLAlchemy ORM, indexes, queries otimizadas
✅ **Módulo 04**: Layered Architecture, Repository Pattern

---

## 🎯 Próximos Passos

- **[Exercício 03](../exercicio-03-autenticacao/)**: Autenticação com JWT
- Adicionar middleware de autenticação
- Proteger endpoints
- Refresh tokens

---

Este exercício forma a base de toda a aplicação. Entender as diferentes abordagens é fundamental para tomar decisões arquiteturais inteligentes! 🚀
