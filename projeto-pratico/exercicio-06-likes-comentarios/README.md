# Exercício 06 - Likes e Comentários

> Sistema de engajamento para rede social: likes, comentários aninhados, contadores, e otimizações.

---

## 📋 Objetivo

Implementar sistema completo de engajamento, explorando:
- Likes com proteção contra duplicatas
- Comentários aninhados (threads)
- Contadores denormalizados para performance
- Race conditions e como evitar
- Paginação eficiente de comentários
- Ordenação (recent, top, controversial)

---

## 🎯 O Que Vamos Aprender

1. **Unique constraints**: prevenir likes duplicados
2. **Denormalization**: contadores em cache
3. **Race conditions**: incrementos atômicos
4. **Tree structures**: comentários aninhados
5. **Hot paths**: otimizar queries mais frequentes
6. **Real-time updates**: invalidar cache

---

## 📊 Modelagem de Dados

### Abordagem A: Simples (MVP)

```python
# models.py
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from datetime import datetime

class Like(Base):
    """Like em um post (1 por usuário)"""
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # CRÍTICO: Prevenir duplicatas
    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='uq_post_user_like'),
    )


class Comment(Base):
    """Comentário em um post"""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="comments")
    author = relationship("User")
```

**Prós:**
- Simples de implementar
- Unique constraint garante 1 like por user

**Contras:**
- ❌ Contar likes requer COUNT(*) - lento para milhões de likes
- ❌ Sem comentários aninhados (replies)

---

### Abordagem B: Com Contadores Denormalizados

```python
# models.py
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Contadores denormalizados (performance!)
    likes_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    likes = relationship("Like", back_populates="post")
    comments = relationship("Comment", back_populates="post")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='uq_post_user_like'),
    )

    # Relationships
    post = relationship("Post", back_populates="likes")
    user = relationship("User")
```

**Vantagens:**
- ✅ Buscar likes_count é O(1) - não precisa COUNT(*)
- ✅ Feed pode ordenar por popularidade sem JOINs

**Desafios:**
- ⚠️  Precisa manter contador sincronizado
- ⚠️  Race conditions (2 likes simultâneos)

---

### Abordagem C: Comentários Aninhados (Threads)

```python
# models.py
class Comment(Base):
    """Comentário com suporte a replies (threads)"""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)

    # Nested comments (self-referential)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)

    # Denormalized counters
    replies_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="comments")
    author = relationship("User")
    parent = relationship("Comment", remote_side=[id], backref="replies")


class CommentLike(Base):
    """Likes em comentários (separado de likes em posts)"""
    __tablename__ = "comment_likes"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('comment_id', 'user_id', name='uq_comment_user_like'),
    )
```

**Estrutura de thread:**
```
Comment 1 (parent_id = NULL)
  ├─ Comment 2 (parent_id = 1)
  │    └─ Comment 3 (parent_id = 2)
  └─ Comment 4 (parent_id = 1)
```

---

## 🔧 Implementações

### 1. Dar Like (com Race Condition Protection)

```python
# services/like_service.py
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

class LikeService:
    def __init__(self, db: Session):
        self.db = db

    def like_post(self, post_id: int, user_id: int) -> dict:
        """
        Dar like em post

        Desafios:
        1. Prevenir duplicatas (unique constraint)
        2. Incrementar contador atomicamente (evitar race condition)
        """
        try:
            # Criar like
            like = Like(post_id=post_id, user_id=user_id)
            self.db.add(like)

            # Incrementar contador ATOMICAMENTE
            # ❌ ERRADO (race condition):
            # post.likes_count += 1

            # ✅ CORRETO (atômico):
            self.db.execute(
                update(Post)
                .where(Post.id == post_id)
                .values(likes_count=Post.likes_count + 1)
            )

            self.db.commit()

            # Buscar post atualizado
            post = self.db.query(Post).filter(Post.id == post_id).first()

            return {
                "liked": True,
                "likes_count": post.likes_count
            }

        except IntegrityError:
            # Duplicata: usuário já deu like
            self.db.rollback()
            raise HTTPException(400, "You already liked this post")


    def unlike_post(self, post_id: int, user_id: int) -> dict:
        """Remover like"""
        like = self.db.query(Like).filter(
            Like.post_id == post_id,
            Like.user_id == user_id
        ).first()

        if not like:
            raise HTTPException(404, "Like not found")

        self.db.delete(like)

        # Decrementar atomicamente
        self.db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(likes_count=Post.likes_count - 1)
        )

        self.db.commit()

        post = self.db.query(Post).filter(Post.id == post_id).first()

        return {
            "liked": False,
            "likes_count": post.likes_count
        }


    def toggle_like(self, post_id: int, user_id: int) -> dict:
        """Toggle: se tem like, remove; se não tem, adiciona"""
        like = self.db.query(Like).filter(
            Like.post_id == post_id,
            Like.user_id == user_id
        ).first()

        if like:
            return self.unlike_post(post_id, user_id)
        else:
            return self.like_post(post_id, user_id)


    def get_post_likers(self, post_id: int, limit: int = 50) -> list:
        """Buscar usuários que deram like"""
        likes = self.db.query(Like).options(
            joinedload(Like.user)  # Eager loading
        ).filter(
            Like.post_id == post_id
        ).order_by(
            Like.created_at.desc()
        ).limit(limit).all()

        return [
            {
                "user_id": like.user.id,
                "username": like.user.username,
                "liked_at": like.created_at
            }
            for like in likes
        ]
```

