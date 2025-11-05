# 08 - Estruturas de Dados Aplicadas ao Backend

## Índice

1. [Hash Tables](#hash-tables)
2. [Trees](#trees)
3. [Graphs](#graphs)
4. [Heaps](#heaps)
5. [Tries](#tries)

---

## Hash Tables

### Aplicações em Backend

**1. Cache (Redis)**
```python
# O(1) lookup
cache = {}
cache['user:123'] = user_data  # O(1)
user = cache.get('user:123')    # O(1)
```

**2. Database Indexes (Hash Index)**
```sql
CREATE INDEX idx_email USING HASH ON users(email);
-- WHERE email = 'joao@example.com'  → O(1)
-- WHERE email LIKE 'joao%'          → Não funciona com hash!
```

**3. Session Storage**
```python
sessions = {}

def create_session(user_id):
    session_id = generate_token()
    sessions[session_id] = {
        'user_id': user_id,
        'created_at': time.time()
    }
    return session_id

def get_session(session_id):
    return sessions.get(session_id)  # O(1)
```

---

## Trees

### B-Tree (Database Indexes)

```
B-Tree = Balanced tree otimizada para disco

         [50]
        /    \
   [20, 30]  [70, 90]
   /  |  \    /  |  \
 [10][25][40][60][80][95]

• Cada node = 1 disk block
• Busca = O(log N) disk reads
• Range query eficiente
```

**SQL Index (B-Tree)**
```sql
CREATE INDEX idx_created_at ON posts(created_at);

-- Range query rápida
SELECT * FROM posts
WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31'
ORDER BY created_at;
-- Index scan → O(log N + K) onde K = resultados
```

### LSM Tree (Log-Structured Merge Tree)

```
Usado em: Cassandra, RocksDB, LevelDB

Write:
1. Append to Write-Ahead Log (disk) → O(1)
2. Insert in MemTable (RAM)         → O(log N)

Read:
1. Check MemTable
2. Check SSTables (disk) em camadas

• Write otimizado: O(1) append
• Read: usa Bloom Filter
```

---

## Graphs

### Social Network (Adjacency List)

```python
# Grafo = Users e Friendships
graph = {
    'alice': ['bob', 'charlie'],
    'bob': ['alice', 'david'],
    'charlie': ['alice'],
    'david': ['bob']
}

# BFS: Amigos de amigos (2 graus)
from collections import deque

def friends_of_friends(user):
    visited = set([user])
    queue = deque([(user, 0)])  # (user, distance)
    fof = []

    while queue:
        current, dist = queue.popleft()

        if dist == 2:
            fof.append(current)
            continue

        for friend in graph.get(current, []):
            if friend not in visited:
                visited.add(friend)
                queue.append((friend, dist + 1))

    return fof

# friends_of_friends('alice')
# → ['david'] (alice → bob → david)
```

### Shortest Path (Dijkstra)

```python
import heapq

def shortest_path(graph, start, end):
    """
    Aplicação: Roteamento, Maps, Network routing
    """
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    pq = [(0, start)]  # (distance, node)

    while pq:
        curr_dist, curr = heapq.heappop(pq)

        if curr == end:
            return curr_dist

        if curr_dist > distances[curr]:
            continue

        for neighbor, weight in graph[curr]:
            distance = curr_dist + weight

            if distance < distances[neighbor]:
                distances[neighbor] = distance
                heapq.heappush(pq, (distance, neighbor))

    return float('inf')

# Grafo ponderado (distância entre cidades)
graph = {
    'A': [('B', 5), ('C', 3)],
    'B': [('D', 2)],
    'C': [('D', 6)],
    'D': []
}

# shortest_path(graph, 'A', 'D') → 7 (A→B→D)
```

---

## Heaps

### Priority Queue (Task Scheduling)

```python
import heapq

class TaskScheduler:
    def __init__(self):
        self.tasks = []  # Min heap

    def add_task(self, priority, task):
        """Menor priority = mais urgente"""
        heapq.heappush(self.tasks, (priority, task))

    def get_next_task(self):
        """O(log N)"""
        if self.tasks:
            return heapq.heappop(self.tasks)[1]
        return None

# Uso em Celery
scheduler = TaskScheduler()

scheduler.add_task(priority=1, task="enviar_email_urgente")
scheduler.add_task(priority=5, task="gerar_relatorio")
scheduler.add_task(priority=2, task="processar_pagamento")

# Worker processa em ordem de prioridade
task = scheduler.get_next_task()  # enviar_email_urgente
```

### Top K Elements

```python
def top_k_expensive_orders(orders, k):
    """
    Encontrar K pedidos mais caros
    Heap mais eficiente que sorting
    """
    # Min heap com tamanho K
    heap = []

    for order in orders:
        if len(heap) < k:
            heapq.heappush(heap, (order.price, order))
        elif order.price > heap[0][0]:
            heapq.heapreplace(heap, (order.price, order))

    return [order for price, order in heap]

# O(N log K) vs O(N log N) do sorting
```

---

## Tries

### Autocomplete

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        """O(M) onde M = tamanho da palavra"""
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True

    def search_prefix(self, prefix):
        """Busca palavras com prefixo"""
        node = self.root

        # Navega até prefixo
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]

        # Coleta todas palavras a partir do prefixo
        results = []
        self._collect_words(node, prefix, results)
        return results

    def _collect_words(self, node, prefix, results):
        if node.is_end:
            results.append(prefix)

        for char, child in node.children.items():
            self._collect_words(child, prefix + char, results)

# Aplicação: Search autocomplete
trie = Trie()
products = ["apple", "application", "append", "banana", "band"]

for product in products:
    trie.insert(product)

# Busca: "app"
trie.search_prefix("app")
# → ["apple", "application", "append"]

# O(M + K) onde M = prefixo, K = resultados
# Muito mais rápido que varrer array: O(N * M)
```

### IP Routing (Longest Prefix Match)

```python
class IPTrie:
    """Roteamento de pacotes IP"""
    def __init__(self):
        self.root = {'children': {}, 'route': None}

    def add_route(self, cidr, next_hop):
        """
        Adiciona rota: 192.168.1.0/24 → router1
        """
        ip, prefix_len = cidr.split('/')
        prefix_len = int(prefix_len)

        # Converte IP para bits
        bits = ''.join(format(int(octet), '08b') for octet in ip.split('.'))

        node = self.root
        for i in range(prefix_len):
            bit = bits[i]
            if bit not in node['children']:
                node['children'][bit] = {'children': {}, 'route': None}
            node = node['children'][bit]

        node['route'] = next_hop

    def lookup(self, ip):
        """Longest prefix match para IP"""
        bits = ''.join(format(int(octet), '08b') for octet in ip.split('.'))

        node = self.root
        best_route = node['route']

        for bit in bits:
            if bit not in node['children']:
                break
            node = node['children'][bit]
            if node['route']:
                best_route = node['route']

        return best_route

# Uso
router = IPTrie()
router.add_route('192.168.0.0/16', 'router1')
router.add_route('192.168.1.0/24', 'router2')

router.lookup('192.168.1.50')   # → router2 (mais específico)
router.lookup('192.168.2.50')   # → router1
```

---

## Resumo de Complexidades

| Estrutura | Busca | Inserção | Deleção | Uso em Backend |
|-----------|-------|----------|---------|----------------|
| Hash Table | O(1) | O(1) | O(1) | Cache, Sessions, Indexes |
| B-Tree | O(log N) | O(log N) | O(log N) | DB Indexes (disk) |
| Heap | O(1) min | O(log N) | O(log N) | Priority Queue, Top-K |
| Trie | O(M) | O(M) | O(M) | Autocomplete, IP Routing |
| Graph | O(V+E) | O(1) | O(1) | Social, Maps, Dependencies |

**M** = tamanho da string
**V** = vertices, **E** = edges

---

## Fim dos Módulos Teóricos

✅ Módulos teóricos completos!

➡️ Próximo: [Exercícios Práticos](../projeto-pratico/)
