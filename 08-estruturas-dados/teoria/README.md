# 🗂️ Módulo 08: Estruturas de Dados Aplicadas ao Backend

> Como estruturas de dados fundamentais são usadas em sistemas reais de backend

---

## 📚 Índice

1. [Por que Estruturas de Dados no Backend?](#por-que-estruturas-de-dados-no-backend)
2. [Arrays e Listas](#arrays-e-listas)
3. [Hash Tables (Dicionários)](#hash-tables)
4. [Árvores](#árvores)
5. [Grafos](#grafos)
6. [Heaps](#heaps)
7. [Tries](#tries)
8. [Estruturas Especializadas](#estruturas-especializadas)

---

## 🎯 Por que Estruturas de Dados no Backend?

### Problema Real

```python
# ❌ Código ineficiente (O(n²))
def get_users_with_posts(user_ids):
    users = []
    for user_id in user_ids:
        user = db.query(User).filter(User.id == user_id).first()  # Query por iteração!
        posts = db.query(Post).filter(Post.user_id == user_id).all()  # Outra query!
        user.posts = posts
        users.append(user)
    return users

# ✅ Código otimizado (O(n))
def get_users_with_posts(user_ids):
    # Buscar tudo de uma vez
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    posts = db.query(Post).filter(Post.user_id.in_(user_ids)).all()

    # Agrupar posts por user_id (Hash Table!)
    posts_by_user = defaultdict(list)
    for post in posts:
        posts_by_user[post.user_id].append(post)

    # Associar
    for user in users:
        user.posts = posts_by_user[user.id]

    return users
```

**Resultado:** 100 users:
- ❌ Versão 1: 201 queries (1 + 100 + 100) = ~500ms
- ✅ Versão 2: 2 queries = ~10ms

**50x mais rápido!**

---

## 📦 Arrays e Listas

### Quando Usar

| Estrutura | Use Quando | Evite Quando | Complexidade |
|-----------|-----------|--------------|--------------|
| **List (Python)** | Acesso por índice, append | Insert no meio | Get: O(1), Insert: O(n) |
| **Deque** | Queue, push/pop nas pontas | Acesso por índice | Push/Pop: O(1) |
| **Array (NumPy)** | Operações matemáticas | Tamanho variável | Operações: O(1) |

### Aplicação 1: Pagination Cursor

```python
# ❌ ERRADO: Offset pagination (lento para páginas grandes)
@app.get("/posts")
def get_posts(page: int = 1, per_page: int = 20):
    offset = (page - 1) * per_page
    posts = db.query(Post).offset(offset).limit(per_page).all()  # O(n) scan!
    return posts

# Problema: Página 10000 → offset 200000 → scan 200k rows!


# ✅ CORRETO: Cursor-based pagination
@app.get("/posts")
def get_posts(cursor: int = None, per_page: int = 20):
    query = db.query(Post).order_by(Post.id.desc())

    if cursor:
        query = query.filter(Post.id < cursor)  # Index scan! O(log n)

    posts = query.limit(per_page).all()

    next_cursor = posts[-1].id if posts else None

    return {
        "posts": posts,
        "next_cursor": next_cursor
    }

# Sempre O(log n) + O(k) onde k = per_page
```

**Ganho:** Página 1 e página 10000 têm mesma performance!

### Aplicação 2: Rate Limiting com Sliding Window

```python
from collections import deque
import time

class RateLimiter:
    """
    Rate limiting com deque (queue de timestamps)

    Sliding window: Conta requests nos últimos N segundos
    """
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = deque()  # [(timestamp1, timestamp2, ...)]

    def allow_request(self) -> bool:
        now = time.time()

        # Remover requests fora do window (mais antigos que N segundos)
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()  # O(1) com deque!

        # Verificar se excedeu limite
        if len(self.requests) >= self.max_requests:
            return False

        # Adicionar request atual
        self.requests.append(now)
        return True


# Uso
limiter = RateLimiter(max_requests=100, window_seconds=60)

@app.post("/api/action")
def action():
    if not limiter.allow_request():
        raise HTTPException(429, "Too many requests")

    # Processar...
    return {"status": "ok"}
```

**Por que deque?**
- `popleft()` é O(1) (vs O(n) em list)
- `append()` é O(1)
- Perfeito para queues!

---

## 🗝️ Hash Tables

### Quando Usar

**Use Hash Table quando precisar:**
- ✅ Lookup rápido (O(1))
- ✅ Agrupar dados por chave
- ✅ Eliminar duplicatas
- ✅ Cache

### Aplicação 1: Resolver N+1 Problem

```python
# ❌ N+1 Problem (disaster!)
posts = db.query(Post).limit(100).all()

for post in posts:
    author = db.query(User).filter(User.id == post.user_id).first()  # 100 queries!
    print(f"{post.title} by {author.name}")

# 101 queries total!


# ✅ Solução 1: Eager loading (SQLAlchemy)
from sqlalchemy.orm import joinedload

posts = db.query(Post).options(joinedload(Post.author)).limit(100).all()

for post in posts:
    print(f"{post.title} by {post.author.name}")

# 1 query com JOIN!


# ✅ Solução 2: Manual com Hash Table
posts = db.query(Post).limit(100).all()
user_ids = [post.user_id for post in posts]

# Buscar todos users de uma vez
users = db.query(User).filter(User.id.in_(user_ids)).all()

# Criar hash table: user_id -> User
users_by_id = {user.id: user for user in users}  # O(n)

# Associar
for post in posts:
    author = users_by_id[post.user_id]  # O(1) lookup!
    print(f"{post.title} by {author.name}")

# 2 queries total!
```

### Aplicação 2: Cache de Queries

```python
from functools import lru_cache
from typing import Optional

class UserService:
    """
    Service com cache em memória (Hash Table)

    LRU Cache = Hash Table + Doubly Linked List
    """

    @lru_cache(maxsize=1000)  # Cache de 1000 users
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Cache em memória

        Primeira chamada: O(n) DB query
        Chamadas seguintes: O(1) hash lookup
        """
        return db.query(User).filter(User.id == user_id).first()

    @lru_cache(maxsize=1000)
    def get_user_by_email(self, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()


# Uso
service = UserService()

user1 = service.get_user_by_id(123)  # DB query
user2 = service.get_user_by_id(123)  # Cache hit! (instantâneo)
```

### Aplicação 3: Contar Frequências

```python
from collections import Counter, defaultdict

def get_popular_hashtags(tweets: List[Tweet], top_n: int = 10):
    """
    Encontrar hashtags mais usadas

    Usando Counter (Hash Table especializada)
    """
    hashtag_counter = Counter()  # defaultdict(int)

    for tweet in tweets:
        hashtags = extract_hashtags(tweet.content)

        for tag in hashtags:
            hashtag_counter[tag] += 1  # O(1)

    # Retornar top N
    return hashtag_counter.most_common(top_n)


# Exemplo
tweets = get_recent_tweets(limit=10000)
popular = get_popular_hashtags(tweets, top_n=10)

# Output: [('#python', 543), ('#coding', 421), ...]
```

### Aplicação 4: Grouping com defaultdict

```python
from collections import defaultdict

def group_posts_by_category(posts: List[Post]):
    """
    Agrupar posts por categoria

    defaultdict evita KeyError
    """
    posts_by_category = defaultdict(list)  # Hash Table com default []

    for post in posts:
        posts_by_category[post.category].append(post)  # O(1)

    return dict(posts_by_category)


# Uso
posts = db.query(Post).all()
grouped = group_posts_by_category(posts)

# Output:
# {
#   'tech': [Post1, Post2, ...],
#   'sports': [Post3, Post4, ...],
#   ...
# }
```

---

## 🌲 Árvores

### Quando Usar

**Use Árvore quando precisar:**
- ✅ Range queries (todos valores entre X e Y)
- ✅ Dados hierárquicos (categorias, org chart)
- ✅ Busca ordenada
- ✅ Prefix matching

### Aplicação 1: Categorias (Árvore N-ária)

```python
class Category:
    """
    Categoria com hierarquia

    E-commerce:
    Eletrônicos
      ├── Computadores
      │   ├── Notebooks
      │   └── Desktops
      └── Celulares
          ├── iPhone
          └── Android
    """
    id: int
    name: str
    parent_id: Optional[int]
    children: List['Category'] = []


def build_category_tree(categories: List[Category]) -> List[Category]:
    """
    Construir árvore de categorias

    Input: Lista flat de categorias
    Output: Árvore hierárquica
    """
    # Hash table para lookup rápido
    category_map = {cat.id: cat for cat in categories}

    root_categories = []

    for category in categories:
        if category.parent_id is None:
            # Root category
            root_categories.append(category)
        else:
            # Adicionar como filho do pai
            parent = category_map[category.parent_id]
            parent.children.append(category)

    return root_categories


def get_all_descendants(category: Category) -> List[Category]:
    """
    Buscar todos descendentes (DFS)

    Útil para: "Buscar todos produtos em Eletrônicos (incluindo subcategorias)"
    """
    descendants = []

    def dfs(cat: Category):
        descendants.append(cat)
        for child in cat.children:
            dfs(child)

    dfs(category)
    return descendants


# Uso
@app.get("/categories/{category_id}/products")
def get_products_in_category(category_id: int, include_subcategories: bool = True):
    category = get_category(category_id)

    if include_subcategories:
        # Buscar em toda subárvore
        categories = get_all_descendants(category)
        category_ids = [cat.id for cat in categories]
    else:
        category_ids = [category_id]

    # Buscar produtos
    products = db.query(Product).filter(
        Product.category_id.in_(category_ids)
    ).all()

    return products
```

### Aplicação 2: Comments Tree (Nested Comments)

```python
class Comment:
    """
    Comentário com replies (árore N-ária)

    Reddit-style:
    Comment 1
      ├── Reply 1.1
      │   └── Reply 1.1.1
      └── Reply 1.2
    Comment 2
      └── Reply 2.1
    """
    id: int
    content: str
    parent_id: Optional[int]
    replies: List['Comment'] = []


def build_comment_tree(comments: List[Comment]) -> List[Comment]:
    """
    Construir árvore de comentários

    Mesmo algoritmo de categorias!
    """
    comment_map = {c.id: c for c in comments}
    root_comments = []

    for comment in comments:
        if comment.parent_id is None:
            root_comments.append(comment)
        else:
            parent = comment_map.get(comment.parent_id)
            if parent:
                parent.replies.append(comment)

    return root_comments


def render_comment_tree(comment: Comment, depth: int = 0):
    """
    Renderizar árvore (DFS pré-order)
    """
    indent = "  " * depth
    print(f"{indent}├── {comment.content}")

    for reply in comment.replies:
        render_comment_tree(reply, depth + 1)


# Uso
@app.get("/posts/{post_id}/comments")
def get_comments(post_id: int):
    # Buscar todos comments de uma vez
    comments = db.query(Comment).filter(Comment.post_id == post_id).all()

    # Construir árvore
    comment_tree = build_comment_tree(comments)

    return comment_tree
```

### Aplicação 3: Range Queries com B-Tree (Database Index)

```python
"""
Índices de banco de dados usam B-Tree!

B-Tree permite:
- Range queries eficientes: SELECT * WHERE age BETWEEN 20 AND 30
- Ordenação: ORDER BY created_at DESC
- Busca binária: O(log n)
"""

# Criar índice (PostgreSQL usa B-Tree por padrão)
CREATE INDEX idx_users_age ON users(age);

# Query otimizada
SELECT * FROM users WHERE age BETWEEN 20 AND 30;

# Execution plan:
# Index Scan using idx_users_age (cost=0.43..8.45 rows=50)
#   Index Cond: (age >= 20 AND age <= 30)

# Sem índice: O(n) - full table scan
# Com índice B-Tree: O(log n + k) - k = resultados
```

---

## 🕸️ Grafos

### Quando Usar

**Use Grafo quando tiver:**
- ✅ Relações muitos-para-muitos
- ✅ Social network (seguidores, amigos)
- ✅ Recomendações
- ✅ Routing (caminhos)

### Aplicação 1: Social Network (Follow Graph)

```python
class SocialGraph:
    """
    Grafo de seguidores

    Directed graph:
    Alice → Bob (Alice segue Bob)
    Bob → Charlie
    Charlie → Alice
    """

    def __init__(self):
        # Adjacency list (Hash Table de Hash Tables)
        self.followers = defaultdict(set)  # user_id -> {follower_ids}
        self.following = defaultdict(set)  # user_id -> {following_ids}

    def follow(self, follower_id: int, followee_id: int):
        """
        User A seguir User B

        O(1) com sets
        """
        self.following[follower_id].add(followee_id)
        self.followers[followee_id].add(follower_id)

    def unfollow(self, follower_id: int, followee_id: int):
        """O(1)"""
        self.following[follower_id].discard(followee_id)
        self.followers[followee_id].discard(follower_id)

    def get_followers(self, user_id: int) -> Set[int]:
        """Retornar quem segue o user - O(1)"""
        return self.followers[user_id]

    def get_following(self, user_id: int) -> Set[int]:
        """Retornar quem o user segue - O(1)"""
        return self.following[user_id]

    def get_mutual_friends(self, user_a: int, user_b: int) -> Set[int]:
        """
        Amigos em comum (interseção de grafos)

        O(min(|A|, |B|))
        """
        following_a = self.following[user_a]
        following_b = self.following[user_b]

        return following_a & following_b  # Set intersection

    def get_friend_suggestions(self, user_id: int, limit: int = 10) -> List[int]:
        """
        Sugestões de amizade (2-hop neighbors)

        Algoritmo:
        1. Pegar amigos dos meus amigos (2-hop BFS)
        2. Remover: eu mesmo, quem já sigo
        3. Ordenar por # de amigos em comum
        """
        following = self.following[user_id]

        # Friends of friends (2-hop)
        friend_suggestions = Counter()

        for friend_id in following:
            friends_of_friend = self.following[friend_id]

            for candidate in friends_of_friend:
                # Pular: eu mesmo, quem já sigo
                if candidate == user_id or candidate in following:
                    continue

                friend_suggestions[candidate] += 1  # Contar amigos em comum

        # Retornar top N por amigos em comum
        return [user_id for user_id, _ in friend_suggestions.most_common(limit)]


# Uso
graph = SocialGraph()

# Construir grafo
graph.follow(1, 2)  # Alice → Bob
graph.follow(1, 3)  # Alice → Charlie
graph.follow(2, 3)  # Bob → Charlie
graph.follow(3, 4)  # Charlie → David

# Sugestões para Alice
suggestions = graph.get_friend_suggestions(user_id=1)
# [4] - David é amigo de Charlie, que Alice já segue
```

### Aplicação 2: Shortest Path (BFS)

```python
from collections import deque

def shortest_path_bfs(graph: dict, start: int, end: int) -> List[int]:
    """
    Caminho mais curto entre dois users (degrees of separation)

    BFS garante caminho mais curto em grafo não-ponderado
    """
    if start == end:
        return [start]

    visited = {start}
    queue = deque([(start, [start])])  # (node, path)

    while queue:
        current, path = queue.popleft()

        # Explorar vizinhos
        for neighbor in graph[current]:
            if neighbor in visited:
                continue

            new_path = path + [neighbor]

            if neighbor == end:
                return new_path  # Encontrou!

            visited.add(neighbor)
            queue.append((neighbor, new_path))

    return []  # Não há caminho


# Uso: "Degrees of separation" (Kevin Bacon game)
graph = {
    1: [2, 3],  # Alice conecta com Bob, Charlie
    2: [1, 3, 4],
    3: [1, 2, 5],
    4: [2],
    5: [3]
}

path = shortest_path_bfs(graph, start=1, end=4)
# Output: [1, 2, 4] - Alice → Bob → David (2 degrees)
```

---

## ⛰️ Heaps

### Quando Usar

**Use Heap quando precisar:**
- ✅ Top K elementos
- ✅ Priority Queue
- ✅ Median em stream
- ✅ Merge K sorted arrays

### Aplicação 1: Top K Posts (Min Heap)

```python
import heapq

def get_top_posts(posts: List[Post], k: int = 10) -> List[Post]:
    """
    Buscar top K posts por engagement

    Heap é mais eficiente que sort para K << N
    """
    # Min heap de tamanho K
    # Heap mantém os K maiores elementos
    heap = []

    for post in posts:
        score = post.likes_count + post.comments_count * 3

        if len(heap) < k:
            heapq.heappush(heap, (score, post))  # O(log k)
        elif score > heap[0][0]:  # Maior que menor elemento do heap
            heapq.heapreplace(heap, (score, post))  # O(log k)

    # Heap tem os top K, ordenar
    return [post for score, post in sorted(heap, reverse=True)]


# Complexidade: O(n log k) vs O(n log n) com sort
# Para k=10, n=1M: ~13x mais rápido!
```

### Aplicação 2: Task Queue (Priority Queue)

```python
import heapq
import time

class TaskQueue:
    """
    Fila de tarefas com prioridade

    Use cases:
    - Email queue (VIP emails primeiro)
    - Job processing (urgent jobs primeiro)
    - Rate limiting (delayed tasks)
    """

    def __init__(self):
        self.heap = []  # Min heap
        self.counter = 0  # Para desempatar (FIFO)

    def add_task(self, task: dict, priority: int = 0):
        """
        Adicionar task

        Priority menor = maior prioridade (min heap)
        - priority 0 = urgent
        - priority 5 = normal
        - priority 10 = low
        """
        # Heap: (priority, counter, task)
        # Counter garante FIFO para mesma priority
        heapq.heappush(self.heap, (priority, self.counter, task))
        self.counter += 1

    def get_next_task(self) -> dict:
        """Pop task de maior prioridade - O(log n)"""
        if not self.heap:
            return None

        priority, counter, task = heapq.heappop(self.heap)
        return task


# Uso
queue = TaskQueue()

# Adicionar tasks
queue.add_task({'type': 'email', 'to': 'vip@example.com'}, priority=0)  # Urgent
queue.add_task({'type': 'email', 'to': 'user@example.com'}, priority=5)  # Normal
queue.add_task({'type': 'cleanup'}, priority=10)  # Low

# Processar tasks
while True:
    task = queue.get_next_task()
    if not task:
        break

    process_task(task)
    # Output: VIP email → Normal email → Cleanup
```

### Aplicação 3: Merge K Sorted Lists (Min Heap)

```python
import heapq

def merge_k_sorted_lists(lists: List[List[int]]) -> List[int]:
    """
    Merge K sorted lists

    Use case: Merge resultados de múltiplos shards de DB

    Exemplo:
    Shard 1: [1, 4, 7]
    Shard 2: [2, 5, 8]
    Shard 3: [3, 6, 9]
    → [1, 2, 3, 4, 5, 6, 7, 8, 9]
    """
    heap = []
    result = []

    # Inicializar heap com primeiro elemento de cada lista
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))  # (value, list_idx, element_idx)

    while heap:
        value, list_idx, element_idx = heapq.heappop(heap)
        result.append(value)

        # Adicionar próximo elemento da mesma lista
        next_idx = element_idx + 1
        if next_idx < len(lists[list_idx]):
            next_value = lists[list_idx][next_idx]
            heapq.heappush(heap, (next_value, list_idx, next_idx))

    return result


# Complexidade: O(N log K) onde N = total elements, K = num lists
# Melhor que naive O(N * K)
```

---

## 🔤 Tries (Prefix Tree)

### Quando Usar

**Use Trie quando precisar:**
- ✅ Autocomplete
- ✅ Spell checking
- ✅ IP routing
- ✅ Prefix matching

### Aplicação: Autocomplete

```python
class TrieNode:
    def __init__(self):
        self.children = {}  # char -> TrieNode
        self.is_end_of_word = False
        self.frequency = 0  # Número de vezes que palavra foi buscada


class Autocomplete:
    """
    Autocomplete com Trie

    Suporta:
    - Insert palavra: O(m) onde m = len(palavra)
    - Search prefix: O(m)
    - Autocomplete: O(m + n) onde n = resultados
    """

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, frequency: int = 1):
        """Inserir palavra no trie"""
        node = self.root

        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()

            node = node.children[char]

        node.is_end_of_word = True
        node.frequency += frequency

    def search(self, word: str) -> bool:
        """Verificar se palavra existe"""
        node = self._find_node(word)
        return node is not None and node.is_end_of_word

    def starts_with(self, prefix: str) -> bool:
        """Verificar se alguma palavra começa com prefix"""
        return self._find_node(prefix) is not None

    def autocomplete(self, prefix: str, limit: int = 10) -> List[tuple]:
        """
        Retornar sugestões para prefix

        Retorna: [(palavra, frequency), ...]
        """
        node = self._find_node(prefix)

        if not node:
            return []

        # DFS para encontrar todas palavras com esse prefix
        suggestions = []

        def dfs(current_node: TrieNode, current_word: str):
            if current_node.is_end_of_word:
                suggestions.append((current_word, current_node.frequency))

            for char, child_node in current_node.children.items():
                dfs(child_node, current_word + char)

        dfs(node, prefix)

        # Ordenar por frequency e limitar
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:limit]

    def _find_node(self, prefix: str) -> TrieNode:
        """Helper: encontrar nó do prefix"""
        node = self.root

        for char in prefix.lower():
            if char not in node.children:
                return None
            node = node.children[char]

        return node


# Uso
autocomplete = Autocomplete()

# Indexar palavras (do histórico de buscas)
autocomplete.insert("python", frequency=1000)
autocomplete.insert("python programming", frequency=500)
autocomplete.insert("python tutorial", frequency=800)
autocomplete.insert("java", frequency=600)
autocomplete.insert("javascript", frequency=900)

# Autocomplete
suggestions = autocomplete.autocomplete("py")
# Output: [('python', 1000), ('python tutorial', 800), ('python programming', 500)]

suggestions = autocomplete.autocomplete("java")
# Output: [('javascript', 900), ('java', 600)]


# Endpoint
@app.get("/search/autocomplete")
def search_autocomplete(query: str, limit: int = 10):
    suggestions = autocomplete.autocomplete(query, limit)
    return {"suggestions": [word for word, freq in suggestions]}
```

---

## 🎯 Estruturas Especializadas

### 1. Union-Find (Disjoint Set)

**Use quando:** Detectar componentes conectados, ciclos em grafo

```python
class UnionFind:
    """
    Union-Find para detectar grupos conectados

    Use case: Detectar grupos de amigos, network connectivity
    """

    def __init__(self, n: int):
        self.parent = list(range(n))  # Cada nó é seu próprio pai
        self.rank = [0] * n  # Altura da árvore

    def find(self, x: int) -> int:
        """
        Encontrar root do componente

        Path compression: O(α(n)) ≈ O(1) amortizado
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Compression

        return self.parent[x]

    def union(self, x: int, y: int):
        """
        Unir dois componentes

        Union by rank: O(α(n))
        """
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return  # Já conectados

        # Unir por rank (menor → maior)
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

    def is_connected(self, x: int, y: int) -> bool:
        """Verificar se dois nós estão conectados"""
        return self.find(x) == self.find(y)


# Uso: Detectar grupos de amigos
uf = UnionFind(n=5)  # 5 usuários

# Amizades (edges)
uf.union(0, 1)  # Alice e Bob são amigos
uf.union(1, 2)  # Bob e Charlie são amigos
uf.union(3, 4)  # David e Eve são amigos

# Verificar conexões
print(uf.is_connected(0, 2))  # True (Alice → Bob → Charlie)
print(uf.is_connected(0, 3))  # False (grupos diferentes)
```

### 2. Segment Tree

**Use quando:** Range queries + updates (somas, mínimo, máximo)

```python
class SegmentTree:
    """
    Segment Tree para range queries

    Use case: Estatísticas de range (soma, min, max)
    Exemplo: "Quantos likes posts receberam entre dia 1 e 30?"
    """

    def __init__(self, arr: List[int]):
        self.n = len(arr)
        self.tree = [0] * (4 * self.n)
        self._build(arr, 0, 0, self.n - 1)

    def _build(self, arr: List[int], node: int, start: int, end: int):
        if start == end:
            self.tree[node] = arr[start]
            return

        mid = (start + end) // 2
        left_child = 2 * node + 1
        right_child = 2 * node + 2

        self._build(arr, left_child, start, mid)
        self._build(arr, right_child, mid + 1, end)

        self.tree[node] = self.tree[left_child] + self.tree[right_child]

    def query_sum(self, left: int, right: int) -> int:
        """Range sum query - O(log n)"""
        return self._query(0, 0, self.n - 1, left, right)

    def _query(self, node: int, start: int, end: int, left: int, right: int) -> int:
        if right < start or left > end:
            return 0  # Fora do range

        if left <= start and end <= right:
            return self.tree[node]  # Completamente dentro

        mid = (start + end) // 2
        left_sum = self._query(2 * node + 1, start, mid, left, right)
        right_sum = self._query(2 * node + 2, mid + 1, end, left, right)

        return left_sum + right_sum


# Uso
likes_per_day = [10, 20, 15, 30, 25, 40, 35, 50]
seg_tree = SegmentTree(likes_per_day)

# Query: Total likes entre dia 2 e 5
total = seg_tree.query_sum(2, 5)
# Output: 15 + 30 + 25 + 40 = 110
```

---

## 📊 Comparação de Complexidades

| Estrutura | Insert | Delete | Search | Access | Use Case |
|-----------|--------|--------|--------|--------|----------|
| **Array** | O(n) | O(n) | O(n) | O(1) | Acesso por índice |
| **Hash Table** | O(1) | O(1) | O(1) | - | Lookup rápido |
| **Binary Tree** | O(log n) | O(log n) | O(log n) | O(log n) | Range queries |
| **Heap** | O(log n) | O(log n) | O(n) | O(1) | Priority queue |
| **Trie** | O(m) | O(m) | O(m) | - | Autocomplete |
| **Graph** | O(1) | O(1) | O(V+E) | - | Relações |

Onde:
- n = número de elementos
- m = tamanho da string
- V = vértices, E = edges

---

## 🎯 Escolhendo a Estrutura Certa

### Fluxograma de Decisão

```
Precisa de ordem?
├─ NÃO → Hash Table (dict, set)
└─ SIM
    ├─ Acesso por índice? → Array, List
    ├─ Range queries? → B-Tree (DB index)
    ├─ Top K elementos? → Heap
    ├─ Prefix matching? → Trie
    └─ Relações? → Graph

Precisa de operações nas pontas?
└─ Queue (FIFO) → Deque

Precisa de prioridade?
└─ Priority Queue → Heap

Precisa de hierarquia?
└─ Tree (categorias, comments)
```

---

## ✅ Resumo Executivo

**Arrays/Lists:**
- Cursor pagination
- Sliding window rate limiting

**Hash Tables:**
- Resolver N+1 problem
- Cache (LRU)
- Agrupar dados (defaultdict)
- Eliminar duplicatas (set)

**Trees:**
- Categorias hierárquicas
- Nested comments
- DB indexes (B-Tree)

**Graphs:**
- Social networks (followers)
- Friend suggestions
- Shortest path (BFS)

**Heaps:**
- Top K posts
- Priority queue (tasks)
- Merge K sorted lists

**Tries:**
- Autocomplete
- Prefix search

**Especializado:**
- Union-Find: Grupos conectados
- Segment Tree: Range queries

---

**Estruturas de dados são a base de sistemas eficientes! 🗂️**
