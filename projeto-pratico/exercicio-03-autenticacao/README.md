# Exercício 03 - Autenticação e Autorização

## 🎯 Objetivo

Implementar autenticação segura com JWT, comparando diferentes abordagens e explicando as melhores práticas de segurança.

---

## 📚 O que vamos aprender

1. **3 tipos de autenticação** (JWT vs Session vs OAuth2)
2. **Access tokens vs Refresh tokens**
3. **Password reset flow**
4. **RBAC (Role-Based Access Control)**
5. **2FA (Two-Factor Authentication)**
6. **Rate limiting em login**
7. **Security best practices**

---

## 🔐 PARTE 1: Tipos de Autenticação

### 1.1 Session-Based (Tradicional)

```python
"""
SESSION-BASED AUTHENTICATION

Como funciona:
1. User faz login
2. Servidor cria sessão e armazena no banco/Redis
3. Servidor retorna cookie com session_id
4. User envia cookie em cada request
5. Servidor valida session_id

┌────────┐           ┌────────┐           ┌─────────┐
│ Client │           │ Server │           │ Session │
│        │           │        │           │  Store  │
└───┬────┘           └───┬────┘           └────┬────┘
    │                    │                     │
    │ POST /login        │                     │
    ├───────────────────>│                     │
    │ email + password   │                     │
    │                    │                     │
    │                    │ Create session      │
    │                    ├────────────────────>│
    │                    │                     │
    │ Set-Cookie:        │                     │
    │ session_id=abc123  │                     │
    │<───────────────────┤                     │
    │                    │                     │
    │ GET /profile       │                     │
    │ Cookie: abc123     │                     │
    ├───────────────────>│                     │
    │                    │ Validate session    │
    │                    ├────────────────────>│
    │                    │ User data           │
    │                    │<────────────────────┤
    │ Profile data       │                     │
    │<───────────────────┤                     │
"""

from datetime import datetime, timedelta
import secrets
import redis

# Redis para armazenar sessões
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def create_session(user_id: int) -> str:
    """
    Criar sessão.

    ✅ Prós:
      • Servidor tem controle total (pode invalidar)
      • Fácil de revogar (delete da session store)
      • Pode armazenar dados complexos

    ❌ Contras:
      • Stateful (dificulta escala horizontal)
      • Requer session store (Redis/DB)
      • Cookies não funcionam bem com mobile apps
    """
    session_id = secrets.token_urlsafe(32)

    # Armazenar no Redis (expira em 24h)
    redis_client.setex(
        f"session:{session_id}",
        86400,  # 24 horas
        str(user_id)
    )

    return session_id

def validate_session(session_id: str) -> Optional[int]:
    """Validar sessão."""
    user_id = redis_client.get(f"session:{session_id}")
    return int(user_id) if user_id else None

def delete_session(session_id: str):
    """Logout: deletar sessão."""
    redis_client.delete(f"session:{session_id}")

# Endpoint
from fastapi import Cookie, HTTPException

@router.post("/login")
def login(credentials: LoginRequest, response: Response):
    user = authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(401, "Credenciais inválidas")

    # Criar sessão
    session_id = create_session(user.id)

    # Definir cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,  # Não acessível via JavaScript (XSS protection)
        secure=True,     # Apenas HTTPS
        samesite="lax",  # CSRF protection
        max_age=86400    # 24 horas
    )

    return {"message": "Login realizado"}

@router.get("/profile")
def get_profile(session_id: str = Cookie(None)):
    if not session_id:
        raise HTTPException(401, "Não autenticado")

    user_id = validate_session(session_id)
    if not user_id:
        raise HTTPException(401, "Sessão inválida")

    user = get_user(user_id)
    return user

@router.post("/logout")
def logout(session_id: str = Cookie(None)):
    if session_id:
        delete_session(session_id)
    return {"message": "Logout realizado"}
```

### 1.2 JWT (JSON Web Token) - RECOMENDADO

