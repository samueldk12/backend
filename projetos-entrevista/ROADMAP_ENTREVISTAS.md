# 🎯 Roadmap de Preparação para Entrevistas de Backend

> Guia completo para se preparar para entrevistas técnicas de engenheiro backend, do júnior ao sênior.

---

## 📚 Índice

1. [Visão Geral](#visão-geral)
2. [Como Pensar em Entrevistas](#como-pensar-em-entrevistas)
3. [Cronograma de Estudo](#cronograma-de-estudo)
4. [Por Tipo de Entrevista](#por-tipo-de-entrevista)
5. [Materiais de Estudo](#materiais-de-estudo)
6. [Checklist Final](#checklist-final)

---

## 🎓 Visão Geral

### Tipos de Entrevistas Técnicas

**1. Coding (Algoritmos e Estruturas de Dados)** - 40% das entrevistas
- LeetCode-style problems
- Complexidade: O(n), espaço
- Foco: Arrays, Strings, Hash Tables, Trees, Graphs

**2. System Design (Low-Level)** - 20% das entrevistas
- URL Shortener, LRU Cache, Rate Limiter
- Foco: Estruturas de dados, algoritmos aplicados

**3. System Design (High-Level)** - 30% das entrevistas
- Twitter, Uber, WhatsApp, Netflix
- Foco: Arquitetura, escalabilidade, trade-offs

**4. Behavioral** - 10% das entrevistas
- STAR method (Situation, Task, Action, Result)
- Liderança, resolução de conflitos, impacto

---

## 🧠 Como Pensar em Entrevistas

### Framework UMPIRE (Para Coding)

```
U - Understand (Entender o problema)
M - Match (Identificar padrão)
P - Plan (Planejar solução)
I - Implement (Implementar)
R - Review (Revisar edge cases)
E - Evaluate (Avaliar complexidade)
```

**Exemplo Prático:**

```
Problema: "Encontrar duplicatas em array"

U - Understand:
  ✓ Input: [1,2,3,2,4,5,1]
  ✓ Output: [1,2]
  ✓ Perguntas:
    - Array pode estar vazio? → Sim, retornar []
    - Números sempre positivos? → Sim
    - Ordenar output? → Não necessário

M - Match:
  ✓ Padrão: Hash Table (set)
  ✓ Problemas similares: Two Sum, Contains Duplicate

P - Plan:
  1. Criar set para elementos vistos
  2. Criar set para duplicatas
  3. Iterar array:
     - Se elemento em vistos → adicionar em duplicatas
     - Senão → adicionar em vistos
  4. Retornar list(duplicatas)

I - Implement:
  def find_duplicates(nums):
      seen = set()
      duplicates = set()

      for num in nums:
          if num in seen:
              duplicates.add(num)
          else:
              seen.add(num)

      return list(duplicates)

R - Review:
  ✓ Edge cases:
    - Array vazio → []
    - Sem duplicatas → []
    - Todos duplicados → [1,2,3,...]

E - Evaluate:
  ✓ Time: O(n) - iterar array uma vez
  ✓ Space: O(n) - sets podem ter até n elementos
```

---

### Framework SNAKE (Para System Design)

```
S - Scope (Definir escopo)
N - Numbers (Estimativas de escala)
A - Architecture (Desenhar arquitetura)
K - Key Components (Detalhar componentes críticos)
E - Extensions (Melhorias e trade-offs)
```

**Exemplo Prático:**

```
Problema: "Design do Twitter"

S - Scope (5 minutos):
  ✓ Clarificar requisitos:
    - Funcionalidades: Post tweets, Timeline, Follow
    - NÃO incluir: DMs, Trends, Ads
  ✓ Perguntar:
    - Quantos usuários?
    - Read-heavy ou write-heavy?
    - Consistência ou disponibilidade?

N - Numbers (5 minutos):
  ✓ Usuários: 500M ativos/mês, 150M ativos/dia
  ✓ Tweets: 200M/dia = 2.3k/s (write)
  ✓ Timeline views: 100B/dia = 1.1M/s (read)
  ✓ Ratio read/write: 500:1 (READ-HEAVY!)
  ✓ Storage: 200M tweets/dia * 300 bytes * 365 * 5 anos = 109TB

A - Architecture (10 minutos):
  ✓ Desenhar high-level:
    [Client] → [LB] → [API Servers]
                          ↓
      ┌───────────────────┼───────────────────┐
      ↓                   ↓                   ↓
    [User Service]  [Tweet Service]  [Timeline Service]
      ↓                   ↓                   ↓
    [PostgreSQL]      [Cassandra]          [Redis Cache]
    (users)           (tweets)             (timelines)

K - Key Components (20 minutos):
  ✓ Post Tweet:
    - Salvar em Cassandra
    - Fanout: Push para followers (se <5k) ou Pull (se >5k)

  ✓ Timeline:
    - Buscar tweets pré-computados (push)
    - Buscar tweets de celebridades (pull)
    - Merge + ordenar
    - Cache com Redis (5 min TTL)

  ✓ Database:
    - PostgreSQL: Users, Follows (relacional)
    - Cassandra: Tweets (alta escrita, time-series)

  ✓ Caching:
    - Timeline: Redis (5 min)
    - User profile: Redis (1 hora)

E - Extensions (10 minutos):
  ✓ Como escalar para 10x usuários?
    - Shard Cassandra por user_id
    - Multiple Redis clusters
    - CDN para static assets

  ✓ Como melhorar latência?
    - Edge servers (CloudFlare)
    - Prefetch next page
    - WebSocket para real-time

  ✓ Trade-offs:
    - Push vs Pull: Latência vs Storage
    - Cassandra vs PostgreSQL: Writes vs Queries
    - Strong vs Eventual consistency
```

---

## 📅 Cronograma de Estudo

### Plano de 8-12 Semanas (Fulltime Study)

#### **Semanas 1-2: Fundamentos (CRITICAL)**
**Objetivo:** Dominar estruturas de dados essenciais

- [ ] **Arrays & Strings** (3 dias)
  - Two pointers, sliding window
  - Problemas: Valid Palindrome, Longest Substring Without Repeating
  - LeetCode: 20 problemas easy/medium

- [ ] **Hash Tables** (2 dias)
  - Hashing, colisões, load factor
  - Problemas: Two Sum, Group Anagrams
  - LeetCode: 15 problemas

- [ ] **Linked Lists** (2 dias)
  - Reversal, fast/slow pointers, cycle detection
  - Problemas: Reverse Linked List, Detect Cycle
  - LeetCode: 10 problemas

**Meta:** 45 problemas resolvidos

---

#### **Semanas 3-4: Estruturas Intermediárias**
**Objetivo:** Stacks, Queues, Trees

- [ ] **Stacks & Queues** (2 dias)
  - Monotonic stack, deque
  - Problemas: Valid Parentheses, Min Stack
  - LeetCode: 15 problemas

- [ ] **Binary Trees** (3 dias)
  - DFS, BFS, recursion
  - Problemas: Max Depth, Invert Tree, Level Order
  - LeetCode: 20 problemas

- [ ] **Binary Search Trees** (2 dias)
  - BST properties, validation
  - Problemas: Validate BST, Kth Smallest
  - LeetCode: 10 problemas

**Meta:** 45 problemas (total: 90)

---

#### **Semanas 5-6: Algoritmos Avançados**
**Objetivo:** Graphs, Dynamic Programming

- [ ] **Graphs** (4 dias)
  - DFS, BFS, Dijkstra, Union-Find
  - Problemas: Number of Islands, Clone Graph
  - LeetCode: 20 problemas

- [ ] **Dynamic Programming** (3 dias)
  - Memoization, tabulation
  - Problemas: Climbing Stairs, Coin Change, LCS
  - LeetCode: 15 problemas

**Meta:** 35 problemas (total: 125)

---

#### **Semanas 7-8: System Design (Low-Level)**
**Objetivo:** Implementações práticas

- [ ] **Dia 1-2:** URL Shortener
  - Ler projeto 01
  - Implementar do zero
  - Adicionar features extras (analytics, custom URLs)

- [ ] **Dia 3-4:** LRU Cache
  - Ler projeto 03
  - Implementar HashMap + DLL
  - Adicionar LFU variant

- [ ] **Dia 5-6:** Rate Limiter
  - Ler projeto 02
  - Implementar Token Bucket
  - Adicionar Sliding Window

- [ ] **Dia 7:** Distributed Lock
  - Ler projeto 04
  - Implementar Redis lock

**Meta:** 4 projetos implementados

---

#### **Semanas 9-10: System Design (High-Level)**
**Objetivo:** Arquitetura de sistemas distribuídos

- [ ] **Dia 1-3:** Twitter Clone
  - Ler projeto 07
  - Desenhar arquitetura no papel
  - Praticar explicação verbal (gravar vídeo)

- [ ] **Dia 4-6:** Uber/Lyft
  - Ler projeto 08
  - Focar em geospatial indexing
  - Praticar matching algorithm

- [ ] **Dia 7-9:** WhatsApp
  - Ler projeto 09
  - WebSocket connection management
  - Message delivery guarantees

- [ ] **Dia 10-12:** Netflix/Instagram (escolher 1)
  - Ler projeto 10 ou 12
  - CDN strategy
  - Praticar end-to-end design

**Meta:** 4 system designs dominados

---

#### **Semanas 11-12: Mock Interviews & Revisão**

- [ ] **Semana 11:**
  - 5 mock coding interviews (LeetCode/Pramp)
  - 2 mock system design (Exponent.com)
  - Revisar problemas errados

- [ ] **Semana 12:**
  - Revisar todos os 12 projetos de entrevista
  - Praticar explicações em voz alta
  - Ler BEST_PRACTICES.md e FAQ.md
  - Descansar 2 dias antes da entrevista

**Meta:** 10+ mock interviews

---

## 🎯 Por Tipo de Entrevista

### 1️⃣ Coding Interview (Algoritmos)

#### **Como Abordar**

1. **Escute o problema todo** antes de começar
2. **Faça perguntas clarificadoras:**
   - Input constraints (tamanho, valores negativos, duplicatas?)
   - Output format (ordenado? unique?)
   - Edge cases (empty input?)
3. **Pense em voz alta** - interviewer quer ver seu raciocínio
4. **Comece com solução brute force** - sempre funciona!
5. **Otimize depois** - discuta trade-offs
6. **Teste com exemplos** - incluindo edge cases

#### **Padrões Mais Comuns (80% dos problemas)**

| Padrão | Quando Usar | Complexidade | Exemplo |
|--------|-------------|--------------|---------|
| **Two Pointers** | Array ordenado, palindrome | O(n) | Valid Palindrome |
| **Sliding Window** | Substring, subarray contíguo | O(n) | Longest Substring |
| **Hash Table** | Lookup rápido, contagem | O(n) | Two Sum |
| **Binary Search** | Array ordenado, busca | O(log n) | Search Insert Position |
| **BFS/DFS** | Tree, graph traversal | O(V+E) | Binary Tree Level Order |
| **Dynamic Programming** | Otimização, combinações | O(n²) | Coin Change |
| **Backtracking** | Permutações, combinações | O(2ⁿ) | Subsets |

#### **Template: Two Pointers**

```python
def two_pointers_pattern(arr):
    """
    Use quando: Array ordenado, encontrar par
    Complexidade: O(n)
    """
    left, right = 0, len(arr) - 1

    while left < right:
        current = arr[left] + arr[right]

        if current == target:
            return [left, right]
        elif current < target:
            left += 1  # Precisa de soma maior
        else:
            right -= 1  # Precisa de soma menor

    return None
```

#### **Template: Sliding Window**

```python
def sliding_window_pattern(s):
    """
    Use quando: Substring/subarray contíguo
    Complexidade: O(n)
    """
    window_start = 0
    max_length = 0
    char_frequency = {}

    for window_end in range(len(s)):
        # Adicionar char ao window
        right_char = s[window_end]
        char_frequency[right_char] = char_frequency.get(right_char, 0) + 1

        # Shrink window se necessário
        while len(char_frequency) > k:  # Exemplo: max k chars únicos
            left_char = s[window_start]
            char_frequency[left_char] -= 1
            if char_frequency[left_char] == 0:
                del char_frequency[left_char]
            window_start += 1

        max_length = max(max_length, window_end - window_start + 1)

    return max_length
```

---

### 2️⃣ System Design (Low-Level)

#### **Como Abordar**

1. **Entenda requisitos funcionais**
   - O que o sistema deve fazer?
   - Quais operações são críticas?

2. **Defina API/Interface**
   ```python
   class URLShortener:
       def shorten(url: str) -> str: pass
       def expand(short_url: str) -> str: pass
   ```

3. **Escolha estruturas de dados**
   - HashMap? Array? Tree? Graph?
   - Justifique escolha (complexidade)

4. **Implemente funcionalidade core**
   - Código limpo e testável
   - Handle edge cases

5. **Otimize**
   - Cache? Batch processing?
   - Discuta trade-offs

#### **Projetos Essenciais (Prioridade)**

| Projeto | Frequência | Conceitos-Chave | Tempo Estudo |
|---------|-----------|-----------------|--------------|
| **LRU Cache** | ⭐⭐⭐⭐⭐ | HashMap + DLL, O(1) ops | 4 horas |
| **URL Shortener** | ⭐⭐⭐⭐⭐ | Hashing, Base62, Sharding | 4 horas |
| **Rate Limiter** | ⭐⭐⭐⭐ | Token Bucket, Redis, Lua | 3 horas |
| **Distributed Lock** | ⭐⭐⭐⭐ | Redis, Atomicity, TTL | 3 horas |
| **Consistent Hashing** | ⭐⭐⭐ | Geohash, Virtual Nodes | 3 horas |
| **Bloom Filter** | ⭐⭐⭐ | Bit Array, Hash Functions | 2 horas |

**Total:** ~20 horas para dominar todos

---

### 3️⃣ System Design (High-Level)

#### **Como Abordar (Framework SNAKE)**

**S - Scope (5 min)**
- Clarificar requisitos funcionais
- Definir o que NÃO fazer
- Perguntar sobre scale, latência, consistência

**N - Numbers (5 min)**
- Quantos usuários? (DAU, MAU)
- Requests/segundo (read vs write)
- Storage necessário (5 anos)
- Bandwidth (GB/s)

**A - Architecture (10 min)**
- Desenhar high-level diagram
- Clients → Load Balancer → Services → Databases
- Identificar gargalos

**K - Key Components (20 min)**
- Detalhar 2-3 componentes críticos
- APIs, schemas, algoritmos
- Caching, sharding, replication

**E - Extensions (10 min)**
- Como escalar 10x?
- Melhorias (search, analytics, ML)
- Trade-offs e bottlenecks

#### **Arquiteturas Essenciais**

| Sistema | Padrão | Conceito-Chave | Projeto |
|---------|--------|----------------|---------|
| **Twitter** | Fanout | Hybrid Push/Pull | #07 |
| **Uber** | Geospatial | Geohash, Matching | #08 |
| **WhatsApp** | Real-time | WebSocket, Pub/Sub | #09 |
| **Netflix** | Streaming | CDN, Adaptive Bitrate | #10 |
| **Airbnb** | Booking | ACID, Distributed Lock | #11 |
| **Instagram** | Feed | ML Ranking, Batch Writes | #12 |

#### **Building Blocks Essenciais**

1. **Load Balancing**
   - Round robin, least connections, consistent hashing
   - Layer 4 (TCP) vs Layer 7 (HTTP)

2. **Caching**
   - Redis, Memcached
   - Cache-aside, write-through, write-behind
   - Eviction: LRU, LFU, TTL

3. **Database**
   - SQL: PostgreSQL, MySQL (ACID, relations)
   - NoSQL: Cassandra, MongoDB (scale, flexibility)
   - Sharding: Horizontal partitioning
   - Replication: Master-slave, multi-master

4. **Message Queue**
   - Kafka, RabbitMQ, SQS
   - Pub/Sub, fanout, retry logic
   - At-least-once vs exactly-once

5. **CDN**
   - CloudFront, Akamai, CloudFlare
   - Edge locations, cache invalidation
   - 95% traffic reduction

---

## 📖 Materiais de Estudo

### Livros Essenciais

**1. Algoritmos & Estruturas de Dados**
- 📘 **"Cracking the Coding Interview"** - Gayle Laakmann McDowell
  - Tempo: 40 horas
  - Focar: Capítulos 1-10 (Arrays até Graphs)
  - ⭐ Rating: 5/5 - MUST READ

- 📗 **"Elements of Programming Interviews in Python"** - Aziz, Lee, Prakash
  - Tempo: 30 horas
  - Focar: Problemas medium/hard
  - ⭐ Rating: 4.5/5

**2. System Design**
- 📙 **"Designing Data-Intensive Applications"** - Martin Kleppmann
  - Tempo: 60 horas
  - Focar: Capítulos 2-6 (Replication, Partitioning, Transactions)
  - ⭐ Rating: 5/5 - BIBLE

- 📕 **"System Design Interview Vol 1 & 2"** - Alex Xu
  - Tempo: 20 horas cada
  - Focar: Todos os 15 designs
  - ⭐ Rating: 5/5 - Específico para entrevistas

**3. Backend Engineering**
- 📗 **"Web Scalability for Startup Engineers"** - Artur Ejsmont
  - Tempo: 15 horas
  - Focar: Caching, Database, Load Balancing
  - ⭐ Rating: 4/5

---

### Plataformas Online

#### **Coding Practice**

**LeetCode** (⭐⭐⭐⭐⭐)
- URL: leetcode.com
- Plano: Premium ($35/mês) vale a pena
- Estratégia:
  - 150 problemas essenciais: [Blind 75](https://leetcode.com/discuss/general-discussion/460599/blind-75-leetcode-questions)
  - Ordenar por "Acceptance Rate" (começar com high)
  - Focar em medium (70% dos problemas)

**Padrão de Estudo:**
```
Dia típico:
- 2 easy (warm-up) - 30 min
- 2 medium (core) - 90 min
- 1 hard (stretch) - 60 min

Total: 3 horas/dia = ~150 problemas em 6 semanas
```

**HackerRank** (⭐⭐⭐⭐)
- URL: hackerrank.com
- Bom para: Interview Preparation Kit
- Menos problemas de system design

**AlgoExpert** (⭐⭐⭐⭐)
- URL: algoexpert.io
- $99 one-time
- Vídeos explicativos excelentes
- 160 problemas curados

#### **System Design Practice**

**Exponent** (⭐⭐⭐⭐⭐)
- URL: tryexponent.com
- $50/mês
- Mock interviews com feedback
- System design frameworks

**Pramp** (⭐⭐⭐⭐)
- URL: pramp.com
- FREE peer-to-peer mock interviews
- Practice com outros candidatos

**SystemDesignPrimer** (⭐⭐⭐⭐⭐)
- URL: github.com/donnemartin/system-design-primer
- FREE, open source
- Anki flashcards inclusos

---

### Vídeos & Cursos

**YouTube Channels:**

1. **NeetCode** (⭐⭐⭐⭐⭐)
   - URL: youtube.com/@NeetCode
   - 400+ LeetCode solutions com explicações claras
   - Roadmap estruturado

2. **Gaurav Sen** (⭐⭐⭐⭐⭐)
   - URL: youtube.com/@gkcs
   - System design: Uber, WhatsApp, Netflix
   - Clareza excepcional

3. **ByteByteGo** (⭐⭐⭐⭐)
   - URL: youtube.com/@ByteByteGo
   - System design com animações
   - Newsletter excelente

4. **Tech Dummies** (⭐⭐⭐⭐)
   - URL: youtube.com/@TechDummiesNarendraL
   - System design em português!
   - Uber, Twitter, Instagram

**Cursos Pagos:**

1. **Grokking the Coding Interview** ($79)
   - URL: educative.io
   - 16 padrões de coding
   - 125+ problemas

2. **Grokking the System Design Interview** ($79)
   - URL: educative.io
   - 12 system designs completos
   - Diagramas interativos

---

### Recursos Adicionais

**GitHub Repositories:**

1. **Tech Interview Handbook**
   - URL: github.com/yangshun/tech-interview-handbook
   - Resume tips, negotiation, behavioral

2. **Coding Interview University**
   - URL: github.com/jwasham/coding-interview-university
   - Roadmap completo (6 meses)

3. **Awesome System Design**
   - URL: github.com/madd86/awesome-system-design
   - Curated list de recursos

**Blogs:**

1. **High Scalability** (highscalability.com)
   - Case studies: Netflix, Instagram, Uber
   - Arquitetura de sistemas reais

2. **Martin Fowler** (martinfowler.com)
   - Patterns, refactoring, architecture
   - Artigos densos mas valiosos

3. **Engineering Blogs:**
   - Netflix Tech Blog (netflixtechblog.com)
   - Uber Engineering (eng.uber.com)
   - Instagram Engineering (instagram-engineering.com)

---

## ✅ Checklist Final (1 Semana Antes)

### 📝 Conhecimento Técnico

**Algoritmos & Estruturas de Dados:**
- [ ] Posso explicar Big O (tempo e espaço)?
- [ ] Domino os 7 padrões principais?
- [ ] Resolvi 150+ problemas no LeetCode?
- [ ] Consigo codificar sem IDE (whiteboard)?

**System Design (Low-Level):**
- [ ] Implementei LRU Cache do zero?
- [ ] Entendo Consistent Hashing?
- [ ] Sei quando usar Redis vs PostgreSQL?
- [ ] Consigo explicar trade-offs de cada solução?

**System Design (High-Level):**
- [ ] Estudei os 6 projetos principais?
- [ ] Consigo estimar QPS, storage, bandwidth?
- [ ] Sei desenhar arquitetura em 10 minutos?
- [ ] Entendo trade-offs: latency vs consistency?

**Backend Fundamentals:**
- [ ] HTTP/REST, WebSocket, gRPC
- [ ] Database: ACID, CAP theorem, sharding
- [ ] Caching: Redis patterns, eviction policies
- [ ] Message Queues: Kafka, pub/sub
- [ ] Security: OAuth, JWT, rate limiting

---

### 🎤 Soft Skills

**Comunicação:**
- [ ] Pratico pensar em voz alta?
- [ ] Explico complexidade de forma clara?
- [ ] Faço perguntas clarificadoras?
- [ ] Sei quando pedir hint?

**Problem Solving:**
- [ ] Começo com brute force?
- [ ] Otimizo após solução funcionar?
- [ ] Testo com edge cases?
- [ ] Discuto trade-offs?

**Behavioral:**
- [ ] Preparei 5 histórias STAR?
- [ ] Cubro: conflito, liderança, falha, sucesso
- [ ] Tenho perguntas para fazer ao interviewer?

---

### 🛠️ Logística

**Setup:**
- [ ] Testar câmera e microfone
- [ ] Ambiente silencioso e iluminado
- [ ] Internet estável (backup: mobile hotspot)
- [ ] Whiteboard ou papel + caneta
- [ ] Copo de água, café

**Plataformas:**
- [ ] Conta no CoderPad/HackerRank criada
- [ ] Familiarizado com interface
- [ ] Sei como rodar código e ver output

**Timing:**
- [ ] Revisar calendário (fuso horário correto?)
- [ ] Entrar 5 minutos antes
- [ ] Alocar 15 min buffer após (pode estender)

---

## 🎯 Estratégia Por Nível

### Junior (0-2 anos)

**Foco: Coding (70%) + System Design Low-Level (30%)**

**Coding:**
- 100 problemas easy/medium
- Dominar: Arrays, Strings, Hash Tables, Trees
- Não precisa: Graphs complexos, DP hard

**System Design:**
- LRU Cache (must!)
- URL Shortener
- Rate Limiter básico

**Timeline:** 6-8 semanas

---

### Mid-Level (3-5 anos)

**Foco: Coding (50%) + System Design (50%)**

**Coding:**
- 150 problemas (incluindo hard)
- Dominar: Todos os 7 padrões
- Graphs, DP, Backtracking

**System Design:**
- Low-level: Todos os 6 projetos
- High-level: 3-4 projetos (Twitter, Uber, WhatsApp)

**Timeline:** 8-10 semanas

---

### Senior (5+ anos)

**Foco: System Design (70%) + Coding (30%)**

**Coding:**
- Manter sharp (50 problemas revisão)
- Focar em hard problems
- Otimizações avançadas

**System Design:**
- Todos os 12 projetos
- Deep dive: Scalability, trade-offs
- Preparar para design aberto ("design X from scratch")

**Behavioral:**
- Liderança técnica
- Mentorar juniors
- Decisões de arquitetura

**Timeline:** 10-12 semanas

---

## 🚀 Dicas de Ouro

### Durante Coding Interview

1. **Não fique preso em silêncio**
   - "Hmm, estou pensando em usar hash table aqui..."
   - Interviewer quer ver seu raciocínio

2. **Peça hints se travar 5+ minutos**
   - "Estou pensando em X, mas não consigo otimizar. Alguma dica?"
   - Melhor pedir hint que perder tempo

3. **Teste antes de dizer "done"**
   - Walk through com exemplo
   - Edge cases: empty, single element, duplicates

4. **Discuta otimizações mesmo que não implemente**
   - "Poderíamos usar binary search para O(log n), mas aumentaria complexidade de código"

---

### Durante System Design

1. **SEMPRE comece com perguntas**
   - "Quantos usuários?"
   - "Read-heavy ou write-heavy?"
   - "Latência mais importante que consistência?"

2. **Desenhe primeiro, detalhe depois**
   - High-level architecture em 5 minutos
   - Detalhar apenas o que interviewer pedir

3. **Use números realistas**
   - Twitter: 300M users (não 1 trillion!)
   - QPS: milhares a milhões (não bilhões)

4. **Sempre mencione trade-offs**
   - "Cassandra escala melhor, mas PostgreSQL tem joins"
   - "Cache-aside é mais simples, write-through é mais consistente"

---

### Erros Comuns (EVITE!)

❌ **Começar a codar imediatamente**
→ ✅ Entenda o problema primeiro

❌ **Solução perfeita de primeira**
→ ✅ Brute force → Otimizar

❌ **Silêncio enquanto pensa**
→ ✅ Pensar em voz alta

❌ **Desistir quando travar**
→ ✅ Pedir hint após 5 min

❌ **Ignorar edge cases**
→ ✅ Testar: empty, null, duplicates

❌ **Overengineer system design**
→ ✅ Começar simples, adicionar complexidade quando necessário

---

## 📚 Resumo Executivo

### Se você tem apenas 4 semanas:

**Semana 1:** Coding - Arrays, Strings, Hash Tables (40 problemas)
**Semana 2:** Coding - Trees, Graphs (30 problemas) + LRU Cache
**Semana 3:** System Design - Twitter, Uber, URL Shortener
**Semana 4:** Mock interviews + revisão

### Se você tem apenas 1 semana:

**Dia 1-2:** Revisar Blind 75 (problemas que você já fez)
**Dia 3:** LRU Cache + URL Shortener (implementar)
**Dia 4:** Twitter System Design (estudar e explicar)
**Dia 5:** 2 mock interviews
**Dia 6:** Revisar erros dos mocks
**Dia 7:** Descansar!

---

## 🎓 Palavras Finais

> "Entrevistas técnicas são uma skill separada de engenharia. Você pode ser excelente engenheiro e falhar em entrevistas se não praticar."

**Lembre-se:**
- Comunicação > Solução perfeita
- Processo > Resposta certa
- Aprendizado > Frustração

**Você consegue! 💪**

Bons estudos e boa sorte nas entrevistas! 🚀
