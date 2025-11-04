# Backend Study Repository - Do Básico ao Avançado

> Repositório completo para estudo de conceitos de backend, desde low-level architecture até high-level architecture, com projeto prático de uma rede social de vídeo e texto usando FastAPI.

## 🎯 Objetivo

Este repositório foi criado para guiar desenvolvedores desde conceitos fundamentais até tópicos avançados necessários para se tornar um desenvolvedor backend sênior capaz de trabalhar em qualquer empresa de tecnologia.

## 🏗️ Estrutura do Repositório

### Módulos Teóricos

#### 📚 [01 - Fundamentos e Low-Level Architecture](./01-fundamentos)
- **Teoria**: Como computadores funcionam, CPU, memória, processos, threads
- **Conceitos**:
  - Arquitetura de CPU e memória
  - System calls e kernel space vs user space
  - Process vs Thread
  - Stack vs Heap
  - Endianness e representação de dados
  - Assembly básico e como código Python é executado
- **Exemplos práticos**: Demonstrações de alocação de memória, threads em Python
- **Exercícios**: Implementações práticas dos conceitos

#### 🌐 [02 - Protocolos e Comunicação](./02-protocolos)
- **Teoria**: Camadas OSI/TCP-IP, protocolos de rede
- **Conceitos**:
  - TCP vs UDP (quando usar cada um)
  - HTTP/1.1 vs HTTP/2 vs HTTP/3
  - WebSockets vs Server-Sent Events vs Long Polling
  - gRPC vs REST vs GraphQL
  - Serialização: JSON, Protocol Buffers, MessagePack, BSON
  - Encoding: UTF-8, Base64, URL encoding
- **Exemplos**: Implementações de cada protocolo
- **Comparações**: Benchmarks e casos de uso

#### 💾 [03 - Banco de Dados](./03-banco-dados)
- **Teoria**: Fundamentos de persistência de dados
- **Conceitos**:
  - SQL vs NoSQL (quando usar cada um)
  - ACID vs BASE
  - Indexes (B-Tree, Hash, Full-text)
  - Query optimization e EXPLAIN
  - Transactions e isolation levels
  - Replicação (Master-Slave, Multi-Master)
  - Sharding e particionamento
  - CAP Theorem
  - Databases: PostgreSQL, MongoDB, Redis, Elasticsearch
- **Exemplos**: Queries otimizadas vs não otimizadas
- **Exercícios**: Design de schemas, otimização de queries

#### 🏛️ [04 - Arquiteturas de Software](./04-arquiteturas)
- **Teoria**: Padrões arquiteturais modernos
- **Conceitos**:
  - Monolith vs Microservices vs Modular Monolith
  - Layered Architecture (MVC, MTV)
  - Clean Architecture / Hexagonal Architecture
  - Event-Driven Architecture
  - CQRS (Command Query Responsibility Segregation)
  - Event Sourcing
  - Domain-Driven Design (DDD)
  - Service Mesh
- **Exemplos**: Implementação de cada arquitetura
- **Análise**: Prós, contras e quando usar cada uma

#### ⚡ [05 - Performance e Concorrência](./05-performance-concorrencia)
- **Teoria**: Otimização e processamento paralelo
- **Conceitos**:
  - Threading vs Multiprocessing vs Async/Await
  - GIL (Global Interpreter Lock) no Python
  - Connection pooling
  - Database connection management
  - Caching strategies (Cache-aside, Write-through, Write-behind)
  - CDN e edge caching
  - Load balancing (Round-robin, Least connections, IP hash)
  - Rate limiting e throttling
  - Profiling e monitoring
- **Exemplos**: Código síncrono vs assíncrono vs paralelo
- **Benchmarks**: Comparações de performance

#### 📨 [06 - Filas e Streaming](./06-filas-streaming)
- **Teoria**: Processamento assíncrono e dados em tempo real
- **Conceitos**:
  - Message Queues vs Event Streams
  - RabbitMQ, Redis Queue, Celery
  - Apache Kafka, AWS Kinesis
  - Pub/Sub patterns
  - Dead letter queues
  - Idempotência
  - At-least-once vs At-most-once vs Exactly-once
  - Backpressure handling
