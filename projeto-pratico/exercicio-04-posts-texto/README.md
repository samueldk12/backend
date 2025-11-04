# Exercício 04 - Posts de Texto

> Implementação de posts de texto em uma rede social, mostrando diferentes abordagens e trade-offs.

---

## 📋 Objetivo

Implementar o sistema de posts de texto, explorando:
- Diferentes formas de modelar posts
- Visibilidade (público, privado, amigos)
- Edição e soft delete
- Paginação eficiente
- Performance e cache

---

## 🎯 O Que Vamos Aprender

1. **Modelagem de dados**: posts com relações complexas
2. **Autorização**: quem pode ver/editar posts
3. **Soft delete vs Hard delete**
4. **Paginação**: offset vs cursor-based
5. **Caching**: invalidação inteligente
6. **Performance**: N+1, eager loading

---

## 📊 Comparação de Abordagens

### 1. Modelagem de Posts

#### Abordagem A: Simples (MVP)

```python
# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationship
    author = relationship("User", back_populates="posts")
```

**Prós:**
- Simples de entender e implementar
- Rápido para MVP

**Contras:**
- Sem controle de visibilidade
- Não rastreia edições
- Difícil adicionar features depois

**Use quando:** MVP, protótipo, produto simples

---

#### Abordagem B: Com Visibilidade e Soft Delete

```python
# models.py
from enum import Enum
from sqlalchemy import Boolean

class PostVisibility(str, Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    visibility = Column(Enum(PostVisibility), default=PostVisibility.PUBLIC)

    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    author = relationship("User", back_populates="posts")

    def soft_delete(self):
        """Marca post como deletado sem remover do banco"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def can_view(self, viewer_id: Optional[int]) -> bool:
        """Verifica se usuário pode ver este post"""
        # Post deletado: ninguém vê
        if self.is_deleted:
            return False

        # Post público: todos veem
        if self.visibility == PostVisibility.PUBLIC:
            return True

        # Sem usuário logado: só vê públicos
        if not viewer_id:
            return False

        # Autor sempre vê seus posts
        if viewer_id == self.user_id:
            return True

        # Post privado: só autor vê
        if self.visibility == PostVisibility.PRIVATE:
            return False

        # Post de amigos: verifica amizade
        if self.visibility == PostVisibility.FRIENDS:
            # Implementar lógica de amizade
            return self.author.is_friend_of(viewer_id)

        return False
```

**Prós:**
- Controle granular de visibilidade
- Soft delete permite recuperação
- Lógica de autorização no modelo

**Contras:**
- Mais complexo
- Query precisa filtrar `is_deleted`
- Lógica de amizade acoplada

**Use quando:** Produto médio, precisa controle de privacidade

---

#### Abordagem C: Com Histórico de Edições

```python
# models.py
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    visibility = Column(Enum(PostVisibility), default=PostVisibility.PUBLIC)
    is_deleted = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Rastreamento de edições
    edited = Column(Boolean, default=False)
    edit_count = Column(Integer, default=0)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    author = relationship("User", back_populates="posts")
    edit_history = relationship("PostEdit", back_populates="post", order_by="PostEdit.edited_at.desc()")


class PostEdit(Base):
    """Armazena histórico de edições do post"""
    __tablename__ = "post_edits"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    # Conteúdo anterior
    previous_content = Column(Text, nullable=False)

    # Quando foi editado
    edited_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    post = relationship("Post", back_populates="edit_history")
```

**Prós:**
- Auditoria completa
- Pode mostrar "editado" para usuários
- Pode desfazer edições

**Contras:**
- Mais espaço em disco
- Queries mais complexas
- Pode crescer muito (considerar limite)

**Use quando:** Transparência é crítica (ex: Twitter, Reddit), compliance

---

## 🔧 Implementações

### 1. Criar Post (Abordagem Repository)