---

### 2. Comentários (com Paginação e Threads)

```python
# services/comment_service.py
class CommentService:
    def __init__(self, db: Session):
        self.db = db

    def create_comment(
        self,
        post_id: int,
        user_id: int,
        content: str,
        parent_id: Optional[int] = None
    ) -> Comment:
        """
        Criar comentário ou reply

        Se parent_id = None: comentário top-level
        Se parent_id != None: reply a outro comentário
        """
        # Validar post existe
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(404, "Post not found")

        # Se é reply, validar parent existe
        if parent_id:
            parent = self.db.query(Comment).filter(Comment.id == parent_id).first()
            if not parent:
                raise HTTPException(404, "Parent comment not found")

            # Validar parent pertence ao mesmo post
            if parent.post_id != post_id:
                raise HTTPException(400, "Parent comment is from different post")

        # Criar comentário
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id
        )
        self.db.add(comment)

        # Incrementar contadores atomicamente
        if parent_id:
            # Reply: incrementar replies_count do parent
            self.db.execute(
                update(Comment)
                .where(Comment.id == parent_id)
                .values(replies_count=Comment.replies_count + 1)
            )
        else:
            # Top-level: incrementar comments_count do post
            self.db.execute(
                update(Post)
                .where(Post.id == post_id)
                .values(comments_count=Post.comments_count + 1)
            )

        self.db.commit()
        self.db.refresh(comment)

        return comment


    def get_comments(
        self,
        post_id: int,
        sort_by: str = "recent",  # recent, top, old
        limit: int = 20,
        offset: int = 0
    ) -> list:
        """
        Buscar comentários top-level de um post

        Sort options:
        - recent: mais recentes primeiro
        - top: mais likes primeiro
        - old: mais antigos primeiro
        """
        query = self.db.query(Comment).options(
            joinedload(Comment.author)
        ).filter(
            Comment.post_id == post_id,
            Comment.parent_id == None  # Apenas top-level
        )

        # Ordenação
        if sort_by == "recent":
            query = query.order_by(Comment.created_at.desc())
        elif sort_by == "top":
            query = query.order_by(Comment.likes_count.desc(), Comment.created_at.desc())
        elif sort_by == "old":
            query = query.order_by(Comment.created_at.asc())

        comments = query.offset(offset).limit(limit).all()

        return [self._serialize_comment(c) for c in comments]


    def get_comment_replies(
        self,
        comment_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> list:
        """Buscar replies de um comentário"""
        replies = self.db.query(Comment).options(
            joinedload(Comment.author)
        ).filter(
            Comment.parent_id == comment_id
        ).order_by(
            Comment.created_at.asc()  # Replies em ordem cronológica
        ).offset(offset).limit(limit).all()

        return [self._serialize_comment(r) for r in replies]


    def _serialize_comment(self, comment: Comment) -> dict:
        """Serializar comentário"""
        return {
            "id": comment.id,
            "content": comment.content,
            "author": {
                "id": comment.author.id,
                "username": comment.author.username
            },
            "likes_count": comment.likes_count,
            "replies_count": comment.replies_count,
            "created_at": comment.created_at,
            "parent_id": comment.parent_id
        }


    def delete_comment(self, comment_id: int, user_id: int) -> None:
        """
        Deletar comentário

        Opções:
        1. Hard delete: remover do DB (perde thread structure)
        2. Soft delete: marcar como [deleted] (mantém structure)
        """
        comment = self.db.query(Comment).filter(Comment.id == comment_id).first()

        if not comment:
            raise HTTPException(404, "Comment not found")

        if comment.user_id != user_id:
            raise HTTPException(403, "Can only delete your own comments")

        # Se tem replies, soft delete (manter structure)
        if comment.replies_count > 0:
            comment.content = "[deleted]"
            comment.updated_at = datetime.utcnow()
        else:
            # Sem replies: hard delete
            self.db.delete(comment)

            # Decrementar contador
            if comment.parent_id:
                self.db.execute(
                    update(Comment)
                    .where(Comment.id == comment.parent_id)
                    .values(replies_count=Comment.replies_count - 1)
                )
            else:
                self.db.execute(
                    update(Post)
                    .where(Post.id == comment.post_id)
                    .values(comments_count=Post.comments_count - 1)
                )

        self.db.commit()
```