- **Exemplos**: Implementações de filas e streams
- **Casos de uso**: Quando usar cada tecnologia

#### ☁️ [07 - Cloud e High-Level Architecture](./07-cloud-high-architecture)
- **Teoria**: Infraestrutura moderna e escalabilidade
- **Conceitos**:
  - Cloud providers (AWS, GCP, Azure)
  - Containerization (Docker, Kubernetes)
  - Serverless (Lambda, Cloud Functions)
  - CI/CD pipelines
  - Infrastructure as Code (Terraform, CloudFormation)
  - Observability (Logs, Metrics, Traces)
  - Service discovery
  - Circuit breakers
  - Health checks
  - Blue-Green deployment, Canary releases
  - Auto-scaling strategies
- **Exemplos**: Configurações de infraestrutura
- **Diagramas**: Arquiteturas de sistemas distribuídos

### 🚀 Projeto Prático: Rede Social de Vídeo e Texto

O projeto prático implementa uma rede social completa, progressivamente, aplicando todos os conceitos aprendidos.

#### [Exercício 01 - Setup e Estrutura Inicial](./projeto-pratico/exercicio-01-setup)
- Configuração do ambiente
- Estrutura do projeto FastAPI
- Docker e docker-compose
- Configuração de linting e formatação

#### [Exercício 02 - Gerenciamento de Usuários](./projeto-pratico/exercicio-02-usuarios)
- CRUD de usuários
- Validação com Pydantic
- Password hashing (bcrypt vs argon2)
- Diferentes formas de estruturar endpoints

#### [Exercício 03 - Autenticação e Autorização](./projeto-pratico/exercicio-03-autenticacao)
- JWT vs Session-based auth
- OAuth2 implementation
- Refresh tokens
- Permission-based access control (RBAC)

#### [Exercício 04 - Posts de Texto](./projeto-pratico/exercicio-04-posts-texto)
- CRUD de posts
- Paginação (offset vs cursor-based)
- Full-text search
- Diferentes formas de modelar relacionamentos

#### [Exercício 05 - Posts de Vídeo](./projeto-pratico/exercicio-05-posts-video)
- Upload de vídeos (multipart, chunked, resumable)
- Video encoding (FFmpeg)
- Adaptive bitrate streaming (HLS, DASH)
- Thumbnail generation
- Storage (local vs S3 vs CDN)

#### [Exercício 06 - Relacionamentos Sociais](./projeto-pratico/exercicio-06-relacionamentos)
- Follow/Unfollow
- Likes, comments, shares
- Notificações
- Diferentes formas de modelar grafos sociais

#### [Exercício 07 - Timeline e Feed](./projeto-pratico/exercicio-07-timeline)
- Algoritmos de ranking
- Personalização de feed
- Infinite scroll
- Real-time updates

#### [Exercício 08 - Otimização de Performance](./projeto-pratico/exercicio-08-performance)
- Database query optimization
- N+1 problem solutions
- Eager loading vs Lazy loading
- DataLoader pattern

#### [Exercício 09 - Caching](./projeto-pratico/exercicio-09-cache)
- Redis implementation
- Cache invalidation strategies
- Cache warming
- Distributed caching

#### [Exercício 10 - Processamento com Filas](./projeto-pratico/exercicio-10-filas)
- Celery para tarefas assíncronas
- Video processing queue
- Email notifications
- Retry strategies

#### [Exercício 11 - Streaming em Tempo Real](./projeto-pratico/exercicio-11-streaming)
- WebSocket para notificações
- Server-Sent Events para updates
- Live video streaming
- Chat em tempo real

#### [Exercício 12 - Deploy e Cloud](./projeto-pratico/exercicio-12-cloud)
- Dockerização completa
- Kubernetes deployment
- CI/CD com GitHub Actions
- Monitoring com Prometheus e Grafana
- Logging centralizado (ELK stack)

## 🎓 Metodologia de Estudo