```python
# repositories/post_repository.py
from sqlalchemy.orm import Session
from typing import Optional
from models import Post, PostVisibility

class PostRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        content: str,
        user_id: int,
        visibility: PostVisibility = PostVisibility.PUBLIC
    ) -> Post:
        """Cria um novo post"""
        post = Post(
            content=content,
            user_id=user_id,
            visibility=visibility
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    def get_by_id(self, post_id: int, include_deleted: bool = False) -> Optional[Post]:
        """Busca post por ID"""
        query = self.db.query(Post).filter(Post.id == post_id)

        if not include_deleted:
            query = query.filter(Post.is_deleted == False)

        return query.first()

    def get_user_posts(
        self,
        user_id: int,
        viewer_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20
    ):
        """Busca posts de um usuário com autorização"""
        query = self.db.query(Post).filter(
            Post.user_id == user_id,
            Post.is_deleted == False
        )

        # Se viewer não é o autor, filtrar por visibilidade
        if viewer_id != user_id:
            if viewer_id:
                # Usuário logado: vê públicos e de amigos
                query = query.filter(
                    Post.visibility.in_([PostVisibility.PUBLIC, PostVisibility.FRIENDS])
                )
            else:
                # Não logado: só públicos
                query = query.filter(Post.visibility == PostVisibility.PUBLIC)

        return query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()

    def update(self, post: Post, new_content: str) -> Post:
        """Atualiza conteúdo do post (com histórico)"""
        # Salvar conteúdo anterior
        from models import PostEdit
        edit = PostEdit(
            post_id=post.id,
            previous_content=post.content
        )
        self.db.add(edit)

        # Atualizar post
        post.content = new_content
        post.edited = True
        post.edit_count += 1

        self.db.commit()
        self.db.refresh(post)
        return post

    def soft_delete(self, post: Post) -> Post:
        """Marca post como deletado"""
        post.soft_delete()
        self.db.commit()
        return post


# schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

class PostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    visibility: PostVisibility = PostVisibility.PUBLIC

    @validator("content")
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace")
        return v.strip()


class PostUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class PostResponse(BaseModel):
    id: int
    content: str
    visibility: PostVisibility
    created_at: datetime
    updated_at: Optional[datetime]
    edited: bool
    edit_count: int

    # Author info
    author_id: int
    author_name: str

    class Config:
        from_attributes = True


# routes/posts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria um novo post"""
    repo = PostRepository(db)
    post = repo.create(
        content=post_data.content,
        user_id=current_user.id,
        visibility=post_data.visibility
    )

    return PostResponse(
        id=post.id,
        content=post.content,
        visibility=post.visibility,
        created_at=post.created_at,
        updated_at=post.updated_at,
        edited=post.edited,
        edit_count=post.edit_count,
        author_id=post.user_id,
        author_name=post.author.name
    )


@router.get("/user/{user_id}", response_model=List[PostResponse])
def get_user_posts(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Lista posts de um usuário (respeitando visibilidade)"""
    repo = PostRepository(db)

    viewer_id = current_user.id if current_user else None
    posts = repo.get_user_posts(user_id, viewer_id, skip, limit)

    return [
        PostResponse(
            id=post.id,
            content=post.content,
            visibility=post.visibility,
            created_at=post.created_at,
            updated_at=post.updated_at,
            edited=post.edited,
            edit_count=post.edit_count,
            author_id=post.user_id,
            author_name=post.author.name
        )
        for post in posts
    ]


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza um post (só o autor pode)"""
    repo = PostRepository(db)
    post = repo.get_by_id(post_id)

    if not post:
        raise HTTPException(404, "Post not found")

    # Verificar autorização
    if post.user_id != current_user.id:
        raise HTTPException(403, "You can only edit your own posts")

    # Atualizar
    updated_post = repo.update(post, post_data.content)

    return PostResponse(
        id=updated_post.id,
        content=updated_post.content,
        visibility=updated_post.visibility,
        created_at=updated_post.created_at,
        updated_at=updated_post.updated_at,
        edited=updated_post.edited,
        edit_count=updated_post.edit_count,
        author_id=updated_post.user_id,
        author_name=updated_post.author.name
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deleta um post (soft delete)"""
    repo = PostRepository(db)
    post = repo.get_by_id(post_id)

    if not post:
        raise HTTPException(404, "Post not found")

    # Verificar autorização
    if post.user_id != current_user.id:
        raise HTTPException(403, "You can only delete your own posts")

    repo.soft_delete(post)
    return None


@router.get("/{post_id}/history", response_model=List[dict])
def get_post_history(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna histórico de edições (só autor vê)"""
    repo = PostRepository(db)
    post = repo.get_by_id(post_id)

    if not post:
        raise HTTPException(404, "Post not found")

    if post.user_id != current_user.id:
        raise HTTPException(403, "You can only see your own edit history")

    return [
        {
            "edited_at": edit.edited_at,
            "previous_content": edit.previous_content
        }
        for edit in post.edit_history
    ]
```