```python
"""
JWT AUTHENTICATION

Como funciona:
1. User faz login
2. Servidor cria JWT (assina com secret key)
3. Servidor retorna JWT para cliente
4. Cliente envia JWT em header Authorization
5. Servidor valida assinatura do JWT

┌────────┐           ┌────────┐
│ Client │           │ Server │
└───┬────┘           └───┬────┘
    │                    │
    │ POST /login        │
    ├───────────────────>│
    │ email + password   │
    │                    │
    │ JWT token          │  (Servidor cria e assina JWT)
    │<───────────────────┤
    │                    │
    │ GET /profile       │
    │ Authorization:     │
    │ Bearer <JWT>       │
    ├───────────────────>│  (Servidor valida assinatura)
    │                    │
    │ Profile data       │
    │<───────────────────┤

JWT Structure:
  header.payload.signature

  header:    {"alg": "HS256", "typ": "JWT"}
  payload:   {"user_id": 123, "exp": 1234567890}
  signature: HMACSHA256(header + payload, secret_key)
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuração
SECRET_KEY = "your-secret-key-change-in-production"  # openssl rand -hex 32
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Criar JWT token.

    ✅ Prós:
      • Stateless (não requer DB/Redis)
      • Escala horizontalmente (qualquer servidor pode validar)
      • Funciona bem com mobile apps
      • Padrão da indústria

    ❌ Contras:
      • Não pode revogar facilmente (precisa esperar expirar)
      • Token grande (mais bytes que session_id)
      • Se secret vazar, todos os tokens são comprometidos
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})

    # Assinar token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verificar e decodificar JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency para obter usuário autenticado.

    Uso:
        @router.get("/profile")
        def get_profile(current_user: User = Depends(get_current_user)):
            return current_user
    """
    token = credentials.credentials
    payload = verify_token(token)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(401, "Token inválido")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(401, "Usuário não encontrado")

    return user


# Endpoints
@router.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login e gerar JWT."""
    # Autenticar usuário
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(401, "Email ou senha incorretos")

    if not user.is_active:
        raise HTTPException(400, "Usuário inativo")

    # Criar token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me")
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Perfil do usuário autenticado."""
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout com JWT.

    Nota: JWT é stateless, então não há como revogar token.
    Opções:
    1. Cliente deleta token (simples, mas não impede uso se vazou)
    2. Blacklist de tokens (adiciona estado, perde vantagem do JWT)
    3. Tokens de curta duração + refresh tokens (melhor abordagem)
    """
    return {"message": "Logout realizado (delete token no cliente)"}
```

### 1.3 Comparação: Session vs JWT

```python
"""
┌─────────────────────┬──────────────────┬──────────────────┐
│ Aspecto             │ Session-Based    │ JWT              │
├─────────────────────┼──────────────────┼──────────────────┤
│ Stateful/Stateless  │ Stateful         │ Stateless        │
│ Storage             │ Redis/DB         │ Cliente          │
│ Revogação           │ Fácil (delete)   │ Difícil          │
│ Escalabilidade      │ Médio            │ Excelente        │
│ Tamanho             │ Pequeno (32B)    │ Grande (200-500B)│
│ Mobile-friendly     │ ⚠️ Cookies       │ ✅ Headers       │
│ API-friendly        │ ⚠️               │ ✅               │
│ Complexidade        │ Média            │ Baixa            │
└─────────────────────┴──────────────────┴──────────────────┘

🎯 QUANDO USAR:

Session-Based:
  ✅ Web app tradicional (server-side rendering)
  ✅ Precisa revogar sessões facilmente
  ✅ Armazena muitos dados de sessão

JWT:
  ✅ REST API para mobile/SPA (RECOMENDADO)
  ✅ Microservices (sem shared session store)
  ✅ Escalabilidade horizontal
  ✅ Tokens de curta duração
"""
```

---

## 🔄 PARTE 2: Refresh Tokens

### 2.1 Problema: Access Tokens de Longa Duração