Cada módulo segue a estrutura:

1. **Teoria** (`teoria/README.md`): Explicação aprofundada dos conceitos
2. **Exemplos** (`exemplos/`): Código demonstrando cada conceito
3. **Exercícios** (`exercicios/`): Problemas para praticar

### Para cada conceito técnico:
- ✅ **O que é**: Definição clara
- ✅ **Como funciona**: Detalhes de implementação
- ✅ **Múltiplas abordagens**: Diferentes formas de resolver o problema
- ✅ **Comparação**: Prós e contras de cada abordagem
- ✅ **Melhor prática**: Recomendação justificada
- ✅ **Exemplo prático**: Código funcional
- ✅ **Exercício**: Implementação hands-on

## 🛠️ Tecnologias Utilizadas

- **Python 3.11+**
- **FastAPI** - Framework web moderno e rápido
- **PostgreSQL** - Banco de dados relacional
- **MongoDB** - Banco de dados NoSQL
- **Redis** - Cache e message broker
- **Celery** - Fila de tarefas assíncronas
- **Docker & Docker Compose** - Containerização
- **Pytest** - Testes
- **SQLAlchemy** - ORM
- **Alembic** - Migrations
- **Pydantic** - Validação de dados
- **FFmpeg** - Processamento de vídeo
- **Nginx** - Reverse proxy e streaming

## 📋 Pré-requisitos

```bash
# Python 3.11+
python --version

# Docker e Docker Compose
docker --version
docker-compose --version

# Git
git --version
```

## 🚀 Como Começar

```bash
# Clone o repositório
git clone <seu-repositorio>
cd backend

# Comece pelo módulo 01
cd 01-fundamentos/teoria
cat README.md

# Ou vá direto para o projeto prático
cd projeto-pratico/exercicio-01-setup
cat README.md
```

## 📚 Ordem Recomendada de Estudo

### Nível Iniciante
1. 01 - Fundamentos e Low-Level Architecture
2. 02 - Protocolos e Comunicação
3. Projeto Prático: Exercícios 01-03

### Nível Intermediário
4. 03 - Banco de Dados
5. 04 - Arquiteturas de Software
6. Projeto Prático: Exercícios 04-07

### Nível Avançado
7. 05 - Performance e Concorrência
8. 06 - Filas e Streaming
9. Projeto Prático: Exercícios 08-11

### Nível Sênior
10. 07 - Cloud e High-Level Architecture
11. Projeto Prático: Exercício 12
12. Revisão e otimização de todo o projeto

## 🎯 Objetivos de Aprendizado

Ao completar este repositório, você será capaz de:

- ✅ Entender como código é executado em baixo nível
- ✅ Escolher o protocolo correto para cada situação
- ✅ Desenhar schemas de banco de dados eficientes
- ✅ Escrever queries otimizadas
- ✅ Implementar diferentes arquiteturas de software
- ✅ Otimizar performance de aplicações
- ✅ Trabalhar com processamento assíncrono
- ✅ Implementar streaming de vídeo
- ✅ Desenhar sistemas distribuídos escaláveis
- ✅ Fazer deploy em produção com confiança
- ✅ Monitorar e debugar sistemas em produção

## 📖 Recursos Adicionais

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [System Design Primer](https://github.com/donnemartin/system-design-primer)
- [Web Scalability for Startup Engineers](https://www.amazon.com/Scalability-Startup-Engineers-Artur-Ejsmont/dp/0071843655)

## 🤝 Contribuindo

Este é um repositório de estudos. Sinta-se livre para:
- Adicionar novos exemplos
- Melhorar explicações
- Corrigir erros
- Sugerir novos tópicos

## 📝 Notas

- Todos os exemplos são funcionais e testados
- Código comentado em português para facilitar o aprendizado
- Foco em boas práticas e código limpo
- Cada conceito é explicado do zero, sem assumir conhecimento prévio

---

**Pronto para começar sua jornada para se tornar um desenvolvedor backend sênior? Comece pelo [Módulo 01](./01-fundamentos/teoria/README.md)!**
