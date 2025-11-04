# 🎓 Guia de Estudos - Caminho de Aprendizado

> Como estudar este repositório de forma eficiente, do básico ao avançado.

---

## 📋 Como Usar Este Repositório

Este repositório foi desenhado para levar você de **júnior a sênior** em backend development. Cada módulo constrói sobre o anterior, então **siga a ordem recomendada**.

### 🎯 Estrutura do Aprendizado

```
📚 TEORIA → 💻 EXEMPLOS → 🏗️ PROJETO PRÁTICO
```

Para cada tópico:
1. **Leia a teoria** (pasta `teoria/`)
2. **Execute os exemplos** (pasta `exemplos/`)
3. **Implemente no projeto** (pasta `projeto-pratico/`)

---

## 🗺️ Caminho Completo (8-12 Semanas)

### Semana 1-2: Fundamentos (CRÍTICO)

**Por que começar aqui?** Entender como Python funciona por baixo dos panos é essencial para debugar problemas de performance e entender async/await.

#### Dia 1-2: Arquitetura de Computador
📖 **Leia:**
- `01-fundamentos/teoria/README.md`
  - CPU, cache, memória RAM
  - Stack vs Heap
  - Como o computador executa código

💻 **Execute:**
- `01-fundamentos/exemplos/01_memory_allocation.py`
  - Veja reference counting em ação
  - Entenda garbage collection

🧠 **Conceitos-chave:**
- L1/L2/L3 cache hierarchy
- Stack é rápido (LIFO), Heap é flexível
- Reference counting: Python conta referências para liberar memória

---

#### Dia 3-5: Threads, Processes, GIL
📖 **Leia:**
- `01-fundamentos/teoria/README.md` (seção Processos vs Threads)

💻 **Execute:**
- `01-fundamentos/exemplos/02_threads_vs_processes.py`
  - Benchmark: threads vs processes vs async
  - Veja quando cada um é melhor

- `01-fundamentos/exemplos/03_gil_deep_dive.py`
  - Entenda por que threads não funcionam para CPU-bound
  - Veja GIL em ação

🧠 **Conceitos-chave:**
- **GIL**: Global Interpreter Lock - apenas 1 thread Python por vez
- **Threads**: bom para I/O-bound (rede, arquivos)
- **Processes**: necessário para CPU-bound (computação)
- **Async**: melhor para I/O-bound (event loop)

🎯 **Checkpoint:** Você deve conseguir explicar:
- "Por que 10 threads não deixam meu código 10x mais rápido?"
- "Quando usar threads vs processes vs async?"

---

#### Dia 6-7: Configurar Ambiente
🏗️ **Execute:**
- `projeto-pratico/exercicio-01-setup/`
  - Docker Compose com PostgreSQL, Redis
  - FastAPI boilerplate
  - Health checks
  - Environment variables

✅ **Meta:** Ter projeto rodando localmente

---

### Semana 3: Protocolos e APIs

**Por que agora?** Agora que entende fundamentos, aprenda como aplicações se comunicam.

#### Dia 1-3: REST vs GraphQL
📖 **Leia:**
- `02-protocolos/teoria/README.md`
  - HTTP/1.1 vs HTTP/2 vs HTTP/3
  - REST principles
  - GraphQL: resolver over-fetching

💻 **Execute:**
- `02-protocolos/exemplos/01_rest_vs_graphql.py`
  - Veja N+1 problem no REST
  - Compare com GraphQL

🧠 **Conceitos-chave:**
- REST: stateless, cacheable, HATEOAS
- GraphQL: resolver N+1, but more complex
- Quando usar cada um

---

#### Dia 4-5: Comunicação em Tempo Real
💻 **Execute:**
- `02-protocolos/exemplos/02_realtime_communication.py`
  - WebSocket (bidirectional)
  - SSE (server → client)
  - Long Polling (polling inteligente)

🧠 **Conceitos-chave:**
- WebSocket: chat, multiplayer games
- SSE: notificações, feed updates
- Long Polling: fallback quando WebSocket não disponível

---

#### Dia 6-7: Projeto - CRUD de Usuários
🏗️ **Implemente:**
- `projeto-pratico/exercicio-02-usuarios/`
  - CRUD completo
  - 3 abordagens de hashing (bcrypt, argon2, PBKDF2)
  - Repository pattern
  - Testes

🎯 **Checkpoint:** CRUD funcionando com testes passando

---

### Semana 4: Banco de Dados (ESSENCIAL)

**Por que crítico?** 90% dos problemas de performance vêm do banco de dados.