```python
"""
❌ PROBLEMA: Se access token dura 7 dias e vaza:
  • Atacante tem acesso por 7 dias
  • Não pode revogar JWT facilmente

✅ SOLUÇÃO: Access token curto (15min) + Refresh token longo (7 dias)

Fluxo:
┌────────┐                                    ┌────────┐
│ Client │                                    │ Server │
└───┬────┘                                    └───┬────┘
    │                                             │
    │ POST /login                                 │
    ├────────────────────────────────────────────>│
    │                                             │
    │ {                                           │
    │   access_token: "...",   (expira 15min)    │
    │   refresh_token: "..."   (expira 7 dias)   │
    │ }                                           │
    │<────────────────────────────────────────────┤
    │                                             │
    │ GET /profile                                │
    │ Authorization: Bearer <access_token>        │
    ├────────────────────────────────────────────>│
    │ Profile data                                │
    │<────────────────────────────────────────────┤
    │                                             │
    │ (15 minutos depois, access_token expira)    │
    │                                             │
    │ GET /profile                                │
    │ Authorization: Bearer <access_token>        │
    ├────────────────────────────────────────────>│
    │ 401 Token expirado                          │
    │<────────────────────────────────────────────┤
    │                                             │
    │ POST /refresh                               │
    │ refresh_token: "..."                        │
    ├────────────────────────────────────────────>│
    │                                             │
    │ {                                           │
    │   access_token: "..." (novo)               │
    │   refresh_token: "..." (rotacionado)       │
    │ }                                           │
    │<────────────────────────────────────────────┤

Benefícios:
  ✅ Se access_token vazar, válido por apenas 15min
  ✅ Refresh tokens podem ser revogados (armazenar no DB)
  ✅ Melhor segurança sem afetar UX
"""
```

### 2.2 Implementação Completa

```python
# app/models/refresh_token.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func

class RefreshToken(Base):
    """
    Armazenar refresh tokens no banco.

    Permite:
    - Revogar tokens (logout de todos os dispositivos)
    - Rastrear dispositivos
    - Detectar uso suspeito
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)

    # Tracking
    device_info = Column(String(255))
    ip_address = Column(String(45))


# app/core/security.py

import secrets
from datetime import datetime, timedelta

REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_refresh_token(db: Session, user_id: int, device_info: str = None) -> str:
    """Criar refresh token."""
    # Gerar token aleatório
    token = secrets.token_urlsafe(32)

    # Armazenar no banco
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        device_info=device_info
    )

    db.add(refresh_token)
    db.commit()

    return token


def verify_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """Verificar refresh token."""
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()

    return refresh_token


def revoke_refresh_token(db: Session, token: str):
    """Revogar refresh token (logout)."""
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token
    ).first()

    if refresh_token:
        refresh_token.revoked = True
        db.commit()


def revoke_all_user_tokens(db: Session, user_id: int):
    """Revogar todos os tokens do usuário (logout de todos os dispositivos)."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id
    ).update({"revoked": True})
    db.commit()


# Endpoints

@router.post("/login")
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login com access + refresh tokens."""
    # Autenticar
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(401, "Credenciais inválidas")

    # Criar access token (curto: 15 min)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=15)
    )

    # Criar refresh token (longo: 7 dias)
    device_info = request.headers.get("User-Agent", "")
    refresh_token = create_refresh_token(
        db,
        user.id,
        device_info=device_info
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900  # 15 minutos
    }


@router.post("/refresh")
def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Renovar access token usando refresh token.

    Security: Refresh token rotation
    - Cada uso do refresh token gera um novo
    - Token antigo é revogado
    - Previne reutilização se vazou
    """
    # Verificar refresh token
    token_record = verify_refresh_token(db, refresh_token)
    if not token_record:
        raise HTTPException(401, "Refresh token inválido ou expirado")

    # Revogar token atual (rotation)
    revoke_refresh_token(db, refresh_token)

    # Criar novo access token
    access_token = create_access_token(
        data={"sub": str(token_record.user_id)},
        expires_delta=timedelta(minutes=15)
    )

    # Criar novo refresh token
    new_refresh_token = create_refresh_token(
        db,
        token_record.user_id,
        device_info=token_record.device_info
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 900
    }


@router.post("/logout")
def logout(
    refresh_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout: revogar refresh token."""
    revoke_refresh_token(db, refresh_token)
    return {"message": "Logout realizado"}


@router.post("/logout-all")
def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout de todos os dispositivos."""
    revoke_all_user_tokens(db, current_user.id)
    return {"message": "Logout de todos os dispositivos realizado"}
```

