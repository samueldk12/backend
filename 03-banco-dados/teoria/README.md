# Módulo 03 - Banco de Dados

## 🎯 Objetivo

Dominar o design, otimização e escolha de bancos de dados para diferentes cenários.

---

## 📚 Conteúdo

1. [SQL vs NoSQL](#1-sql-vs-nosql)
2. [Modelagem e Normalização](#2-modelagem-e-normalização)
3. [Indexes e Performance](#3-indexes-e-performance)
4. [Transactions e ACID](#4-transactions-e-acid)
5. [Replicação e Sharding](#5-replicação-e-sharding)
6. [CAP Theorem](#6-cap-theorem)
7. [Tipos de Bancos NoSQL](#7-tipos-de-bancos-nosql)

---

## 1. SQL vs NoSQL

### 1.1 SQL (Relacional)

**Estrutura:** Tabelas com schemas fixos

```sql
-- Tabela Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabela Posts (relacionamento)
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255),
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Características:**
- ✅ ACID compliant
- ✅ Relações complexas (JOINs)
- ✅ Schema rígido (integridade)
- ✅ Queries poderosas (SQL)
- ❌ Escalabilidade horizontal difícil
- ❌ Schema changes custosos

**Bancos populares:**
- PostgreSQL (mais completo)
- MySQL/MariaDB
- SQLite (embedded)

### 1.2 NoSQL (Não-relacional)

**Estrutura:** Documentos, key-value, grafo, etc.

```javascript
// MongoDB (Document Store)
{
  "_id": "507f1f77bcf86cd799439011",
  "email": "joao@example.com",
  "name": "João",
  "posts": [
    {
      "title": "Meu Post",
      "content": "...",
      "created_at": "2025-01-01"
    }
  ],
  "created_at": "2025-01-01"
}
```

**Características:**
- ✅ Flexível (schema-less)
- ✅ Escalável horizontalmente
- ✅ Alta performance para casos específicos
- ❌ Menos garantias (eventual consistency)
- ❌ Sem JOINs nativos (denormalização)

**Bancos populares:**
- MongoDB (document)
- Redis (key-value)
- Cassandra (wide-column)
- Neo4j (graph)

### 1.3 Quando usar cada um?

| Cenário | SQL | NoSQL |
|---------|-----|-------|
| **Dados estruturados** | ✅ | ❌ |
| **Relacionamentos complexos** | ✅ | ❌ |
| **Transactions críticas** | ✅ | ⚠️ |
| **Schema flexível** | ❌ | ✅ |
| **Escala horizontal** | ⚠️ | ✅ |
| **Cache** | ❌ | ✅ (Redis) |
| **Dados geoespaciais** | ⚠️ | ✅ (MongoDB) |
| **Grafos sociais** | ❌ | ✅ (Neo4j) |

**Decisão:**
```
Sistema financeiro → SQL (ACID)
Rede social → SQL (relacionamentos) + NoSQL (cache)
IoT sensor data → NoSQL (escala, flexibilidade)
E-commerce → SQL (transações) + NoSQL (catálogo)
```

---

## 2. Modelagem e Normalização

### 2.1 Formas Normais

**1NF (Primeira Forma Normal):**
- Cada célula contém valores atômicos
- Sem arrays ou listas

```sql
-- ❌ NÃO 1NF
CREATE TABLE users (
    id INT,
    name VARCHAR(100),
    phones VARCHAR(255)  -- "111-1111,222-2222" ❌
);

-- ✅ 1NF
CREATE TABLE users (
    id INT,
    name VARCHAR(100)
);

CREATE TABLE user_phones (
    user_id INT REFERENCES users(id),
    phone VARCHAR(20)
);
```

**2NF (Segunda Forma Normal):**
- Estar em 1NF
- Todos os atributos não-chave dependem da chave primária completa

**3NF (Terceira Forma Normal):**
- Estar em 2NF
- Sem dependências transitivas

```sql
-- ❌ NÃO 3NF (país depende de cidade, não do pedido)
CREATE TABLE orders (
    id INT PRIMARY KEY,
    city VARCHAR(100),
    country VARCHAR(100)  -- Depende de city! ❌
);

-- ✅ 3NF
CREATE TABLE orders (
    id INT PRIMARY KEY,
    city_id INT REFERENCES cities(id)
);

CREATE TABLE cities (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    country_id INT REFERENCES countries(id)
);
```

### 2.2 Denormalização (Performance vs Normalização)

**Normalizado (3NF):**
```sql
-- 3 JOINs para pegar posts com autor
SELECT p.*, u.name, u.email
FROM posts p
JOIN users u ON p.user_id = u.id
WHERE p.id = 123;
```

**Denormalizado:**
```sql
-- Sem JOIN, mais rápido
SELECT id, title, content, author_name, author_email
FROM posts
WHERE id = 123;

-- Trade-off: Redundância (nome/email duplicados em cada post)
```

**Quando denormalizar?**
- ✅ Read-heavy (muitas leituras)
- ✅ Performance crítica
- ✅ Dados não mudam frequentemente
- ❌ Write-heavy (muitas escritas)
- ❌ Dados mudam muito

---

## 3. Indexes e Performance

### 3.1 O que são Indexes?

Indexes são estruturas de dados que aceleram buscas.

**Sem index:**
```sql
-- O(n) - scan completo da tabela
SELECT * FROM users WHERE email = 'joao@example.com';
-- Tempo: ~500ms para 1M registros
```

**Com index:**
```sql
CREATE INDEX idx_users_email ON users(email);

-- O(log n) - busca binária na árvore B-Tree
SELECT * FROM users WHERE email = 'joao@example.com';
-- Tempo: ~5ms para 1M registros
```

### 3.2 Tipos de Indexes

**B-Tree (padrão):**
- Uso geral
- Bom para: `=`, `<`, `>`, `BETWEEN`, `ORDER BY`

```sql
CREATE INDEX idx_users_created_at ON users(created_at);

-- Usa index
SELECT * FROM users WHERE created_at > '2025-01-01';
```

**Hash:**
- Apenas igualdade (`=`)
- Muito rápido para lookups exatos

```sql
CREATE INDEX idx_users_id_hash ON users USING HASH (id);

-- Usa index
SELECT * FROM users WHERE id = 123;

-- ❌ NÃO usa index
SELECT * FROM users WHERE id > 100;
```

**Full-Text:**
- Busca em texto

```sql
CREATE INDEX idx_posts_content_fts ON posts USING GIN (to_tsvector('english', content));

-- Busca full-text
SELECT * FROM posts WHERE to_tsvector('english', content) @@ to_tsquery('backend');
```

**Partial Index:**
- Index apenas parte dos dados

```sql
-- Index apenas usuários ativos (economiza espaço)
CREATE INDEX idx_active_users ON users(email) WHERE active = true;
```

**Composite Index:**
- Múltiplas colunas

```sql
CREATE INDEX idx_posts_user_created ON posts(user_id, created_at);

-- ✅ Usa index (ordem importa!)
SELECT * FROM posts WHERE user_id = 123 AND created_at > '2025-01-01';
SELECT * FROM posts WHERE user_id = 123;  -- Usa apenas primeira parte

-- ❌ NÃO usa index completamente
SELECT * FROM posts WHERE created_at > '2025-01-01';  -- Pula user_id
```

### 3.3 Query Optimization

**EXPLAIN ANALYZE:**
```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(p.id) as post_count
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
GROUP BY u.id, u.name
HAVING COUNT(p.id) > 10;

-- Output mostra:
-- - Seq Scan vs Index Scan
-- - Cost estimado
-- - Tempo real de execução
-- - Número de rows processadas
```

**N+1 Problem:**
```python
# ❌ PROBLEMA: 1 query + N queries (uma por usuário)
users = db.query("SELECT * FROM users LIMIT 100")
for user in users:
    posts = db.query("SELECT * FROM posts WHERE user_id = ?", user.id)  # N queries!

# ✅ SOLUÇÃO: Eager loading (1 query)
users_with_posts = db.query("""
    SELECT u.*, p.*
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    WHERE u.id IN (SELECT id FROM users LIMIT 100)
""")
```

**Pagination:**
```sql
-- ❌ OFFSET lento para páginas grandes
SELECT * FROM posts
ORDER BY created_at DESC
LIMIT 20 OFFSET 10000;  -- Lê 10020 rows e descarta 10000!

-- ✅ Cursor-based pagination (muito mais rápido)
SELECT * FROM posts
WHERE created_at < '2025-01-01 12:00:00'  -- Último valor da página anterior
ORDER BY created_at DESC
LIMIT 20;
```

---

## 4. Transactions e ACID

### 4.1 ACID

**Atomicity (Atomicidade):**
- Tudo ou nada

```python
# Transferência bancária
BEGIN TRANSACTION;
    UPDATE accounts SET balance = balance - 100 WHERE id = 1;
    UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;  # Ambas ou nenhuma!
```

**Consistency (Consistência):**
- Banco mantém regras (constraints)

```sql
-- Constraint garante consistência
ALTER TABLE accounts ADD CONSTRAINT check_balance CHECK (balance >= 0);

-- ❌ Falha se violar constraint
UPDATE accounts SET balance = -50 WHERE id = 1;  -- ERRO!
```

**Isolation (Isolamento):**
- Transactions não interferem entre si

**Durability (Durabilidade):**
- Dados commitados persistem (mesmo com crash)

### 4.2 Isolation Levels

```
┌─────────────────────┬──────────────┬────────────────┬─────────────┐
│ Isolation Level     │ Dirty Read   │ Non-Repeatable │ Phantom     │
│                     │              │ Read           │ Read        │
├─────────────────────┼──────────────┼────────────────┼─────────────┤
│ Read Uncommitted    │ ✅ Possível  │ ✅ Possível    │ ✅ Possível │
│ Read Committed      │ ❌ Impedido  │ ✅ Possível    │ ✅ Possível │
│ Repeatable Read     │ ❌ Impedido  │ ❌ Impedido    │ ✅ Possível │
│ Serializable        │ ❌ Impedido  │ ❌ Impedido    │ ❌ Impedido │
└─────────────────────┴──────────────┴────────────────┴─────────────┘
```

**Read Committed (padrão PostgreSQL):**
```python
# Transaction 1
BEGIN;
SELECT balance FROM accounts WHERE id = 1;  # 1000
# Transaction 2 atualiza e commita
SELECT balance FROM accounts WHERE id = 1;  # 900 (vê mudança!)
COMMIT;
```

**Repeatable Read:**
```python
# Transaction 1
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM accounts WHERE id = 1;  # 1000
# Transaction 2 atualiza e commita
SELECT balance FROM accounts WHERE id = 1;  # 1000 (não vê mudança!)
COMMIT;
```

**Quando usar:**
- **Read Committed**: Padrão, bom para maioria
- **Repeatable Read**: Relatórios consistentes
- **Serializable**: Transações financeiras críticas (lento!)

---

## 5. Replicação e Sharding

### 5.1 Replicação

**Master-Slave (Read Replicas):**
```
        ┌─────────────┐
        │   Master    │ ← Writes
        │ (Primary)   │
        └──────┬──────┘
               │ Replicação
      ┌────────┼────────┐
      │        │        │
 ┌────▼───┐ ┌─▼─────┐ ┌▼──────┐
 │ Slave1 │ │Slave2 │ │Slave3 │ ← Reads
 │(Replica)│ │       │ │       │
 └────────┘ └───────┘ └───────┘
```

**Vantagens:**
- ✅ Escala leituras
- ✅ Alta disponibilidade
- ✅ Backup automático

**Desvantagens:**
- ⚠️ Replication lag (eventual consistency)
- ⚠️ Writes não escalam

**Multi-Master:**
```
┌─────────┐ ⇄ ┌─────────┐
│ Master1 │   │ Master2 │
└─────────┘   └─────────┘
  ↕ Writes      ↕ Writes
```

**Vantagens:**
- ✅ Escala writes
- ✅ Alta disponibilidade

**Desvantagens:**
- ⚠️ Conflitos de escrita
- ⚠️ Mais complexo

### 5.2 Sharding (Particionamento Horizontal)

**Dividir dados em múltiplos servidores:**

```
           ┌──────────────┐
           │ Application  │
           └──────┬───────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
┌─────▼────┐ ┌───▼─────┐ ┌──▼──────┐
│ Shard 1  │ │ Shard 2 │ │ Shard 3 │
│ Users    │ │ Users   │ │ Users   │
│ ID 1-1M  │ │ 1M-2M   │ │ 2M-3M   │
└──────────┘ └─────────┘ └─────────┘
```

**Estratégias:**

**1. Range-based:**
```python
# Dividir por ID
if user_id <= 1_000_000:
    shard = shard_1
elif user_id <= 2_000_000:
    shard = shard_2
else:
    shard = shard_3
```

**2. Hash-based:**
```python
# Distribuição uniforme
shard = hash(user_id) % num_shards
```

**3. Geographic:**
```python
# Dividir por região
if user.country == 'BR':
    shard = shard_br
elif user.country == 'US':
    shard = shard_us
```

**Vantagens:**
- ✅ Escala writes e reads
- ✅ Suporta bilhões de registros

**Desvantagens:**
- ❌ Complexidade alta
- ❌ JOINs entre shards impossíveis
- ❌ Rebalanceamento difícil

---

## 6. CAP Theorem

```
      ┌─────────────────┐
      │  Consistency    │ ← Todos veem mesmos dados
      └────────┬────────┘
               │
        Escolha 2 de 3!
               │
      ┌────────┼────────┐
      │                 │
┌─────▼──────┐   ┌─────▼──────┐
│Availability│   │  Partition │
│            │   │  Tolerance │
│Todo request│   │Funciona com│
│tem resposta│   │falhas rede │
└────────────┘   └────────────┘
```

**Combinações:**

**CA (Consistency + Availability):**
- Sem partition tolerance
- Exemplos: RDBMS tradicionais (single node)
- **Problema**: Falha de rede derruba tudo

**CP (Consistency + Partition Tolerance):**
- Sacrifica availability
- Exemplos: MongoDB, HBase, Redis (strong consistency)
- **Comportamento**: Pode rejeitar requests durante partições

**AP (Availability + Partition Tolerance):**
- Sacrifica consistency (eventual)
- Exemplos: Cassandra, DynamoDB, CouchDB
- **Comportamento**: Sempre responde (pode retornar dados antigos)

**Na prática:**
```
Sistema financeiro → CP (consistência > disponibilidade)
Rede social        → AP (disponibilidade > consistência)
E-commerce         → Mix (carrinho=AP, pagamento=CP)
```

---

## 7. Tipos de Bancos NoSQL

### 7.1 Key-Value (Redis, Memcached)

```python
# Simples: chave → valor
SET user:123:name "João"
GET user:123:name  # "João"

# Uso: cache, sessions, rate limiting
```

### 7.2 Document (MongoDB, CouchDB)

```javascript
// Documentos JSON aninhados
{
  "user_id": 123,
  "name": "João",
  "addresses": [
    {"street": "Rua A", "city": "SP"},
    {"street": "Rua B", "city": "RJ"}
  ]
}

// Uso: catálogos, CMS, dados semi-estruturados
```

### 7.3 Wide-Column (Cassandra, HBase)

```
Row Key | Column1 | Column2 | Column3 | ...
--------|---------|---------|---------|----
user:1  | name    | email   | age     |
user:2  | name    | city    | phone   | country

// Colunas podem variar por row!
// Uso: IoT, time-series, logs
```

### 7.4 Graph (Neo4j, ArangoDB)

```cypher
// Relacionamentos são first-class citizens
(João)-[:SEGUE]->(Maria)
(João)-[:CURTIU]->(Post1)
(Maria)-[:CRIOU]->(Post1)

// Query: Amigos de amigos que curtiram posts similares
MATCH (me:User {name: 'João'})-[:SEGUE]->(friend)-[:SEGUE]->(fof)
WHERE NOT (me)-[:SEGUE]->(fof)
RETURN fof

// Uso: redes sociais, recomendações, fraud detection
```

---

## 🎓 Resumo - Decisões

### Escolha de Banco:

```
Dados estruturados + transactions → PostgreSQL
Cache / sessions                  → Redis
Dados flexíveis + escala          → MongoDB
Time-series / IoT                 → Cassandra / InfluxDB
Grafos / redes sociais            → Neo4j
Full-text search                  → Elasticsearch
```

### Otimização:

```
Queries lentas    → Adicione indexes
Leituras > Writes → Read replicas
Crescimento       → Sharding
Latência          → Cache (Redis)
Consistência      → Transactions + ACID
Disponibilidade   → Replicação + eventual consistency
```

---

## 📝 Próximos Passos

1. Exemplos práticos em [`../exemplos/`](../exemplos/)
2. Exercícios em [`../exercicios/`](../exercicios/)
3. Avance para **[Módulo 04 - Arquiteturas](../../04-arquiteturas/teoria/README.md)**
