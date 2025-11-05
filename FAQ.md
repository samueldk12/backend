# ❓ FAQ - Perguntas Frequentes

> Respostas para as dúvidas mais comuns de desenvolvedores backend.

---

## 📋 Índice

- [Fundamentos](#fundamentos)
- [Performance e Async](#performance-e-async)
- [Banco de Dados](#banco-de-dados)
- [Arquitetura](#arquitetura)
- [Segurança](#segurança)
- [DevOps e Deploy](#devops-e-deploy)
- [Carreira](#carreira)

---

## 🔧 Fundamentos

### Por que meu código com 10 threads não fica 10x mais rápido?

**R:** O **GIL (Global Interpreter Lock)** do Python permite que apenas **1 thread execute código Python por vez**.

Threads funcionam APENAS para **I/O-bound** (esperando rede, arquivos, banco):
- ✅ HTTP requests: 10 threads = ~10x mais rápido
- ❌ Cálculos: 10 threads = mesma velocidade (GIL bloqueia)

**Solução para CPU-bound:**
```python
# ❌ Threads não ajudam
with ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(cpu_intensive_task, data)

# ✅ Multiprocessing funciona
with ProcessPoolExecutor(max_workers=10) as executor:
    results = executor.map(cpu_intensive_task, data)
```

---

### Quando usar async vs threads vs multiprocessing?

**R:** Depende do tipo de tarefa:

| Tipo de Tarefa | Melhor Abordagem | Por quê |
|----------------|------------------|---------|
| **I/O-bound** (HTTP, DB, arquivos) | **ASYNC** | Event loop, milhares de connections |
| **I/O-bound** (biblioteca síncrona) | **THREADS** | Fallback quando async não disponível |
| **CPU-bound** (cálculos, encoding) | **MULTIPROCESSING** | Bypassa GIL, usa múltiplos cores |

**Exemplo:**
```python
# I/O-bound: Web scraping
async def scrape_websites(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# CPU-bound: Processar imagens
with ProcessPoolExecutor() as executor:
    results = executor.map(process_image, images)
```

---

### O que significa "non-blocking" em async?

**R:** Significa que enquanto **espera I/O**, o código **libera controle** para outras tarefas executarem.

```python
# BLOCKING (trava tudo por 2s)
def bad():
    time.sleep(2)  # ❌ Nada mais executa

# NON-BLOCKING (executa outras tarefas durante 2s)
async def good():
    await asyncio.sleep(2)  # ✅ Event loop executa outras tarefas
```

**Analogia:** Restaurante
- **Blocking**: Garçom espera na cozinha até prato ficar pronto (desperdiça tempo)
- **Non-blocking**: Garçom atende outras mesas enquanto cozinha prepara (eficiente)

---

## ⚡ Performance e Async

### Por que await não deixa meu código mais rápido?

**R:** `await` sozinho **NÃO paraleliza**. Você precisa usar `asyncio.gather()`:

```python
# ❌ SEQUENCIAL (4 segundos)
async def slow():
    result1 = await fetch_api()  # 2s
    result2 = await fetch_api()  # 2s
    return [result1, result2]

# ✅ PARALELO (2 segundos)
async def fast():
    task1 = fetch_api()  # Inicia task
    task2 = fetch_api()  # Inicia task
    return await asyncio.gather(task1, task2)  # Aguarda ambos
```

---

### Posso usar requests em código async?

**R:** ❌ **NÃO!** `requests` é **bloqueante** e vai **travar o event loop**.

```python
# ❌ ERRADO: bloqueia event loop
async def bad():
    response = requests.get(url)  # Trava tudo!

# ✅ CORRETO: use aiohttp
async def good():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

**Regra de ouro:** Em código async, use **apenas bibliotecas async**:
- ❌ `requests` → ✅ `aiohttp` ou `httpx`
- ❌ `psycopg2` → ✅ `asyncpg`
- ❌ `redis` → ✅ `aioredis`
- ❌ `time.sleep` → ✅ `asyncio.sleep`

---

### Como saber se meu código está bloqueando o event loop?

**R:** Use `asyncio.to_thread()` ou monitore latência:

```python
import asyncio
import time

async def blocking_task():
    """Tarefa bloqueante"""
    time.sleep(5)  # ❌ Bloqueia event loop

async def check_blocking():
    """Detectar bloqueio"""
    start = time.time()

    # Criar task que deve completar em 1s
    async def quick_task():
        await asyncio.sleep(1)
        print(f"Quick task: {time.time() - start:.1f}s")

    # Se quick_task demorar mais que 1s, algo está bloqueando
    await asyncio.gather(
        blocking_task(),
        quick_task()
    )

# Resultado: quick_task demora 5s (deveria ser 1s)
# Conclusão: blocking_task está bloqueando event loop
```

**Solução:**
```python
async def non_blocking():
    """Rodar código bloqueante em thread"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, cpu_intensive_function)
```

---

## 🗄️ Banco de Dados

### O que é o problema N+1?

**R:** Fazer **N queries extras** desnecessárias em um loop.

```python
# ❌ N+1 PROBLEM (11 queries!)
posts = db.query(Post).limit(10).all()  # 1 query
for post in posts:
    print(post.author.name)  # 10 queries! (N+1)

# ✅ SOLUÇÃO: Eager loading (1 query)
posts = db.query(Post).options(
    joinedload(Post.author)  # JOIN
).limit(10).all()
for post in posts:
    print(post.author.name)  # Dados já carregados
```

**Como detectar:**
```python
# Ative SQL logging
engine = create_engine(url, echo=True)

# Conte queries
from sqlalchemy import event
query_count = 0

@event.listens_for(Engine, "before_cursor_execute")
def count_queries(conn, cursor, statement, parameters, context, executemany):
    global query_count
    query_count += 1
```

---

### Quando criar índices no banco?

**R:** Crie índices em colunas usadas em:
- ✅ `WHERE` (filtros)
- ✅ `ORDER BY` (ordenação)
- ✅ `JOIN` (foreign keys)
- ✅ `GROUP BY` (agregações)

```sql
-- ✅ BOM: filtrar por email
CREATE INDEX idx_users_email ON users(email);
SELECT * FROM users WHERE email = 'joao@example.com';

-- ✅ BOM: ordenar por created_at
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20;

-- ✅ BOM: índice composto para query específica
CREATE INDEX idx_posts_user_status ON posts(user_id, status);
SELECT * FROM posts WHERE user_id = 123 AND status = 'published';
```

**⚠️ Cuidados:**
- ❌ Não crie índices em TODAS as colunas (overhead em INSERT/UPDATE)
- ❌ Não crie índices em colunas com baixa cardinalidade (ex: boolean)
- ✅ Use `EXPLAIN ANALYZE` para verificar se índice está sendo usado

---

### Offset pagination é ruim?

**R:** Sim para **grandes datasets**. Use **cursor-based pagination**.

```python
# ❌ OFFSET: ruim para páginas altas
# ?page=1000 força DB a escanear e descartar 20000 linhas
posts = db.query(Post).offset(20000).limit(20).all()

# ✅ CURSOR: performance constante
# ?cursor=12345 usa índice em id
posts = db.query(Post).filter(Post.id > cursor).limit(20).all()
```

**Por quê?**
- Offset: `O(n)` - escaneia n linhas
- Cursor: `O(log n)` - usa índice B-Tree

**Quando usar cada:**
- Offset: número de páginas pequeno (<100), need page numbers
- Cursor: infinite scroll, large datasets, APIs

---

### Qual isolation level usar?

**R:** Depende do caso de uso:

| Isolation Level | Use quando | Exemplo |
|-----------------|------------|---------|
| **Read Committed** (padrão) | Maioria dos casos (80%) | Buscar posts, usuários |
| **Repeatable Read** | Precisa leituras consistentes | Reports, analytics |
| **Serializable** | Consistência é CRÍTICA | Pagamentos, transferências bancárias |

```python
# Read Committed (padrão PG)
engine = create_engine(url)

# Repeatable Read
engine = create_engine(url, isolation_level="REPEATABLE READ")

# Serializable
engine = create_engine(url, isolation_level="SERIALIZABLE")
```

**Trade-off:**
- Read Committed: mais rápido, mas pode ter non-repeatable reads
- Serializable: mais lento, pode ter serialization failures (retries)

---

## 🏗️ Arquitetura

### Monolith ou Microservices?

**R:** **Comece com Monolith**. Microservices só quando necessário.

**Monolith quando:**
- ✅ Time pequeno (<10 devs)
- ✅ Produto ainda validando PMF (product-market fit)
- ✅ Não tem experiência com microservices
- ✅ 90% dos casos

**Microservices quando:**
- ✅ Múltiplos times independentes
- ✅ Partes do sistema com diferentes requirements (ex: video encoding needs GPU)
- ✅ Escala diferente por serviço (ex: API vs worker)
- ✅ Já tem infraestrutura pronta (K8s, service mesh)

**Citação famosa:** "Almost never start with microservices. Almost always regret it." - Martin Fowler

---

### Clean Architecture vs Layered Architecture?

**R:** Use **Layered** para 80% dos casos. Clean quando business logic é MUITO complexa.

**Layered (3 camadas):**
```
Controller → Service → Repository
```
- ✅ Simples
- ✅ Fácil de entender
- ✅ Suficiente para maioria dos projetos

**Clean Architecture:**
```
Controllers → Use Cases → Domain Entities
                ↓
         Gateways/Adapters
                ↓
          Infrastructure
```
- ✅ Testável sem dependências externas
- ✅ Business logic isolada
- ❌ Mais código (boilerplate)
- ❌ Overhead para projetos simples

**Decisão:** Complexidade do domínio justifica o overhead?

---

### Quando usar Event-Driven Architecture?

**R:** Quando precisa **desacoplar serviços** ou **auditar tudo**.

**Use quando:**
- ✅ Microservices precisam comunicar sem dependência direta
- ✅ Precisa replay de eventos (event sourcing)
- ✅ Auditoria completa (compliance)
- ✅ Múltiplos consumers para mesmo evento

**Exemplo:** E-commerce
```
Order Created Event
    ↓
    ├─> Inventory Service (reserva estoque)
    ├─> Payment Service (cobra cliente)
    ├─> Shipping Service (cria ordem de envio)
    └─> Email Service (envia confirmação)
```

**Não use quando:**
- ❌ Monolith simples (overhead desnecessário)
- ❌ Time não tem experiência com event sourcing
- ❌ Debugar fica complexo demais

---

## 🔒 Segurança

### JWT ou Session-based auth?

**R:** Depende do caso de uso:

| Aspecto | JWT | Session |
|---------|-----|---------|
| **Stateless** | ✅ Sim | ❌ Não (redis/db) |
| **Escalabilidade** | ✅ Fácil | ⚠️  Precisa shared storage |
| **Revogar token** | ❌ Difícil | ✅ Fácil (delete session) |
| **Tamanho** | ❌ Grande (1KB+) | ✅ Pequeno (32 bytes) |
| **Complexidade** | ⚠️  Média | ✅ Simples |

**Recomendação:**
- **JWT** se: API pública, mobile apps, precisa escalar horizontalmente
- **Session** se: web app tradicional, precisa revogar tokens frequentemente

**Melhor dos dois mundos:**
```python
# JWT de curta duração + Refresh token em DB
access_token = create_jwt(user_id, expires_in=15*60)  # 15 min
refresh_token = create_refresh_token(user_id, expires_in=7*24*3600)  # 7 dias
save_refresh_token_to_db(refresh_token)  # Pode revogar
```

---

### Qual algoritmo de hash usar para senhas?

**R:** **Argon2** > bcrypt > PBKDF2 > ❌ SHA256

```python
# 🥇 MELHOR: Argon2 (vencedor do Password Hashing Competition)
from argon2 import PasswordHasher
ph = PasswordHasher()
hashed = ph.hash(password)

# 🥈 BOM: bcrypt (indústria usa há anos)
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"])
hashed = pwd_context.hash(password)

# 🥉 OK: PBKDF2 (Django usa, mas não recomendado)
# ❌ NUNCA: SHA256, MD5 (muito rápido = inseguro)
```

**Por quê Argon2?**
- Resistente a GPU/ASIC attacks
- Memory-hard (precisa muita RAM = difícil otimizar ataque)
- Venceu competição de 2015

---

### Como proteger contra SQL Injection?

**R:** **SEMPRE** use **parameterized queries** (prepared statements).

```python
# ❌ VULNERÁVEL: SQL injection
user_id = request.query_params.get("id")
query = f"SELECT * FROM users WHERE id = {user_id}"  # ☠️  Inject: id=1 OR 1=1
result = db.execute(query)

# ✅ SEGURO: Parameterized query
user_id = request.query_params.get("id")
query = "SELECT * FROM users WHERE id = :user_id"
result = db.execute(query, {"user_id": user_id})  # Sanitizado automaticamente

# ✅ SEGURO: SQLAlchemy ORM
user = db.query(User).filter(User.id == user_id).first()  # Protegido
```

**Nunca:**
- ❌ String formatting: `f"SELECT * FROM users WHERE id = {id}"`
- ❌ String concatenation: `"SELECT * FROM users WHERE id = " + str(id)`

---

## 🚀 DevOps e Deploy

### Docker vs Virtual Machine?

**R:** **Docker** para quase tudo hoje em dia.

| Aspecto | Docker | VM |
|---------|--------|-----|
| **Startup** | Segundos | Minutos |
| **Tamanho** | MB | GB |
| **Overhead** | Baixo | Alto |
| **Isolamento** | Process-level | Hardware-level |
| **Use caso** | Apps, microservices | Legacy, Windows apps no Linux |

**Quando usar VM:**
- Precisa rodar Windows app no Linux
- Isolamento de segurança crítico (multi-tenancy)
- Legacy apps que não podem ser containerizadas

---

### Quantos workers Gunicorn/Uvicorn usar?

**R:** Fórmula: `(2 x CPU_CORES) + 1`

```bash
# Servidor com 4 cores:
# workers = (2 x 4) + 1 = 9

uvicorn main:app --workers 9
```

**Por quê?**
- 2x cores: enquanto 1 worker espera I/O, outro usa CPU
- +1: buffer para variabilidade

**Async (FastAPI):**
```bash
# Async precisa menos workers (event loop)
uvicorn main:app --workers 4  # Mesmo número de cores
```

**Monitorar:**
```bash
# Se CPU < 80% e workers todos busy: aumentar workers
# Se CPU > 80%: diminuir workers ou escalar horizontalmente
```

---

### Health check: liveness vs readiness?

**R:** Kubernetes usa ambos para propósitos diferentes:

**Liveness Probe:**
- Pergunta: "App está vivo?"
- Se falhar: **reiniciar pod**
- Exemplo: `/health/live` retorna 200

```python
@app.get("/health/live")
def liveness():
    # Simples: app está rodando?
    return {"status": "alive"}
```

**Readiness Probe:**
- Pergunta: "App está pronto para receber tráfego?"
- Se falhar: **remover do load balancer** (não reiniciar!)
- Exemplo: `/health/ready` verifica dependências

```python
@app.get("/health/ready")
def readiness():
    # Completo: DB conectado? Redis ok? Deps prontas?
    checks = {
        "database": check_db_connection(),
        "cache": check_redis(),
        "external_api": check_api()
    }

    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    else:
        return Response(status_code=503, content={"status": "not_ready"})
```

---

### O que colocar no .env e o que não colocar?

**R:** ✅ Secrets, ❌ Código

**✅ Coloque no .env:**
- Database URLs
- API keys
- Senhas
- Tokens
- Feature flags

**❌ NÃO coloque no .env:**
- Lógica de negócio
- Configurações de app que não mudam por ambiente
- Constantes

```python
# ✅ BOM
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=super-secret-key-123
AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE

# ❌ RUIM
MAX_UPLOAD_SIZE=10485760  # Constante, coloque no código
ALGORITHM=HS256  # Não muda, coloque no código
```

**Segurança:**
```bash
# ✅ NUNCA comite .env
echo ".env" >> .gitignore

# ✅ Use .env.example sem valores reais
cp .env .env.example
# Editar .env.example e remover valores sensíveis
```

---

## 💼 Carreira

### Quanto tempo para ficar sênior?

**R:** **5-8 anos** em média, mas depende mais de **experiência** que tempo.

**Júnior (0-2 anos):**
- Implementa features com supervisão
- Segue padrões existentes
- Foca em aprender

**Pleno (2-5 anos):**
- Implementa features autonomamente
- Propõe melhorias técnicas
- Mentorar juniores
- Entende trade-offs

**Sênior (5-10 anos):**
- **Design** de sistemas completos
- **Decisões** arquiteturais
- **Liderança** técnica (não necessariamente gestão)
- **Influencia** múltiplos times
- Entende impacto no **negócio**

**Acelerador:**
- Trabalhar em startups (mais responsabilidade cedo)
- Contribuir para open source (code review de experts)
- Estudar sistemas de grandes empresas (Netflix, Uber tech blogs)

---

### Vale a pena fazer certificações?

**R:** Depende. **Portfolio > Certificações**.

**Certificações que valem:**
- ✅ AWS Certified Developer/Solutions Architect (muito valorizado)
- ✅ Kubernetes CKA (se trabalhar com K8s)
- ⚠️  Python certifications (menos valorizado)

**Melhor investimento:**
- ✅ **GitHub com projetos reais**
- ✅ **Blog posts técnicos**
- ✅ **Contribuições open source**
- ✅ **Tech talks / YouTube**

**Empresas querem ver:**
1. Você resolve problemas reais? (GitHub)
2. Você comunica bem? (Blog, talks)
3. Você trabalha em time? (Open source contributions)

---

### Especializar ou generalizar?

**R:** **T-shaped**: profundo em 1-2 áreas, amplo em outras.

```
     Python/Backend (PROFUNDO)
           │
           │ (especialista)
           │
    ───────┴──────────────────────
     Frontend, DevOps, Data
        (conhecimento amplo)
```

**Júnior:** Generalizar (explorar)
**Pleno:** Escolher especialização (aprofundar)
**Sênior:** T-shaped (profundo + amplo)

**Áreas hot em 2024:**
- Backend + Cloud (AWS, K8s)
- Backend + Data Engineering
- Backend + ML/AI
- Backend + DevOps (SRE)

---

### Como se preparar para entrevistas de sênior?

**R:** Foco em **System Design** e **trade-offs**.

**Técnicas:**
1. **LeetCode** (menos importante para sênior, mas ainda cobrado)
   - Focus: Medium problems
   - 50 problemas é suficiente

2. **System Design** (CRÍTICO)
   - Desenhe: Twitter, Instagram, WhatsApp
   - Trade-offs: SQL vs NoSQL, quando usar cache, como escalar
   - Livro: "Designing Data-Intensive Applications"

3. **Experiência passada** (STAR method)
   - Situation, Task, Action, Result
   - "Conte sobre uma vez que otimizou performance"
   - "Como você lidou com um sistema caindo?"

4. **Código Real**
   - Traga projeto do GitHub
   - Explique decisões arquiteturais
   - "Por que escolheu PostgreSQL e não MongoDB?"

**Empresas top (FAANG):**
- LeetCode: 40% (Hard problems)
- System Design: 40%
- Behavioral: 20%

**Startups:**
- Coding: 30% (práticos, não LeetCode)
- System Design: 30%
- Experiência: 40%

---

## 🤔 Perguntas Filosóficas

### Vale a pena otimizar prematuramente?

**R:** **"Premature optimization is the root of all evil" - Donald Knuth**

**Não otimize antes de:**
1. **Medir** (use profiler, não achismos)
2. **Identificar** bottleneck
3. **Verificar** que é problema real (afeta usuários?)

**Exemplo:**
```python
# ❌ Otimização prematura
# Gastar 2 dias otimizando função que executa 1x por hora

# ✅ Otimização necessária
# Otimizar query que executa 1000x/s e demora 500ms
```

**Mas algumas otimizações são "free":**
- ✅ Usar índices no banco (sempre)
- ✅ Eager loading para prevenir N+1 (sempre)
- ✅ Connection pooling (sempre)
- ✅ Caching de dados estáticos (sempre)

**Regra:** Se é best practice conhecida, não é otimização prematura.

---

### Devo reescrever sistema legado ou refatorar?

**R:** **Quase sempre refatorar**. Reescritas raramente funcionam.

**Reescrever quando:**
- ✅ Tecnologia está obsoleta (Python 2, PHP 4)
- ✅ Arquitetura é fundamentalmente quebrada
- ✅ Custo de manutenção > custo de reescrita
- ✅ Time inteiro dedicado à reescrita (não paralelo)

**Refatorar quando:**
- ✅ Sistema funciona (clientes usam)
- ✅ Problema é organização do código (não tecnologia)
- ✅ Pode fazer incremental (feature by feature)

**Estratégia híbrida (Strangler Fig Pattern):**
```
1. Novo sistema convive com legado
2. Gradualmente migrar features
3. Quando legado ficar vazio, desligar

Example:
    ┌─────────┐
    │ New API │ ← /users (nova feature)
    └─────────┘
    ┌─────────┐
    │ Old API │ ← /posts (ainda legado)
    └─────────┘
```

**Citação:** "Things you're likely to get wrong: 1. Estimating rewrite time (2-3x real)"

---

### Quando é hora de sair do emprego atual?

**R:** Quando você parou de **aprender** ou **crescer**.

**Sinais que é hora:**
- ❌ Não aprende nada novo há 6+ meses
- ❌ Tecnologia está ultrapassada e empresa não muda
- ❌ Não há oportunidade de crescimento (promoção)
- ❌ Salário muito abaixo do mercado (>20%)
- ❌ Cultura tóxica (burnout, falta de respeito)

**Sinais para ficar:**
- ✅ Aprende constantemente
- ✅ Tem mentores (tech leads, seniors)
- ✅ Trabalha em problemas desafiadores
- ✅ Salário justo
- ✅ Work-life balance

**Timing:**
- Júnior: 1-2 anos por empresa (aprender rápido)
- Pleno/Sênior: 2-4 anos (mostrar impacto)
- Muito job hopping (<1 ano) é red flag para recrutadores

---

## 📞 Dúvidas Não Respondidas?

Abra uma **issue** no GitHub com sua pergunta!

Podemos adicionar aqui para ajudar outros devs.

---

**Happy coding! 🚀**