---

### 2. Paginação: Offset vs Cursor-Based

#### Offset (Tradicional)

```python
@router.get("/feed")
def get_feed_offset(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Feed com paginação offset"""
    skip = (page - 1) * per_page

    posts = db.query(Post).filter(
        Post.is_deleted == False,
        Post.visibility == PostVisibility.PUBLIC
    ).order_by(Post.created_at.desc()).offset(skip).limit(per_page).all()

    return {"posts": posts, "page": page, "per_page": per_page}
```

**Problemas:**
1. **Inconsistência**: Se posts forem adicionados entre páginas, usuário pode ver duplicados
2. **Performance**: `OFFSET 10000` força DB a escanear e descartar 10000 linhas
3. **Difícil deep linking**: URL `?page=5` não garante mesmo conteúdo depois

---

#### Cursor-Based (Recomendado)

```python
from typing import Optional

@router.get("/feed")
def get_feed_cursor(
    cursor: Optional[int] = None,  # ID do último post visto
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Feed com paginação cursor-based (melhor performance)"""
    query = db.query(Post).filter(
        Post.is_deleted == False,
        Post.visibility == PostVisibility.PUBLIC
    )

    # Se tem cursor, buscar posts mais antigos que ele
    if cursor:
        query = query.filter(Post.id < cursor)

    posts = query.order_by(Post.id.desc()).limit(limit).all()

    # Próximo cursor
    next_cursor = posts[-1].id if posts else None

    return {
        "posts": posts,
        "next_cursor": next_cursor,
        "has_more": len(posts) == limit
    }
```

**Vantagens:**
- ✅ Sem duplicados entre páginas
- ✅ Performance constante (usa índice)
- ✅ Funciona bem com feeds em tempo real

**Use quando:** Feeds infinitos, performance crítica

---

### 3. Performance: Evitando N+1

#### ❌ Problema N+1

```python
@router.get("/feed")
def get_feed_bad(db: Session = Depends(get_db)):
    """N+1 problem: 1 query para posts + N queries para autores"""
    posts = db.query(Post).limit(20).all()

    # Cada iteração faz UMA query!
    for post in posts:
        print(post.author.name)  # N+1 queries!

    return posts
```

**Queries executadas:**
```sql
-- Query 1: Buscar posts
SELECT * FROM posts LIMIT 20;

-- Query 2-21: Para cada post, buscar autor (N+1!)
SELECT * FROM users WHERE id = 1;
SELECT * FROM users WHERE id = 2;
...
SELECT * FROM users WHERE id = 20;
```

---

#### ✅ Solução: Eager Loading

```python
from sqlalchemy.orm import joinedload

@router.get("/feed")
def get_feed_optimized(db: Session = Depends(get_db)):
    """Solução: eager loading com joinedload"""
    posts = db.query(Post).options(
        joinedload(Post.author)  # JOIN em uma única query
    ).limit(20).all()

    # Nenhuma query adicional!
    for post in posts:
        print(post.author.name)  # Dados já carregados

    return posts
```