#### Dia 1-3: Query Optimization
📖 **Leia:**
- `03-banco-dados/teoria/README.md`
  - Indexes (B-Tree, Hash)
  - N+1 problem
  - EXPLAIN ANALYZE

💻 **Execute:**
- `03-banco-dados/exemplos/01_query_optimization.py`
  - Veja N+1 problem (11 queries para 10 posts!)
  - Solução: joinedload (1 query apenas)
  - Cursor-based pagination

🧠 **Conceitos-chave:**
- **N+1 problem**: maior vilão de performance
- **Eager loading**: joinedload, selectinload
- **Indexes**: B-Tree para ORDER BY, Hash para =
- **Pagination**: cursor > offset para grandes datasets

---

#### Dia 4-5: Transações e Isolation
💻 **Execute:**
- `03-banco-dados/exemplos/02_transactions_isolation.py`
  - ACID properties
  - Dirty Read, Non-Repeatable Read, Phantom Read
  - Deadlock e como evitar
  - Connection pooling

🧠 **Conceitos-chave:**
- **ACID**: Atomicity, Consistency, Isolation, Durability
- **Read Committed**: padrão do PostgreSQL
- **Repeatable Read**: para operações financeiras
- **SELECT FOR UPDATE**: lock explícito
- **Connection pooling**: 5-10 conexões geralmente suficiente

---

#### Dia 6-7: Projeto - Autenticação
🏗️ **Implemente:**
- `projeto-pratico/exercicio-03-autenticacao/`
  - JWT vs Session
  - Access token (15min) + Refresh token (7 dias)
  - Token rotation
  - RBAC (Role-Based Access Control)
  - Password reset flow
  - Rate limiting

🎯 **Checkpoint:** Auth completo com refresh tokens e RBAC

---

### Semana 5: Arquiteturas

**Por que agora?** Você já tem features funcionando. Hora de organizá-las melhor.

#### Dia 1-4: Padrões Arquiteturais
📖 **Leia:**
- `04-arquiteturas/teoria/README.md`
  - Monolith vs Microservices
  - Layered vs Clean vs DDD
  - Event-Driven Architecture

💻 **Execute:**
- `04-arquiteturas/exemplos/01_architecture_comparison.py`
  - Mesma feature em 4 arquiteturas:
    1. Procedural (~50 linhas)
    2. Layered (~120 linhas)
    3. Clean Architecture (~200 linhas)
    4. DDD (~250+ linhas)

🧠 **Conceitos-chave:**
- **80% dos projetos**: Layered Architecture (Controller → Service → Repository)
- **Clean Architecture**: quando business logic é complexa
- **DDD**: quando domínio é MUITO complexo
- **Microservices**: quando múltiplos times

🎯 **Decisão:** Escolha arquitetura para seu projeto (recomendo Layered)

---

#### Dia 5-7: Projeto - Posts de Texto
🏗️ **Implemente:**
- `projeto-pratico/exercicio-04-posts-texto/`
  - CRUD de posts
  - Soft delete
  - Visibilidade (public, friends, private)
  - Histórico de edições
  - Cursor-based pagination
  - Caching com Redis

🎯 **Checkpoint:** Posts funcionando com cache

---

### Semana 6-7: Performance e Concorrência

**Por que crucial?** Escalar de 100 para 100k usuários requer otimizações.

#### Dia 1-3: Async vs Sync
📖 **Leia:**
- `05-performance-concorrencia/teoria/README.md`

💻 **Execute:**
- `05-performance-concorrencia/exemplos/02_async_vs_sync_comparison.py`
  - I/O-bound: async é 5x mais rápido
  - CPU-bound: só multiprocessing funciona
  - Pitfalls: não bloquear event loop

🧠 **Conceitos-chave:**
- **I/O-bound** → ASYNC (aiohttp, asyncpg)
- **CPU-bound** → MULTIPROCESSING (FFmpeg, ML)
- **GIL**: impede paralelismo em threads
- **Event loop**: executar múltiplas coroutines

---

#### Dia 4-6: Caching Strategies
💻 **Execute:**
- `05-performance-concorrencia/exemplos/01_caching_strategies.py`
  - Cache-Aside (70% dos casos)
  - Write-Through (consistency critical)
  - Write-Behind (high throughput)
  - Read-Through, Refresh-Ahead

🧠 **Conceitos-chave:**
- **Cache-Aside**: app gerencia cache manualmente
- **TTL**: balancear freshness vs performance
- **Invalidation**: harder than caching

---