---

### 3. Endpoints FastAPI

```python
# routes/engagement.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/posts", tags=["engagement"])


# ============================================================================
# LIKES
# ============================================================================

@router.post("/{post_id}/like")
def like_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dar like em post"""
    service = LikeService(db)
    return service.like_post(post_id, current_user.id)


@router.delete("/{post_id}/like")
def unlike_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remover like"""
    service = LikeService(db)
    return service.unlike_post(post_id, current_user.id)


@router.post("/{post_id}/like/toggle")
def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle like (idempotente)"""
    service = LikeService(db)
    return service.toggle_like(post_id, current_user.id)


@router.get("/{post_id}/likes")
def get_likers(
    post_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Buscar usuários que deram like"""
    service = LikeService(db)
    return service.get_post_likers(post_id, limit)


# ============================================================================
# COMENTÁRIOS
# ============================================================================

@router.post("/{post_id}/comments")
def create_comment(
    post_id: int,
    content: str,
    parent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Criar comentário ou reply"""
    service = CommentService(db)
    comment = service.create_comment(post_id, current_user.id, content, parent_id)

    return {
        "id": comment.id,
        "content": comment.content,
        "parent_id": comment.parent_id,
        "created_at": comment.created_at
    }


@router.get("/{post_id}/comments")
def get_comments(
    post_id: int,
    sort_by: str = "recent",  # recent, top, old
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Buscar comentários (top-level apenas)"""
    service = CommentService(db)
    comments = service.get_comments(post_id, sort_by, limit, offset)

    return {
        "comments": comments,
        "count": len(comments),
        "offset": offset,
        "limit": limit
    }


@router.get("/comments/{comment_id}/replies")
def get_comment_replies(
    comment_id: int,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Buscar replies de um comentário"""
    service = CommentService(db)
    replies = service.get_comment_replies(comment_id, limit, offset)

    return {
        "replies": replies,
        "count": len(replies)
    }


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletar comentário"""
    service = CommentService(db)
    service.delete_comment(comment_id, current_user.id)

    return {"message": "Comment deleted"}
```

---

## ⚡ Otimizações Avançadas

### 1. Cache de Contadores em Redis

```python
# services/like_service.py
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

class OptimizedLikeService:
    """Like service com cache Redis"""

    def like_post(self, post_id: int, user_id: int) -> dict:
        """Like com cache"""
        # Adicionar like no DB
        like = Like(post_id=post_id, user_id=user_id)
        self.db.add(like)

        # Incrementar contador no DB
        self.db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(likes_count=Post.likes_count + 1)
        )

        self.db.commit()

        # Invalidar cache
        cache_key = f"post:{post_id}:likes_count"
        redis_client.delete(cache_key)

        # Ou incrementar cache
        redis_client.incr(cache_key)

        post = self.db.query(Post).filter(Post.id == post_id).first()
        return {"liked": True, "likes_count": post.likes_count}


    def get_likes_count(self, post_id: int) -> int:
        """Buscar contador com cache"""
        cache_key = f"post:{post_id}:likes_count"

        # Tentar cache
        cached = redis_client.get(cache_key)
        if cached:
            return int(cached)

        # Cache miss: buscar DB
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return 0

        # Cachear por 1 hora
        redis_client.setex(cache_key, 3600, post.likes_count)

        return post.likes_count
```

---

### 2. Batch Loading (Evitar N+1)

