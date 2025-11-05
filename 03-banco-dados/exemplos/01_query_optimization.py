"""
Exemplo 01: Otimização de Queries e o Problema N+1

Demonstra:
1. O famoso problema N+1 queries
2. Eager loading vs Lazy loading
3. Impacto de indexes
4. Otimização de pagination

Este é um dos problemas mais comuns em performance de aplicações!
"""

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload, selectinload
from sqlalchemy.sql import func
import time
from contextlib import contextmanager
from typing import List

# ============================================================================
# SETUP DO BANCO
# ============================================================================

Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)

    # Relacionamento
    posts = relationship("Post", back_populates="author", lazy="select")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name})>"


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    views = Column(Integer, default=0)

    # Relacionamento
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", lazy="select")

    # Index para busca por user_id (será demonstrado o impacto)
    __table_args__ = (
        Index('idx_posts_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<Post(id={self.id}, title={self.title})>"


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)

    # Relacionamentos
    post = relationship("Post", back_populates="comments")
    author = relationship("User")

    __table_args__ = (
        Index('idx_comments_post_id', 'post_id'),
        Index('idx_comments_user_id', 'user_id'),
    )


# ============================================================================
# UTILITÁRIOS
# ============================================================================

# Contador de queries
query_count = 0
query_log = []

def reset_query_counter():
    """Reseta contador de queries."""
    global query_count, query_log
    query_count = 0
    query_log = []

@contextmanager
def track_queries(engine):
    """Context manager para contar queries executadas."""
    global query_count, query_log

    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        global query_count, query_log
        query_count += 1
        # Simplificar query para logging
        query_preview = statement[:100].replace('\n', ' ')
        query_log.append(f"Query {query_count}: {query_preview}...")

    # Registrar listener
    from sqlalchemy import event
    event.listen(engine, "before_cursor_execute", receive_before_cursor_execute)

    reset_query_counter()
    start = time.time()

    try:
        yield
    finally:
        elapsed = time.time() - start
        event.remove(engine, "before_cursor_execute", receive_before_cursor_execute)
        print(f"  ⏱️  Tempo: {elapsed*1000:.2f}ms")
        print(f"  📊 Queries executadas: {query_count}")


# ============================================================================
# CRIAR DADOS DE TESTE
# ============================================================================

def setup_database():
    """Cria banco de dados em memória e popula com dados de teste."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Criar usuários
    users = [
        User(name=f"Usuário {i}", email=f"user{i}@example.com")
        for i in range(1, 11)  # 10 usuários
    ]
    session.add_all(users)
    session.flush()

    # Criar posts (100 posts, ~10 por usuário)
    posts = []
    for i in range(1, 101):
        user_id = ((i - 1) % 10) + 1
        post = Post(
            user_id=user_id,
            title=f"Post {i}",
            content=f"Conteúdo do post {i}" * 10,  # Conteúdo maior
            views=i * 10
        )
        posts.append(post)
    session.add_all(posts)
    session.flush()

    # Criar comentários (300 comentários, ~3 por post)
    comments = []
    for i in range(1, 301):
        post_id = ((i - 1) % 100) + 1
        user_id = ((i - 1) % 10) + 1
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            text=f"Comentário {i}"
        )
        comments.append(comment)
    session.add_all(comments)

    session.commit()
    return engine, Session


# ============================================================================
# PROBLEMA N+1
# ============================================================================

def demonstrar_problema_n_plus_1(engine, Session):
    """
    O FAMOSO PROBLEMA N+1!

    Cenário: Listar posts com nome do autor
    """
    print("\n" + "=" * 70)
    print("PROBLEMA N+1 QUERIES")
    print("=" * 70)

    print("\n❌ FORMA ERRADA (N+1):")
    print("Listar 10 posts com nome do autor...")

    session = Session()

    with track_queries(engine):
        # Query 1: Buscar posts
        posts = session.query(Post).limit(10).all()

        # Para cada post, acessar author (lazy loading)
        for post in posts:
            # Query 2, 3, 4... N: Buscar autor de cada post
            print(f"  • {post.title} por {post.author.name}")

    print("\n  💡 O que aconteceu:")
    print("     1 query para buscar posts")
    print("     + 10 queries para buscar cada autor")
    print("     = 11 queries no total! (N+1 onde N=10)")
    print("     Isso escala MUITO MAL (100 posts = 101 queries)")

    session.close()


def demonstrar_solucao_eager_loading(engine, Session):
    """
    SOLUÇÃO: Eager Loading com joinedload
    """
    print("\n" + "=" * 70)
    print("SOLUÇÃO 1: JOINEDLOAD (Eager Loading)")
    print("=" * 70)

    print("\n✅ FORMA CORRETA (Eager Loading):")
    print("Listar 10 posts com nome do autor...")

    session = Session()

    with track_queries(engine):
        # UMA ÚNICA query com JOIN!
        posts = session.query(Post).options(
            joinedload(Post.author)  # Fazer JOIN com users
        ).limit(10).all()

        for post in posts:
            print(f"  • {post.title} por {post.author.name}")

    print("\n  💡 O que aconteceu:")
    print("     1 query com JOIN")
    print("     = Apenas 1 query! (90% mais rápido)")

    session.close()


def demonstrar_selectinload(engine, Session):
    """
    SOLUÇÃO 2: selectinload (melhor para relacionamentos *-many)
    """
    print("\n" + "=" * 70)
    print("SOLUÇÃO 2: SELECTINLOAD")
    print("=" * 70)

    print("\n✅ SELECTINLOAD (melhor para one-to-many):")
    print("Listar usuários com seus posts...")

    session = Session()

    with track_queries(engine):
        # joinedload pode criar cartesian product em one-to-many
        # selectinload usa IN clause (mais eficiente)
        users = session.query(User).options(
            selectinload(User.posts)
        ).limit(5).all()

        for user in users:
            print(f"  • {user.name}: {len(user.posts)} posts")
            for post in user.posts[:2]:  # Mostrar 2 primeiros
                print(f"    - {post.title}")

    print("\n  💡 O que aconteceu:")
    print("     Query 1: SELECT users LIMIT 5")
    print("     Query 2: SELECT posts WHERE user_id IN (1,2,3,4,5)")
    print("     = 2 queries (não N+1!)")

    session.close()


def demonstrar_nested_relationships(engine, Session):
    """
    Relacionamentos aninhados (posts → comments → authors)
    """
    print("\n" + "=" * 70)
    print("RELACIONAMENTOS ANINHADOS")
    print("=" * 70)

    print("\n❌ SEM EAGER LOADING:")
    print("Listar posts com comentários e autores dos comentários...")

    session = Session()

    with track_queries(engine):
        posts = session.query(Post).limit(5).all()

        for post in posts:
            print(f"\n  📝 {post.title}")
            for comment in post.comments[:3]:  # Primeiros 3 comentários
                print(f"    💬 {comment.author.name}: {comment.text}")

    print("\n  ⚠️ Problema: Muitas queries!")

    session.close()

    print("\n✅ COM EAGER LOADING:")

    session = Session()

    with track_queries(engine):
        posts = session.query(Post).options(
            selectinload(Post.comments).selectinload(Comment.author)
        ).limit(5).all()

        for post in posts:
            print(f"\n  📝 {post.title}")
            for comment in post.comments[:3]:
                print(f"    💬 {comment.author.name}: {comment.text}")

    print("\n  ✅ Muito mais eficiente!")

    session.close()


# ============================================================================
# INDEXES E PERFORMANCE
# ============================================================================

def demonstrar_impacto_indexes(engine, Session):
    """
    Demonstrar impacto de indexes em queries.
    """
    print("\n" + "=" * 70)
    print("IMPACTO DE INDEXES")
    print("=" * 70)

    session = Session()

    # Query com index (user_id tem index)
    print("\n✅ Query COM index (user_id):")
    with track_queries(engine):
        posts = session.query(Post).filter(Post.user_id == 5).all()
        print(f"  Encontrado: {len(posts)} posts")

    # Explicar query
    print("\n  📊 EXPLAIN:")
    result = session.execute(text("EXPLAIN QUERY PLAN SELECT * FROM posts WHERE user_id = 5"))
    for row in result:
        print(f"  {row}")

    # Query sem index (views não tem index)
    print("\n⚠️ Query SEM index (views):")
    with track_queries(engine):
        posts = session.query(Post).filter(Post.views > 500).all()
        print(f"  Encontrado: {len(posts)} posts")

    print("\n  📊 EXPLAIN:")
    result = session.execute(text("EXPLAIN QUERY PLAN SELECT * FROM posts WHERE views > 500"))
    for row in result:
        print(f"  {row}")

    print("\n  💡 Observação:")
    print("     - Com index: SEARCH usando index")
    print("     - Sem index: SCAN table (lê todas as linhas)")
    print("     - Em tabelas grandes, isso faz MUITA diferença!")

    session.close()


def demonstrar_quando_criar_indexes():
    """Guia de quando criar indexes."""
    print("\n" + "=" * 70)
    print("QUANDO CRIAR INDEXES?")
    print("=" * 70)

    print("""
✅ CRIE INDEXES EM:

1. Foreign Keys (sempre!)
   CREATE INDEX idx_posts_user_id ON posts(user_id);

2. Colunas frequentemente usadas em WHERE
   SELECT * FROM posts WHERE status = 'published';
   → CREATE INDEX idx_posts_status ON posts(status);

3. Colunas usadas em JOINs
   SELECT * FROM posts JOIN users ON posts.user_id = users.id;
   → Index em posts.user_id (já é FK)

4. Colunas usadas em ORDER BY
   SELECT * FROM posts ORDER BY created_at DESC;
   → CREATE INDEX idx_posts_created_at ON posts(created_at);

5. Composite indexes para queries com múltiplas condições
   SELECT * FROM posts WHERE user_id = 1 AND status = 'published';
   → CREATE INDEX idx_posts_user_status ON posts(user_id, status);

❌ NÃO CRIE INDEXES EM:

1. Tabelas pequenas (<1000 linhas)
   → Full scan é mais rápido

2. Colunas com poucos valores distintos
   → Ex: boolean (true/false) raramente beneficia de index

3. Colunas raramente usadas em queries

4. Tabelas com muitos writes
   → Indexes tornam INSERT/UPDATE/DELETE mais lentos

📊 REGRAS DE OURO:

• Foreign Keys → SEMPRE indexar
• WHERE clauses frequentes → Indexar
• ORDER BY em queries lentas → Indexar
• Tabelas > 10k rows → Considerar indexes
• Write-heavy tables → Menos indexes
• Read-heavy tables → Mais indexes

🔍 ANALISAR:

Use EXPLAIN ANALYZE para verificar se query usa index:

  EXPLAIN ANALYZE SELECT * FROM posts WHERE user_id = 123;

Procure por:
  • "Index Scan" → Bom! Usando index
  • "Seq Scan" → Ruim! Full table scan
    """)


# ============================================================================
# PAGINATION
# ============================================================================

def demonstrar_pagination_offset_vs_cursor(engine, Session):
    """
    Comparar OFFSET vs Cursor-based pagination.
    """
    print("\n" + "=" * 70)
    print("PAGINATION: OFFSET vs CURSOR")
    print("=" * 70)

    session = Session()

    # OFFSET (tradicional)
    print("\n⚠️ OFFSET PAGINATION (página 50):")
    with track_queries(engine):
        # Página 50 (50 * 20 = 1000 offset)
        posts = session.query(Post).order_by(Post.id).limit(20).offset(1000).all()
        print(f"  Retornado: {len(posts)} posts")

    print("\n  💡 Problema:")
    print("     OFFSET 1000 = Banco lê 1020 linhas e descarta 1000!")
    print("     Quanto maior a página, pior a performance.")
    print("     Página 1: rápido")
    print("     Página 1000: MUITO lento")

    # CURSOR-BASED (melhor)
    print("\n✅ CURSOR-BASED PAGINATION:")

    # Primeira página
    with track_queries(engine):
        first_page = session.query(Post).order_by(Post.id).limit(20).all()
        last_id = first_page[-1].id if first_page else 0
        print(f"  Página 1: {len(first_page)} posts (último ID: {last_id})")

    # Próxima página (usar last_id como cursor)
    with track_queries(engine):
        next_page = session.query(Post).filter(
            Post.id > last_id  # Cursor!
        ).order_by(Post.id).limit(20).all()
        print(f"  Página 2: {len(next_page)} posts")

    print("\n  💡 Vantagens:")
    print("     - Sempre rápido (mesmo em páginas altas)")
    print("     - Usa index do ID")
    print("     - Não lê linhas desnecessárias")
    print("     - Performance constante: O(log n)")

    print("\n  📝 Implementação no Frontend:")
    print("""
    // Primeira request
    GET /api/posts?limit=20
    → Retorna posts 1-20 + last_id=20

    // Próxima página
    GET /api/posts?limit=20&cursor=20
    → Retorna posts 21-40 + last_id=40

    // Vantagem: Funciona mesmo com INSERT/DELETE entre requests
    """)

    session.close()


# ============================================================================
# RESUMO E BEST PRACTICES
# ============================================================================

def resumo_best_practices():
    """Resumo de boas práticas."""
    print("\n" + "=" * 70)
    print("RESUMO: BEST PRACTICES")
    print("=" * 70)

    print("""
🎯 REGRAS DE OURO PARA OTIMIZAÇÃO DE QUERIES:

1️⃣ EVITE N+1 (SEMPRE!)
   ❌ for post in posts: print(post.author.name)
   ✅ posts = query(Post).options(joinedload(Post.author)).all()

2️⃣ USE EAGER LOADING APROPRIADO
   • joinedload() → One-to-one, many-to-one
   • selectinload() → One-to-many, many-to-many

3️⃣ INDEXES EM FOREIGN KEYS (OBRIGATÓRIO)
   CREATE INDEX idx_posts_user_id ON posts(user_id);

4️⃣ PAGINATION COM CURSOR (NÃO OFFSET)
   ❌ LIMIT 20 OFFSET 1000
   ✅ WHERE id > last_id LIMIT 20

5️⃣ USE EXPLAIN ANALYZE
   • Identifique queries lentas
   • Verifique se indexes estão sendo usados
   • Otimize queries que fazem Seq Scan

6️⃣ SELECT APENAS COLUNAS NECESSÁRIAS
   ❌ SELECT * FROM posts
   ✅ SELECT id, title, created_at FROM posts

7️⃣ USE CONNECTION POOLING
   • Não crie conexão por request
   • Configure pool_size adequado

8️⃣ CACHE QUERIES FREQUENTES
   • Use Redis para queries repetitivas
   • Invalide cache ao modificar dados

9️⃣ MONITORE PERFORMANCE
   • Log slow queries (>100ms)
   • Use ferramentas como pg_stat_statements (PostgreSQL)

🔟 PROFILE ANTES DE OTIMIZAR
   • "Premature optimization is the root of all evil"
   • Meça primeiro, otimize depois
   • Foque nas queries que realmente são lentas

┌────────────────────────────────────────────────────────┐
│           IMPACTO DE OTIMIZAÇÕES                       │
├────────────────────────────────────────────────────────┤
│ N+1 → Eager loading     : 10-100x mais rápido         │
│ Sem index → Com index   : 100-1000x mais rápido       │
│ OFFSET → Cursor         : 2-10x mais rápido           │
│ SELECT * → SELECT cols  : 1.5-3x mais rápido          │
└────────────────────────────────────────────────────────┘

🚀 CHECKLIST DE PERFORMANCE:

Para cada query, pergunte:
  □ Está fazendo N+1? → Usar eager loading
  □ Tem index nas colunas do WHERE? → Criar index
  □ Está usando OFFSET alto? → Mudar para cursor
  □ Está selecionando colunas não usadas? → SELECT específico
  □ Query demora >100ms? → Investigar com EXPLAIN
    """)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("OTIMIZAÇÃO DE QUERIES E PROBLEMA N+1")
    print("=" * 70)

    # Setup
    engine, Session = setup_database()

    # Demonstrações
    demonstrar_problema_n_plus_1(engine, Session)
    demonstrar_solucao_eager_loading(engine, Session)
    demonstrar_selectinload(engine, Session)
    demonstrar_nested_relationships(engine, Session)
    demonstrar_impacto_indexes(engine, Session)
    demonstrar_quando_criar_indexes()
    demonstrar_pagination_offset_vs_cursor(engine, Session)
    resumo_best_practices()

    print("\n" + "=" * 70)
    print("🎓 CONCLUSÃO")
    print("=" * 70)
    print("""
O problema N+1 é uma das causas mais comuns de performance ruim em aplicações.

✅ SEMPRE use eager loading quando acessar relacionamentos
✅ SEMPRE crie indexes em foreign keys
✅ SEMPRE use cursor-based pagination

Seguindo essas 3 regras, você evita 90% dos problemas de performance! 🚀

Para saber mais:
• SQLAlchemy Query API: https://docs.sqlalchemy.org/en/20/orm/queryguide/
• PostgreSQL EXPLAIN: https://www.postgresql.org/docs/current/using-explain.html
• Index Design: https://use-the-index-luke.com/
    """)


if __name__ == "__main__":
    main()
