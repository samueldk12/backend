# 03 - Banco de Dados

## Índice

1. [SQL vs NoSQL](#sql-vs-nosql)
2. [Indexes](#indexes)
3. [Transactions](#transactions)
4. [N+1 Problem](#n1-problem)
5. [Connection Pooling](#connection-pooling)

---

## SQL vs NoSQL

### SQL (Relacional)

**Quando usar:**
- Dados estruturados e relacionados
- Transações ACID críticas (banco, pagamento)
- Queries complexas com JOINs

**Exemplos:** PostgreSQL, MySQL

```sql
-- Schema rígido
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(200),
    content TEXT
);

-- JOIN query
SELECT u.name, p.title
FROM users u
JOIN posts p ON p.user_id = u.id
WHERE u.id = 1;
```

### NoSQL (Não-Relacional)

**Quando usar:**
- Schema flexível (campos variam)
- Alta escalabilidade horizontal
- Leituras/escritas muito rápidas

**Tipos:**
- **Document**: MongoDB (JSON documents)
- **Key-Value**: Redis (cache)
- **Column**: Cassandra (time-series)
- **Graph**: Neo4j (relacionamentos complexos)

```python
# MongoDB - Schema flexível
{
    "_id": ObjectId("..."),
    "name": "João",
    "email": "joao@example.com",
    "posts": [  # Embedded
        {
            "title": "Post 1",
            "content": "..."
        }
    ],
    "metadata": {  # Campo adicional sem schema
        "last_login": "2024-01-01",
        "preferences": {...}
    }
}
```

---

## Indexes

### O que são Indexes?

Estrutura de dados que melhora velocidade de SELECT (mas piora INSERT/UPDATE).

```sql
-- Sem index: O(N) - full table scan
SELECT * FROM users WHERE email = 'joao@example.com';
-- Scan 1M linhas = ~500ms

-- Com index: O(log N) - B-Tree lookup
CREATE INDEX idx_users_email ON users(email);
-- Lookup em B-Tree = ~5ms
```

### Tipos de Index

**1. B-Tree (default)** - Bom para ranges
```sql
CREATE INDEX idx_created_at ON posts(created_at);

-- Range query rápida
SELECT * FROM posts WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31';
```

**2. Hash** - Apenas equality (=)
```sql
CREATE INDEX idx_email_hash ON users USING HASH(email);

-- Funciona
SELECT * FROM users WHERE email = 'joao@example.com';

-- NÃO funciona com hash
SELECT * FROM users WHERE email LIKE 'joao%';
```

**3. Composite** - Múltiplas colunas
```sql
CREATE INDEX idx_user_date ON posts(user_id, created_at);

-- Index usado ✅
SELECT * FROM posts WHERE user_id = 1 AND created_at > '2024-01-01';

-- Index usado parcialmente ⚠️ (apenas user_id)
SELECT * FROM posts WHERE user_id = 1;

-- Index NÃO usado ❌ (created_at não é prefixo)
SELECT * FROM posts WHERE created_at > '2024-01-01';
```

---

## Transactions

### ACID Properties

```
A - Atomicity:   Tudo ou nada
C - Consistency: Regras sempre válidas
I - Isolation:   Transações não interferem
D - Durability:  Commit é permanente
```

### Exemplo

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Transferência bancária
def transferir(origem_id, destino_id, valor):
    with Session(engine) as session:
        try:
            # BEGIN TRANSACTION
            origem = session.query(Conta).filter_by(id=origem_id).with_for_update().first()
            destino = session.query(Conta).filter_by(id=destino_id).with_for_update().first()

            if origem.saldo < valor:
                raise ValueError("Saldo insuficiente")

            origem.saldo -= valor
            destino.saldo += valor

            session.commit()  # COMMIT - sucesso
        except Exception as e:
            session.rollback()  # ROLLBACK - erro
            raise
```

### Isolation Levels

```sql
-- READ UNCOMMITTED: Lê dados não commitados (dirty read)
-- READ COMMITTED:   Lê apenas dados commitados (default)
-- REPEATABLE READ:  Garante mesma leitura durante transação
-- SERIALIZABLE:     Evita phantom reads (mais lento)

SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
```

---

## N+1 Problem

### O Problema

```python
# ❌ N+1 queries
users = session.query(User).all()  # 1 query

for user in users:
    posts = user.posts  # N queries (uma para cada user!)
    print(f"{user.name}: {len(posts)} posts")

# Total: 1 + N queries
# 100 users = 101 queries! 😱
```

### Solução 1: Eager Loading

```python
# ✅ 2 queries apenas
users = session.query(User).options(
    selectinload(User.posts)  # JOIN ou subquery
).all()

for user in users:
    posts = user.posts  # Já carregado!
    print(f"{user.name}: {len(posts)} posts")

# Total: 2 queries (users + posts)
```

### Solução 2: Aggregate

```python
# ✅ 1 query com COUNT
from sqlalchemy import func

results = session.query(
    User.name,
    func.count(Post.id).label('post_count')
).outerjoin(Post).group_by(User.id).all()

# Total: 1 query!
```

---

## Connection Pooling

### Por que usar?

Criar conexão DB é caro (~50-100ms).
Pool reutiliza conexões.

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# ❌ Sem pool
engine = create_engine(
    "postgresql://user:pass@localhost/db",
    poolclass=None  # Nova conexão a cada request
)
# 1000 req/s = 1000 conexões/s = 💀

# ✅ Com pool
engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=10,        # 10 conexões mantidas
    max_overflow=20,     # +20 em pico
    pool_timeout=30,     # Timeout se pool cheio
    pool_recycle=3600,   # Recicla conexões antigas
)
# 1000 req/s = 10-30 conexões reutilizadas = ✅
```

### Pool em Async

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,
    max_overflow=0,
)
```

---

## Query Optimization

### EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(p.id)
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
GROUP BY u.id;

-- Output mostra:
-- • Seq Scan vs Index Scan
-- • Nested Loop vs Hash Join
-- • Tempo real de execução
```

### Dicas

1. **Index foreign keys**
```sql
CREATE INDEX idx_posts_user_id ON posts(user_id);
```

2. **Limit + Offset** (paginação)
```sql
-- ❌ Lento com offset alto
SELECT * FROM posts ORDER BY id LIMIT 10 OFFSET 100000;

-- ✅ Cursor-based pagination
SELECT * FROM posts WHERE id > 100000 ORDER BY id LIMIT 10;
```

3. **SELECT apenas o necessário**
```sql
-- ❌ Traz todas colunas
SELECT * FROM users;

-- ✅ Apenas o que precisa
SELECT id, name FROM users;
```

---

## Próximo Módulo

➡️ [04 - Arquiteturas](../04-arquiteturas/README.md)