#### Dia 7: Projeto - Posts de Vídeo
🏗️ **Leia e planeje:**
- `projeto-pratico/exercicio-05-posts-video/`
  - Upload: chunked vs S3 multipart
  - Encoding: FFmpeg pipeline
  - Streaming: HLS adaptive bitrate
  - Background jobs: Celery

🎯 **Opcional:** Implemente upload básico

---

### Semana 8: Filas e Streaming

**Por que essencial?** Jobs pesados não podem bloquear API.

#### Dia 1-4: Message Queues
📖 **Leia:**
- `06-filas-streaming/teoria/README.md`
  - Task Queue vs Message Broker vs Event Stream
  - Celery vs RabbitMQ vs Kafka

💻 **Execute:**
- `06-filas-streaming/exemplos/01_message_queues_comparison.py`
  - Celery: task assíncrona
  - Retry com exponential backoff
  - Idempotência (executar 2x = mesmo resultado)
  - Chain de tasks (pipeline)
  - Dead Letter Queue (DLQ)
  - Fanout pattern (broadcast)
  - Saga pattern (transação distribuída)

🧠 **Conceitos-chave:**
- **Celery**: 80% dos casos (email, reports, encoding)
- **RabbitMQ**: mensageria entre microservices
- **Kafka**: event sourcing, analytics, replay
- **Idempotência**: pode re-executar sem problemas

---

#### Dia 5-7: Integrar Celery no Projeto
🏗️ **Implemente:**
- Enviar email em background
- Processar uploads de vídeo
- Gerar relatórios

---

### Semana 9-10: Cloud e Observabilidade

**Por que fundamental?** Sem observabilidade, você está voando cego.

#### Dia 1-3: Observabilidade
📖 **Leia:**
- `07-cloud-high-architecture/teoria/README.md`
  - 3 pilares: Logs, Metrics, Traces

💻 **Execute:**
- `07-cloud-high-architecture/exemplos/01_observability_monitoring.py`
  - Structured logging (JSON)
  - Prometheus metrics (Counter, Gauge, Histogram)
  - OpenTelemetry distributed tracing
  - Health checks (liveness, readiness)

🧠 **Conceitos-chave:**
- **Logs**: O que aconteceu?
- **Metrics**: Com que frequência? Quanto?
- **Traces**: Onde gastou tempo?
- **Alerting**: Prometheus + Alertmanager

---

#### Dia 4-7: Deploy e CI/CD
📖 **Leia:**
- Docker
- Kubernetes básico
- GitHub Actions

🏗️ **Implemente:**
- Dockerfile otimizado (multi-stage build)
- docker-compose.yml para produção
- CI/CD pipeline (.github/workflows/)
  - Rodar testes
  - Build Docker image
  - Deploy automático

---

### Semana 11-12: Projeto Final e Polimento

#### Completar Features Restantes
🏗️ **Implemente:**
- Likes e comentários
- Timeline/feed personalizado
- Notificações em tempo real (WebSocket)
- Search (Elasticsearch)

#### Otimização e Testes
- Cobertura de testes >80%
- Load testing (Locust)
- Performance profiling
- Security audit

---

## 📚 Documentos de Apoio

### Durante Todo o Percurso
- **CHEATSHEET.md**: comandos rápidos (git, docker, psql, redis)
- **DEBUGGING_GUIDE.md**: como debugar problemas
- **BEST_PRACTICES.md**: checklist de qualidade

### Ao Final
- **ROADMAP.md**: próximos passos na carreira
- Portfolios no GitHub
- Contribuir para open source

---

## 🎯 Checkpoints e Auto-Avaliação

### Nível Júnior (Semanas 1-4)
✅ Entendo fundamentos (CPU, memória, threads, GIL)
✅ Sei fazer CRUD com FastAPI
✅ Entendo N+1 problem e como resolver
✅ Sei fazer autenticação com JWT
✅ Tenho projeto rodando localmente com Docker

### Nível Pleno (Semanas 5-8)
✅ Sei quando usar async vs threads vs multiprocessing
✅ Implemento caching eficazmente
✅ Uso Celery para background jobs
✅ Entendo diferentes arquiteturas e quando usar cada
✅ Sei otimizar queries (EXPLAIN ANALYZE)

### Nível Sênior (Semanas 9-12)
✅ Implemento observabilidade completa (logs, metrics, traces)
✅ Projeto tem CI/CD funcionando
✅ Sei fazer deploy em produção
✅ Entendo trade-offs de diferentes tecnologias
✅ Consigo debugar problemas complexos

---

## 💡 Dicas de Estudo