**Query executada:**
```sql
-- UMA query com JOIN
SELECT posts.*, users.*
FROM posts
JOIN users ON posts.user_id = users.id
LIMIT 20;
```

**Performance:**
- Offset: 21 queries → 1 query = **21x mais rápido**
- Reduz latência drasticamente

---

### 4. Caching de Posts

```python
from functools import lru_cache
from redis import Redis
import json

redis_client = Redis(host="localhost", port=6379, decode_responses=True)

class PostService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PostRepository(db)

    def get_post_with_cache(self, post_id: int) -> Optional[dict]:
        """Busca post com cache (Cache-Aside)"""
        cache_key = f"post:{post_id}"

        # Tentar cache primeiro
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        # Cache miss: buscar do DB
        post = self.repo.get_by_id(post_id)
        if not post:
            return None

        # Serializar e cachear
        post_dict = {
            "id": post.id,
            "content": post.content,
            "author_id": post.user_id,
            "author_name": post.author.name,
            "created_at": post.created_at.isoformat()
        }

        # Cache por 5 minutos
        redis_client.setex(cache_key, 300, json.dumps(post_dict))

        return post_dict

    def update_post_and_invalidate_cache(self, post_id: int, content: str):
        """Atualiza post e invalida cache"""
        post = self.repo.get_by_id(post_id)
        updated = self.repo.update(post, content)

        # Invalidar cache
        redis_client.delete(f"post:{post_id}")

        return updated


# Uso
@router.get("/{post_id}")
def get_post_cached(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Endpoint com cache"""
    service = PostService(db)
    post = service.get_post_with_cache(post_id)

    if not post:
        raise HTTPException(404, "Post not found")

    return post
```

**Estratégia:**
- **Cache-Aside**: App gerencia cache manualmente
- **TTL**: 5 minutos para balancear freshness e performance
- **Invalidação**: Deletar cache quando post é editado/deletado

---

## 🚀 Migration

```python
# alembic/versions/xxx_create_posts.py
def upgrade():
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('visibility', sa.Enum('public', 'friends', 'private', name='postvisibility'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('edited', sa.Boolean(), default=False),
        sa.Column('edit_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Índices importantes
    op.create_index('ix_posts_user_id', 'posts', ['user_id'])
    op.create_index('ix_posts_created_at', 'posts', ['created_at'])
    op.create_index('ix_posts_is_deleted', 'posts', ['is_deleted'])

    # Índice composto para queries comuns
    op.create_index(
        'ix_posts_user_visibility_deleted',
        'posts',
        ['user_id', 'visibility', 'is_deleted']
    )

    # Tabela de histórico de edições
    op.create_table(
        'post_edits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('previous_content', sa.Text(), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_post_edits_post_id', 'post_edits', ['post_id'])
```

---

## 🧪 Testes