```python
# services/comment_service.py
def get_comments_with_batch_loading(
    self,
    post_id: int,
    current_user_id: Optional[int] = None
) -> list:
    """
    Buscar comentários com batch loading

    Evita N+1:
    - 1 query para comentários
    - 1 query para autores (JOIN)
    - 1 query para verificar se user deu like (IN)
    """
    # Query principal
    comments = self.db.query(Comment).options(
        joinedload(Comment.author)  # JOIN para autores
    ).filter(
        Comment.post_id == post_id,
        Comment.parent_id == None
    ).order_by(Comment.created_at.desc()).all()

    if not comments:
        return []

    # Se usuário logado, verificar quais comentários ele curtiu
    user_likes = set()
    if current_user_id:
        comment_ids = [c.id for c in comments]

        # 1 query para buscar todos os likes do usuário
        likes = self.db.query(CommentLike.comment_id).filter(
            CommentLike.comment_id.in_(comment_ids),
            CommentLike.user_id == current_user_id
        ).all()

        user_likes = {like.comment_id for like in likes}

    # Serializar
    return [
        {
            **self._serialize_comment(comment),
            "liked_by_me": comment.id in user_likes
        }
        for comment in comments
    ]
```

---

## 🧪 Testes

```python
# tests/test_engagement.py
import pytest

def test_like_post(client, auth_headers, sample_post):
    """Testa dar like"""
    response = client.post(
        f"/posts/{sample_post['id']}/like",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["liked"] == True
    assert data["likes_count"] == 1


def test_like_post_twice_fails(client, auth_headers, sample_post):
    """Testa que não pode dar like 2x"""
    # Primeiro like
    client.post(f"/posts/{sample_post['id']}/like", headers=auth_headers)

    # Segundo like (deve falhar)
    response = client.post(
        f"/posts/{sample_post['id']}/like",
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "already liked" in response.json()["detail"].lower()


def test_toggle_like(client, auth_headers, sample_post):
    """Testa toggle like (idempotente)"""
    # Toggle 1: dar like
    response = client.post(
        f"/posts/{sample_post['id']}/like/toggle",
        headers=auth_headers
    )
    assert response.json()["liked"] == True

    # Toggle 2: remover like
    response = client.post(
        f"/posts/{sample_post['id']}/like/toggle",
        headers=auth_headers
    )
    assert response.json()["liked"] == False


def test_create_comment(client, auth_headers, sample_post):
    """Testa criar comentário"""
    response = client.post(
        f"/posts/{sample_post['id']}/comments",
        json={"content": "Great post!"},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Great post!"
    assert data["parent_id"] is None


def test_reply_to_comment(client, auth_headers, sample_post, sample_comment):
    """Testa reply a comentário"""
    response = client.post(
        f"/posts/{sample_post['id']}/comments",
        json={"content": "Thanks!", "parent_id": sample_comment["id"]},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["parent_id"] == sample_comment["id"]


def test_get_comments_sorted_by_top(client, sample_post):
    """Testa buscar comentários ordenados por likes"""
    # Criar 3 comentários com diferentes números de likes
    # ... (criar comentários e likes)

    response = client.get(f"/posts/{sample_post['id']}/comments?sort_by=top")

    data = response.json()
    comments = data["comments"]

    # Verificar ordenação (mais likes primeiro)
    assert comments[0]["likes_count"] >= comments[1]["likes_count"]
```

---

## 📊 Comparação de Abordagens

| Aspecto | Contador em Query | Contador Denormalizado |
|---------|-------------------|------------------------|
| **Leitura** | O(n) - COUNT(*) | O(1) - campo no DB |
| **Escrita** | Rápida | Precisa atualizar contador |
| **Consistência** | Sempre correta | Pode dessincronizar |
| **Escalabilidade** | ❌ Lenta para milhões | ✅ Rápida |
| **Complexidade** | Simples | Média |

**Decisão:** Use contador denormalizado para performance

---

## 🎯 Conceitos Aprendidos

1. ✅ **Unique constraints**: prevenir duplicatas
2. ✅ **Incremento atômico**: `UPDATE ... SET count = count + 1`
3. ✅ **Denormalization**: trade-off consistência vs performance
4. ✅ **Self-referential FK**: comentários aninhados
5. ✅ **Soft delete**: manter structure de threads
6. ✅ **Batch loading**: evitar N+1 em has_liked checks
7. ✅ **Cache invalidation**: deletar cache ao mudar dados

---

## 📚 Próximos Passos

- **Exercício 07**: Timeline/feed personalizado
- **Exercício 08**: Notificações em tempo real
- **Exercício 09**: Search e recomendações

---

**Agora sua rede social tem engajamento! 👍💬**