### 1. **NÃO pule fundamentos**
Muitos devs pulam para frameworks sem entender o básico. Resultado: ficam travados quando precisam otimizar ou debugar.

### 2. **Execute TODOS os exemplos**
Não apenas leia. Execute, modifique, quebre, conserte. Aprendizado acontece experimentando.

### 3. **Faça anotações**
Crie seu próprio cheatsheet. Escrever ajuda a fixar.

### 4. **Ensine alguém**
Explique conceitos para um amigo ou escreva blog posts. Se consegue ensinar, você realmente entendeu.

### 5. **Compare abordagens**
Sempre que ver "Abordagem A vs B", TESTE ambas. Veja os trade-offs na prática.

### 6. **Use debugger**
Não use apenas print(). Aprenda pdb/ipdb. Coloque breakpoints, inspecione variáveis.

### 7. **Leia código de produção**
Veja projetos open source: Django, FastAPI, Flask. Como eles resolvem problemas?

---

## 📖 Leituras Complementares

### Durante Fundamentos (Semana 1-2)
- **Livro**: "Computer Systems: A Programmer's Perspective"
  - Capítulo sobre memória e cache
- **Vídeo**: "What is the GIL?" - David Beazley

### Durante Banco de Dados (Semana 4)
- **Livro**: "Use The Index, Luke!" (online, grátis)
- **Curso**: "PostgreSQL Query Optimization" (Udemy)

### Durante Arquitetura (Semana 5)
- **Livro**: "Clean Architecture" - Robert Martin
- **Artigo**: "Monolith First" - Martin Fowler

### Durante Performance (Semana 6-7)
- **Talk**: "Python Concurrency From the Ground Up" - David Beazley
- **Docs**: FastAPI Async Best Practices

### Durante Cloud (Semana 9-10)
- **Livro**: "Designing Data-Intensive Applications"
- **Curso**: "Kubernetes for Developers"

---

## 🎓 Certificações Recomendadas

Após completar este repositório:

1. **AWS Certified Developer - Associate**
   - Demonstra conhecimento em cloud
   - Muito valorizado pelo mercado

2. **Kubernetes (CKA)**
   - Se pretende trabalhar com K8s

3. **Portfolio no GitHub**
   - Mais importante que certificações
   - Mostre código real

---

## 🚀 Próximos Passos (Pós-Repositório)

### Aprofundar
1. **Distributed Systems**
   - CAP theorem na prática
   - Consensus algorithms (Raft, Paxos)
   - Eventual consistency

2. **Security**
   - OWASP Top 10
   - Penetration testing
   - Security audit

3. **Machine Learning em Produção**
   - MLOps
   - Model serving (FastAPI + MLflow)
   - A/B testing

### Contribuir
1. **Open Source**
   - FastAPI, Django, Flask
   - Fixe bugs, adicione features
   - Aprenda com code reviews

2. **Blog/YouTube**
   - Ensine o que aprendeu
   - Construa audiência
   - Networking

---

## 📞 Comunidade e Suporte

### Onde Tirar Dúvidas
- **Stack Overflow**: para erros específicos
- **Reddit**: r/learnpython, r/django, r/FastAPI
- **Discord**: Python Brasil, FastAPI, Docker

### Como Fazer Boas Perguntas
1. Descreva o problema claramente
2. Mostre o que já tentou
3. Código mínimo reproduzível
4. Mensagem de erro completa
5. O que você espera vs o que acontece

---

## ✅ Checklist Final

Ao completar este repositório, você deve conseguir:

### Técnico
- [ ] Explicar GIL e quando threads não funcionam
- [ ] Otimizar queries (resolver N+1, criar indexes)
- [ ] Implementar autenticação segura (JWT + refresh tokens)
- [ ] Escolher arquitetura adequada ao projeto
- [ ] Usar async/await corretamente
- [ ] Implementar caching eficazmente
- [ ] Usar Celery para background jobs
- [ ] Adicionar observabilidade (logs, metrics, traces)
- [ ] Fazer deploy com Docker e CI/CD

### Soft Skills
- [ ] Ler documentação de bibliotecas
- [ ] Debugar problemas complexos
- [ ] Comparar trade-offs de tecnologias
- [ ] Escrever código limpo e testável
- [ ] Documentar decisões técnicas

---

## 🎉 Parabéns!

Se chegou até aqui, você tem conhecimento equivalente a um **desenvolvedor pleno/sênior**.

**Próximo passo:** Aplique para vagas e mostre este projeto como portfolio!

---

**Bons estudos! 🚀**

Dúvidas? Abra uma issue ou entre em contato.