```python
# tests/test_posts.py
import pytest
from fastapi.testclient import TestClient

def test_create_post(client: TestClient, auth_headers: dict):
    """Testa criação de post"""
    response = client.post(
        "/posts/",
        json={"content": "Meu primeiro post!", "visibility": "public"},
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Meu primeiro post!"
    assert data["visibility"] == "public"
    assert data["edited"] == False


def test_create_post_empty_content(client: TestClient, auth_headers: dict):
    """Testa validação de conteúdo vazio"""
    response = client.post(
        "/posts/",
        json={"content": "   "},  # Só whitespace
        headers=auth_headers
    )

    assert response.status_code == 422


def test_update_post(client: TestClient, auth_headers: dict, sample_post: dict):
    """Testa edição de post"""
    response = client.put(
        f"/posts/{sample_post['id']}",
        json={"content": "Post editado"},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Post editado"
    assert data["edited"] == True
    assert data["edit_count"] == 1


def test_update_post_unauthorized(client: TestClient, other_user_headers: dict, sample_post: dict):
    """Testa que usuário não pode editar post de outro"""
    response = client.put(
        f"/posts/{sample_post['id']}",
        json={"content": "Tentando hackear"},
        headers=other_user_headers
    )

    assert response.status_code == 403


def test_soft_delete_post(client: TestClient, auth_headers: dict, sample_post: dict):
    """Testa soft delete"""
    # Deletar
    response = client.delete(f"/posts/{sample_post['id']}", headers=auth_headers)
    assert response.status_code == 204

    # Tentar buscar: não deve aparecer
    response = client.get(f"/posts/{sample_post['id']}")
    assert response.status_code == 404


def test_post_visibility(client: TestClient, auth_headers: dict, other_user_headers: dict):
    """Testa controle de visibilidade"""
    # Criar post privado
    response = client.post(
        "/posts/",
        json={"content": "Post privado", "visibility": "private"},
        headers=auth_headers
    )
    post_id = response.json()["id"]

    # Autor consegue ver
    response = client.get(f"/posts/{post_id}", headers=auth_headers)
    assert response.status_code == 200

    # Outro usuário não consegue
    response = client.get(f"/posts/{post_id}", headers=other_user_headers)
    assert response.status_code == 404


def test_pagination_cursor(client: TestClient, auth_headers: dict):
    """Testa paginação cursor-based"""
    # Criar 30 posts
    for i in range(30):
        client.post(
            "/posts/",
            json={"content": f"Post {i}"},
            headers=auth_headers
        )

    # Primeira página
    response = client.get("/posts/feed?limit=10")
    data = response.json()

    assert len(data["posts"]) == 10
    assert data["has_more"] == True
    assert data["next_cursor"] is not None

    # Segunda página
    response = client.get(f"/posts/feed?limit=10&cursor={data['next_cursor']}")
    data2 = response.json()

    assert len(data2["posts"]) == 10
    # Posts não devem se repetir
    post_ids_1 = [p["id"] for p in data["posts"]]
    post_ids_2 = [p["id"] for p in data2["posts"]]
    assert len(set(post_ids_1) & set(post_ids_2)) == 0
```

---

## 📊 Comparação Final

| Aspecto | Abordagem Simples | Abordagem Completa |
|---------|-------------------|-------------------|
| **Linhas de código** | ~100 | ~400 |
| **Features** | CRUD básico | Visibilidade, soft delete, histórico, cache |
| **Performance** | N+1 problem | Eager loading, cache |
| **Escalabilidade** | Limitada | Preparada para crescer |
| **Manutenção** | Fácil inicialmente | Mais código, mas organizado |
| **Tempo desenvolvimento** | 2-3 horas | 1-2 dias |
| **Adequado para** | MVP, protótipo | Produto real |

---

## 🎯 Decisão: Qual Usar?

### Use Abordagem Simples quando:
- ✅ MVP ou protótipo
- ✅ Time pequeno (1-2 devs)
- ✅ Poucos usuários (<1000)
- ✅ Features podem evoluir depois

### Use Abordagem Completa quando:
- ✅ Produto que vai crescer
- ✅ Privacidade é importante
- ✅ Precisa auditoria
- ✅ Time médio/grande (3+ devs)
- ✅ Muitos usuários (>10k)

---

## 🎓 Conceitos Aprendidos

1. ✅ **Soft delete**: Preservar dados sem remover
2. ✅ **Visibilidade**: Controle granular de acesso
3. ✅ **Paginação cursor**: Performance constante
4. ✅ **N+1 problem**: Eager loading com `joinedload`
5. ✅ **Cache invalidation**: Deletar cache ao atualizar
6. ✅ **Repository pattern**: Separar lógica de acesso
7. ✅ **Histórico de edições**: Auditoria e transparência

---

## 📚 Próximos Passos

- **Exercício 05**: Posts de vídeo (upload, encoding, streaming)
- **Exercício 06**: Likes e comentários
- **Exercício 07**: Timeline e feed personalizado
- **Exercício 08**: Notificações em tempo real

---

**Agora você sabe criar um sistema completo de posts! 🎉**
