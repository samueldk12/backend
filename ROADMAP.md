# Roadmap de Aprendizado Backend

> Guia passo a passo para ir de iniciante a desenvolvedor backend sênior.

---

## 📊 Níveis de Conhecimento

```
┌────────────────────────────────────────────────────────────┐
│  Júnior    │  Pleno     │  Sênior    │  Staff/Principal │
├────────────┼────────────┼────────────┼──────────────────┤
│  0-2 anos  │  2-5 anos  │  5-10 anos │  10+ anos        │
└────────────┴────────────┴────────────┴──────────────────┘
```

---

## 🎯 Nível 1: Júnior (0-2 anos)

### Objetivo
Construir bases sólidas e ser produtivo em tarefas supervisionadas.

### O que estudar

#### Fase 1: Fundamentos (1-2 meses)
- [ ] **Python básico**
  - Sintaxe, tipos de dados, estruturas de controle
  - Funções, classes, módulos
  - List comprehensions, generators
  - Recursos: [Python.org Tutorial](https://docs.python.org/3/tutorial/)

- [ ] **Git e controle de versão**
  - Comandos básicos (add, commit, push, pull)
  - Branches e merges
  - Pull requests
  - Recursos: [Git Book](https://git-scm.com/book/en/v2)

- [ ] **Terminal/CLI**
  - Navegação, manipulação de arquivos
  - Pipes, redirecionamento
  - Recursos: [Linux Command Line](https://www.linuxcommand.org/)

#### Fase 2: Web Fundamentals (1-2 meses)
- [ ] **HTTP básico**
  - Métodos (GET, POST, PUT, DELETE)
  - Status codes
  - Headers
  - Recursos: [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP)

- [ ] **FastAPI básico**
  - Criar endpoints simples
  - Path e query parameters
  - Request body
  - Documentação: [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)

- [ ] **Banco de dados SQL**
  - SELECT, INSERT, UPDATE, DELETE
  - JOINs básicos
  - Recursos: [SQL Zoo](https://sqlzoo.net/)

#### Fase 3: Projeto Prático (1-2 meses)
- [ ] **TODO API**
  - CRUD completo
  - Validação com Pydantic
  - SQLite como database
  - Testes básicos com pytest

### Habilidades Esperadas
- ✅ Criar endpoints REST básicos
- ✅ Fazer queries SQL simples
- ✅ Usar Git para versionamento
- ✅ Debugar código
- ✅ Escrever testes básicos

### Projetos para Portfolio
1. **TODO API** com autenticação
2. **Blog API** com posts e comentários
3. **Weather API** consumindo API externa

---

## 🎯 Nível 2: Pleno (2-5 anos)

### Objetivo
Ser independente, desenhar soluções e mentorar júniores.

### O que estudar

#### Fase 1: Arquitetura (2-3 meses)
- [ ] **[Módulo 04 - Arquiteturas](./04-arquiteturas/teoria/README.md)**
  - Layered Architecture
  - Repository Pattern
  - Service Layer
  - Clean Architecture (introdução)

- [ ] **Design Patterns**
  - Singleton, Factory, Strategy
  - Dependency Injection
  - Recursos: [Refactoring Guru](https://refactoring.guru/design-patterns)

#### Fase 2: Performance (2-3 meses)
- [ ] **[Módulo 03 - Banco de Dados](./03-banco-dados/teoria/README.md)**
  - Indexes e otimização
  - N+1 problem
  - Transactions
  - Migrations

- [ ] **[Módulo 05 - Performance](./05-performance-concorrencia/teoria/README.md)**
  - Caching (Redis)
  - Connection pooling
  - Async/await
  - Profiling

#### Fase 3: Segurança (1-2 meses)
- [ ] **Autenticação e Autorização**
  - JWT tokens
  - OAuth2
  - RBAC (Role-Based Access Control)

- [ ] **Segurança Web**
  - OWASP Top 10
  - SQL Injection prevention
  - XSS, CSRF

#### Fase 4: DevOps Básico (1-2 meses)
- [ ] **Docker**
  - Dockerfile
  - Docker Compose
  - Recursos: [Docker Getting Started](https://docs.docker.com/get-started/)

- [ ] **CI/CD**
  - GitHub Actions básico
  - Automated testing
  - Deploy automatizado

#### Fase 5: Projeto Intermediário (2-3 meses)
- [ ] **E-commerce API**
  - Produtos, carrinho, checkout
  - Autenticação JWT
  - Payment gateway integration
  - Redis caching
  - Docker

### Habilidades Esperadas
- ✅ Desenhar arquitetura de APIs médias
- ✅ Otimizar queries e performance
- ✅ Implementar autenticação segura
- ✅ Usar Docker e CI/CD
- ✅ Fazer code review
- ✅ Mentorar júniores

### Projetos para Portfolio
1. **E-commerce API** completa
2. **Social Media API** com posts, followers
3. **Video Streaming API** com upload e encoding

---

## 🎯 Nível 3: Sênior (5-10 anos)

### Objetivo
Desenhar sistemas escaláveis, liderar tecnicamente, tomar decisões arquiteturais.

### O que estudar

#### Fase 1: Sistemas Distribuídos (3-4 meses)
- [ ] **[Módulo 06 - Filas e Streaming](./06-filas-streaming/teoria/README.md)**
  - Message queues (RabbitMQ, Kafka)
  - Event-driven architecture
  - Eventual consistency

- [ ] **Microservices**
  - Service mesh
  - API Gateway
  - Service discovery
  - Recursos: [Microservices Patterns](https://microservices.io/patterns/)

- [ ] **CAP Theorem e Trade-offs**
  - Consistency vs Availability
  - Partition tolerance
  - Distributed transactions

#### Fase 2: Escalabilidade (3-4 meses)
- [ ] **[Módulo 07 - Cloud](./07-cloud-high-architecture/teoria/README.md)**
  - Kubernetes
  - Auto-scaling
  - Load balancing
  - CDN

- [ ] **Database Scaling**
  - Replication
  - Sharding
  - Read replicas

#### Fase 3: Observabilidade (2-3 meses)
- [ ] **Monitoring e Logging**
  - Prometheus, Grafana
  - ELK Stack
  - Distributed tracing (Jaeger)

- [ ] **SRE Practices**
  - SLIs, SLOs, SLAs
  - Error budgets
  - Incident response

#### Fase 4: Domain-Driven Design (2-3 meses)
- [ ] **DDD**
  - Bounded contexts
  - Aggregates
  - Domain events
  - Recursos: [Domain-Driven Design](https://www.amazon.com/Domain-Driven-Design-Tackling-Complexity-Software/dp/0321125215)

#### Fase 5: Projeto Avançado (3-6 meses)
- [ ] **Rede Social de Video (Este Projeto!)**
  - Microservices
  - Video encoding pipeline
  - Real-time notifications
  - Horizontal scaling
  - Full observability

### Habilidades Esperadas
- ✅ Desenhar sistemas de larga escala
- ✅ Fazer trade-offs arquiteturais
- ✅ Liderar tecnicamente um time
- ✅ Fazer estimativas precisas
- ✅ Mentorar plenos
- ✅ Participar de discussões de produto

### Projetos para Portfolio
1. **Video Streaming Platform** (estilo YouTube)
2. **Real-time Chat Platform** (estilo Slack)
3. **Ride-sharing System** (estilo Uber)

---

## 🎯 Nível 4: Staff/Principal (10+ anos)

### Objetivo
Definir direção técnica da empresa, influenciar múltiplos times, resolver problemas únicos.

### O que dominar

#### Technical Leadership
- [ ] Arquitetura de múltiplos sistemas
- [ ] Technical debt management
- [ ] Technology selection
- [ ] Build vs Buy decisions

#### Cross-functional Skills
- [ ] Product thinking
- [ ] Business acumen
- [ ] Communication e apresentação
- [ ] Technical writing

#### Advanced Topics
- [ ] Machine Learning infrastructure
- [ ] Security architecture
- [ ] Compliance e regulations
- [ ] Cost optimization

### Habilidades Esperadas
- ✅ Influenciar arquitetura de toda empresa
- ✅ Resolver problemas únicos/complexos
- ✅ Mentorar seniores
- ✅ Representar engenharia com liderança
- ✅ Criar RFCs e ADRs
- ✅ Tech talks e conferências

---

## 📅 Timeline Realista

```
┌─────────────────────────────────────────────────────────┐
│ ANO 1-2    │ Júnior                                     │
├─────────────────────────────────────────────────────────┤
│ ANO 2-5    │ Pleno                                      │
├─────────────────────────────────────────────────────────┤
│ ANO 5-10   │ Sênior                                     │
├─────────────────────────────────────────────────────────┤
│ ANO 10+    │ Staff/Principal                            │
└─────────────────────────────────────────────────────────┘

⚠️ IMPORTANTE:
  • Não é linear (pode ser mais rápido ou lento)
  • Experiência > Tempo
  • Sempre depende do contexto e da empresa
```

---

## 🗺️ Como Usar Este Roadmap

### 1. Avalie seu nível atual
```
Faça uma auto-avaliação honesta:
□ Consigo criar um CRUD completo? → Júnior
□ Consigo otimizar queries lentas? → Pleno
□ Consigo desenhar um sistema distribuído? → Sênior
```

### 2. Defina metas de curto prazo (3 meses)
```
Exemplo (Júnior → Pleno):
Mês 1: Estudar Repository Pattern + fazer projeto
Mês 2: Estudar otimização de DB + refatorar projeto
Mês 3: Adicionar cache Redis + Docker
```

### 3. Construa projetos
```
Não apenas ler/assistir:
❌ Assistir 10 cursos
✅ Fazer 2-3 projetos completos

Projeto > Curso
```

### 4. Contribua com open source
```
Benefícios:
✅ Code review de devs experientes
✅ Aprende padrões reais
✅ Portfolio público
✅ Networking
```

### 5. Escreva e ensine
```
Melhor forma de aprender:
• Blog posts sobre o que aprendeu
• Tutoriais no YouTube
• Responder Stack Overflow
• Mentorar iniciantes
```

---

## 📚 Recursos Essenciais

### Livros
- **Júnior**
  - Clean Code (Robert C. Martin)
  - Python Crash Course (Eric Matthes)

- **Pleno**
  - Designing Data-Intensive Applications (Martin Kleppmann)
  - System Design Interview (Alex Xu)

- **Sênior**
  - Domain-Driven Design (Eric Evans)
  - Building Microservices (Sam Newman)

### Cursos
- [FastAPI Full Course](https://fastapi.tiangolo.com/tutorial/)
- [PostgreSQL Tutorial](https://www.postgresql.org/docs/current/tutorial.html)
- [Docker Mastery](https://www.udemy.com/course/docker-mastery/)
- [System Design Primer](https://github.com/donnemartin/system-design-primer)

### YouTube Channels
- [ArjanCodes](https://www.youtube.com/c/ArjanCodes) - Python e design
- [Hussein Nasser](https://www.youtube.com/c/HusseinNasser-software-engineering) - Backend deep dives
- [ByteByteGo](https://www.youtube.com/c/ByteByteGo) - System design

### Practice Platforms
- [LeetCode](https://leetcode.com/) - Algoritmos
- [HackerRank](https://www.hackerrank.com/) - SQL, APIs
- [System Design Interview](https://www.tryexponent.com/) - Design systems

---

## ✅ Checklist de Skills por Nível

### Júnior
- [ ] Python intermediário
- [ ] Git básico
- [ ] SQL básico
- [ ] REST API (GET, POST, PUT, DELETE)
- [ ] Testes unitários básicos

### Pleno
- [ ] Arquitetura (Repository, Service Layer)
- [ ] Otimização de DB (indexes, N+1)
- [ ] Autenticação (JWT, OAuth2)
- [ ] Caching (Redis)
- [ ] Docker básico
- [ ] CI/CD básico

### Sênior
- [ ] Sistemas distribuídos (queues, events)
- [ ] Microservices
- [ ] Kubernetes
- [ ] Database scaling (replication, sharding)
- [ ] Observability (metrics, logs, traces)
- [ ] DDD
- [ ] Technical leadership

---

## 🎯 Dicas Finais

### DO ✅
- Construa projetos reais
- Leia código de projetos open source
- Faça code review de outros
- Aprenda com erros
- Escreva testes
- Documente decisões
- Mentore outros
- Peça feedback

### DON'T ❌
- Tutorial hell (só assistir sem fazer)
- Pular fundamentos
- Focar só em frameworks (aprenda o "porquê")
- Ter medo de perguntar
- Ignorar soft skills
- Copiar código sem entender

---

## 🚀 Começe Agora!

Não espere estar "pronto". Comece com o que sabe e aprenda fazendo.

**Próximo passo:**
1. Escolha um projeto do seu nível
2. Dedique 1-2 horas por dia
3. Faça, erre, aprenda, refatore
4. Repita

**Lembre-se:** Toda pessoa sênior foi júnior um dia. A diferença é persistência! 💪

---

**Este repositório tem tudo que você precisa. Bora codar! 🚀**