---

## 🛡️ PARTE 3: RBAC (Role-Based Access Control)

```python
# app/models/user.py

from enum import Enum

class UserRole(str, Enum):
    """Roles de usuário."""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    # ... outros campos


# app/api/deps.py

from functools import wraps
from typing import List

def require_role(allowed_roles: List[UserRole]):
    """
    Decorator para proteger endpoints por role.

    Uso:
        @router.delete("/users/{user_id}")
        @require_role([UserRole.ADMIN])
        def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
            # ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Acesso negado. Requer role: {', '.join(allowed_roles)}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


# Dependency alternativa
def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency que requer admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "Acesso negado. Requer admin.")
    return current_user


# Uso nos endpoints

@router.get("/users")
def list_users(current_user: User = Depends(get_current_user)):
    """Qualquer usuário autenticado pode listar."""
    # ...

@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user)  # Requer admin!
):
    """Apenas admin pode banir usuários."""
    # ...

@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user)
):
    """Pode deletar se for autor ou moderator/admin."""
    post = get_post(post_id)

    # Verificar permissão
    if post.user_id != current_user.id:
        if current_user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
            raise HTTPException(403, "Sem permissão para deletar este post")

    delete_post_from_db(post_id)
    return {"message": "Post deletado"}
```

---

## 🔒 PARTE 4: Password Reset Flow

```python
"""
FLUXO DE RESET DE SENHA:

1. User clica "Esqueci minha senha"
2. User envia email
3. Server gera token de reset e envia por email
4. User clica no link com token
5. User define nova senha
6. Token é invalidado

Security:
  • Token expira em 1 hora
  • Token pode ser usado apenas uma vez
  • Token armazenado com hash no banco
"""

# app/models/password_reset.py

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token_hash = Column(String(255), unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# app/core/security.py

import hashlib

def create_password_reset_token(db: Session, user_id: int) -> str:
    """Criar token de reset de senha."""
    # Gerar token aleatório
    token = secrets.token_urlsafe(32)

    # Hash do token (não armazenar plain text!)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Armazenar no banco
    reset_token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )

    db.add(reset_token)
    db.commit()

    return token  # Retornar token plain para enviar por email


def verify_password_reset_token(db: Session, token: str) -> Optional[int]:
    """Verificar token de reset."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()

    if not reset_token:
        return None

    return reset_token.user_id


# Endpoints

@router.post("/password-reset/request")
def request_password_reset(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Solicitar reset de senha."""
    user = db.query(User).filter(User.email == email).first()

    # SEMPRE retornar sucesso (não vazar se email existe)
    message = "Se o email existir, você receberá instruções de reset."

    if user:
        # Criar token
        token = create_password_reset_token(db, user.id)

        # Enviar email (em background)
        reset_url = f"https://myapp.com/reset-password?token={token}"
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            reset_url
        )

    return {"message": message}


@router.post("/password-reset/confirm")
def confirm_password_reset(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Confirmar reset de senha."""
    # Verificar token
    user_id = verify_password_reset_token(db, token)
    if not user_id:
        raise HTTPException(400, "Token inválido ou expirado")

    # Atualizar senha
    user = db.query(User).filter(User.id == user_id).first()
    user.hashed_password = pwd_context.hash(new_password)

    # Marcar token como usado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).update({"used": True})

    db.commit()

    # Revogar todos os tokens ativos (forçar re-login)
    revoke_all_user_tokens(db, user_id)

    return {"message": "Senha alterada com sucesso"}
```

---

## ⏱️ PARTE 5: Rate Limiting

```python
"""
RATE LIMITING EM LOGIN

Por quê?
  • Prevenir brute force attacks
  • Prevenir credential stuffing
  • Proteger recursos

Estratégias:
  1. Por IP: 5 tentativas por minuto
  2. Por email: 10 tentativas por hora
  3. Lockout: Bloquear após X tentativas
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
import redis

limiter = Limiter(key_func=get_remote_address)
redis_client = redis.Redis()

# Forma 1: Rate limit por IP (simples)
@router.post("/login")
@limiter.limit("5/minute")  # Max 5 tentativas por minuto
def login_with_rate_limit(
    request: Request,
    credentials: LoginRequest
):
    # ...


# Forma 2: Rate limit por email (mais robusto)
def check_login_attempts(email: str):
    """Verificar tentativas de login."""
    key = f"login_attempts:{email}"
    attempts = redis_client.get(key)

    if attempts and int(attempts) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente em 1 hora."
        )


def record_failed_login(email: str):
    """Registrar tentativa falha."""
    key = f"login_attempts:{email}"
    redis_client.incr(key)
    redis_client.expire(key, 3600)  # Expira em 1 hora


def clear_login_attempts(email: str):
    """Limpar tentativas após login bem-sucedido."""
    redis_client.delete(f"login_attempts:{email}")


@router.post("/login")
def login_with_attempt_tracking(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login com tracking de tentativas."""
    # Verificar rate limit
    check_login_attempts(credentials.email)

    # Autenticar
    user = authenticate_user(db, credentials.email, credentials.password)

    if not user:
        # Registrar falha
        record_failed_login(credentials.email)
        raise HTTPException(401, "Credenciais inválidas")

    # Limpar tentativas após sucesso
    clear_login_attempts(credentials.email)

    # Criar tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
```

---

## 🎯 Checklist de Segurança

### Autenticação
- [ ] Passwords com hash (bcrypt/argon2)
- [ ] JWT com secret key forte
- [ ] Access tokens de curta duração (15-30min)
- [ ] Refresh tokens armazenados no DB
- [ ] Refresh token rotation
- [ ] Rate limiting em login
- [ ] Password reset seguro (token de 1 uso)

### Autorização
- [ ] RBAC implementado
- [ ] Validação de permissões em cada endpoint
- [ ] Princípio de menor privilégio

### Transporte
- [ ] HTTPS obrigatório
- [ ] Cookies com httponly, secure, samesite
- [ ] Headers de segurança (HSTS, CSP)

### Monitoramento
- [ ] Log de logins e tentativas falhas
- [ ] Alertas para atividades suspeitas
- [ ] Tracking de dispositivos

---

## 📊 Comparação Final

```
┌────────────────────────┬─────────┬─────────┬──────────┐
│ Feature                │ Session │ JWT     │ OAuth2   │
├────────────────────────┼─────────┼─────────┼──────────┤
│ Stateless              │ ❌      │ ✅      │ ✅       │
│ Revogação fácil        │ ✅      │ ❌*     │ ✅       │
│ Escalabilidade         │ Médio   │ Alta    │ Alta     │
│ Mobile-friendly        │ ⚠️      │ ✅      │ ✅       │
│ Complexidade           │ Baixa   │ Média   │ Alta     │
│ Third-party auth       │ ❌      │ ❌      │ ✅       │
└────────────────────────┴─────────┴─────────┴──────────┘

* JWT + Refresh tokens permite revogação

🏆 RECOMENDAÇÃO:

API REST moderna: JWT + Refresh Tokens
Web app tradicional: Session-Based
API pública: OAuth2
```

---

## 🚀 Próximos Passos

- **[Exercício 04](../exercicio-04-posts-texto/)**: Posts de texto
- Adicionar ownership (user pode editar apenas seus posts)
- Moderadores podem deletar qualquer post

Este exercício cobre 90% dos casos de autenticação/autorização em produção! 🔐
