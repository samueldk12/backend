"""
Exemplo 3: Heaps, Tries e Estruturas Especializadas

Demonstra estruturas de dados avançadas para casos específicos
"""

import heapq
from typing import List, Tuple, Dict
from collections import defaultdict
import time


# =====================================
# HEAP: Top K Elements
# =====================================

class Post:
    def __init__(self, id: int, title: str, likes: int, comments: int):
        self.id = id
        self.title = title
        self.likes = likes
        self.comments = comments

    def engagement_score(self) -> int:
        """Score de engagement (likes + comments * 3)"""
        return self.likes + (self.comments * 3)

    def __repr__(self):
        return f"Post({self.id}, '{self.title}', score={self.engagement_score()})"


def get_top_posts_sort(posts: List[Post], k: int = 10) -> List[Post]:
    """
    ❌ VERSÃO LENTA: Sort completo

    Complexidade: O(n log n)
    """
    sorted_posts = sorted(posts, key=lambda p: p.engagement_score(), reverse=True)
    return sorted_posts[:k]


def get_top_posts_heap(posts: List[Post], k: int = 10) -> List[Post]:
    """
    ✅ VERSÃO RÁPIDA: Min heap de tamanho K

    Mantém apenas os K maiores elementos
    Complexidade: O(n log k) << O(n log n) quando k << n

    Exemplo: k=10, n=1M
    - Sort: O(1M * log 1M) = ~20M operações
    - Heap: O(1M * log 10) = ~3.3M operações
    Speedup: 6x!
    """
    heap = []  # Min heap

    for post in posts:
        score = post.engagement_score()

        if len(heap) < k:
            # Heap ainda não está cheio, adicionar
            heapq.heappush(heap, (score, post))
        elif score > heap[0][0]:  # Maior que menor elemento do heap
            # Substituir menor elemento
            heapq.heapreplace(heap, (score, post))

    # Heap tem os top K, ordenar
    return [post for score, post in sorted(heap, key=lambda x: x[0], reverse=True)]


# =====================================
# HEAP: Priority Queue
# =====================================

class Task:
    def __init__(self, id: int, description: str, priority: int):
        self.id = id
        self.description = description
        self.priority = priority  # Menor = mais prioritário

    def __repr__(self):
        return f"Task({self.id}, '{self.description}', priority={self.priority})"


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

    def add_task(self, task: Task):
        """
        Adicionar task à fila

        Heap: (priority, counter, task)
        Counter garante FIFO para mesma priority
        """
        heapq.heappush(self.heap, (task.priority, self.counter, task))
        self.counter += 1

    def get_next_task(self) -> Task:
        """Pop task de maior prioridade - O(log n)"""
        if not self.heap:
            return None

        priority, counter, task = heapq.heappop(self.heap)
        return task

    def peek(self) -> Task:
        """Ver próxima task sem remover - O(1)"""
        if not self.heap:
            return None

        priority, counter, task = self.heap[0]
        return task

    def size(self) -> int:
        return len(self.heap)


# =====================================
# HEAP: Merge K Sorted Lists
# =====================================

def merge_k_sorted_lists(lists: List[List[int]]) -> List[int]:
    """
    Merge K sorted lists (útil para merge de shards de DB)

    Exemplo:
    Shard 1: [1, 4, 7]
    Shard 2: [2, 5, 8]
    Shard 3: [3, 6, 9]
    → [1, 2, 3, 4, 5, 6, 7, 8, 9]

    Complexidade: O(N log K) onde N=total elements, K=num lists
    Melhor que naive O(N * K)
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


# =====================================
# TRIE: Autocomplete
# =====================================

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end_of_word = False
        self.frequency = 0  # Popularidade da palavra


class Autocomplete:
    """
    Autocomplete com Trie (Prefix Tree)

    Usado por: Google Search, IDE autocomplete, spell check
    """

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, frequency: int = 1):
        """
        Inserir palavra no trie

        Complexidade: O(m) onde m = len(palavra)
        """
        node = self.root

        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()

            node = node.children[char]

        node.is_end_of_word = True
        node.frequency += frequency

    def search(self, word: str) -> bool:
        """Verificar se palavra existe - O(m)"""
        node = self._find_node(word)
        return node is not None and node.is_end_of_word

    def starts_with(self, prefix: str) -> bool:
        """Verificar se alguma palavra começa com prefix - O(m)"""
        return self._find_node(prefix) is not None

    def autocomplete(self, prefix: str, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Retornar sugestões para prefix

        Retorna: [(palavra, frequency), ...]
        Complexidade: O(m + n) onde m=len(prefix), n=resultados
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


# =====================================
# UNION-FIND: Grupos Conectados
# =====================================

class UnionFind:
    """
    Union-Find (Disjoint Set)

    Use cases:
    - Detectar grupos de amigos
    - Network connectivity
    - Kruskal's MST algorithm
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
        """Verificar se dois nós estão conectados - O(α(n))"""
        return self.find(x) == self.find(y)

    def count_components(self) -> int:
        """Contar número de componentes conectados"""
        roots = set()
        for i in range(len(self.parent)):
            roots.add(self.find(i))
        return len(roots)


# =====================================
# EXEMPLOS PRÁTICOS
# =====================================

def example_top_k_posts():
    """Exemplo: Top posts por engagement"""
    print("\n" + "="*60)
    print("EXEMPLO: Top K Posts (Heap)")
    print("="*60)

    # Gerar 1000 posts
    posts = [
        Post(i, f"Post {i}", likes=i*10, comments=i*2)
        for i in range(1, 1001)
    ]

    k = 5

    # Benchmark
    start = time.time()
    top_sort = get_top_posts_sort(posts, k)
    time_sort = time.time() - start

    start = time.time()
    top_heap = get_top_posts_heap(posts, k)
    time_heap = time.time() - start

    print(f"\n✅ Top {k} posts:")
    for post in top_heap:
        print(f"  - {post}")

    print(f"\nPerformance:")
    print(f"  Sort:   {time_sort*1000:.2f}ms")
    print(f"  Heap:   {time_heap*1000:.2f}ms")
    print(f"  Speedup: {time_sort/time_heap:.1f}x")


def example_priority_queue():
    """Exemplo: Task queue com prioridades"""
    print("\n" + "="*60)
    print("EXEMPLO: Priority Queue (Heap)")
    print("="*60)

    queue = TaskQueue()

    # Adicionar tasks com diferentes prioridades
    tasks = [
        Task(1, "Send VIP email", priority=0),  # Urgent
        Task(2, "Process payment", priority=1),  # High
        Task(3, "Send notification", priority=5),  # Normal
        Task(4, "Cleanup logs", priority=10),  # Low
        Task(5, "Send welcome email", priority=5),  # Normal
        Task(6, "Security alert", priority=0),  # Urgent
    ]

    for task in tasks:
        queue.add_task(task)

    print(f"\n✅ Tasks adicionadas: {queue.size()}")
    print("\nProcessando tasks (por prioridade):")

    while queue.size() > 0:
        task = queue.get_next_task()
        print(f"  → {task}")


def example_merge_k_lists():
    """Exemplo: Merge resultados de shards"""
    print("\n" + "="*60)
    print("EXEMPLO: Merge K Sorted Lists (Heap)")
    print("="*60)

    # Simular resultados de 3 shards de DB (ordenados por timestamp)
    shard1 = [1, 4, 7, 10, 13]
    shard2 = [2, 5, 8, 11, 14]
    shard3 = [3, 6, 9, 12, 15]

    merged = merge_k_sorted_lists([shard1, shard2, shard3])

    print("\nShards:")
    print(f"  Shard 1: {shard1}")
    print(f"  Shard 2: {shard2}")
    print(f"  Shard 3: {shard3}")

    print(f"\n✅ Merged (ordenado): {merged}")


def example_autocomplete():
    """Exemplo: Autocomplete de busca"""
    print("\n" + "="*60)
    print("EXEMPLO: Autocomplete (Trie)")
    print("="*60)

    autocomplete = Autocomplete()

    # Indexar palavras (do histórico de buscas)
    searches = [
        ("python", 1000),
        ("python programming", 500),
        ("python tutorial", 800),
        ("python for beginners", 600),
        ("java", 700),
        ("javascript", 900),
        ("java tutorial", 400),
    ]

    for word, frequency in searches:
        autocomplete.insert(word, frequency)

    # Autocomplete para "py"
    print("\n✅ Autocomplete para 'py':")
    suggestions = autocomplete.autocomplete("py", limit=5)
    for word, freq in suggestions:
        print(f"  - {word} ({freq} searches)")

    # Autocomplete para "java"
    print("\n✅ Autocomplete para 'java':")
    suggestions = autocomplete.autocomplete("java", limit=5)
    for word, freq in suggestions:
        print(f"  - {word} ({freq} searches)")


def example_union_find():
    """Exemplo: Grupos de amigos (componentes conectados)"""
    print("\n" + "="*60)
    print("EXEMPLO: Grupos de Amigos (Union-Find)")
    print("="*60)

    # 6 usuários
    users = {
        0: "Alice",
        1: "Bob",
        2: "Charlie",
        3: "David",
        4: "Eve",
        5: "Frank"
    }

    uf = UnionFind(n=6)

    # Amizades (edges)
    friendships = [
        (0, 1),  # Alice - Bob
        (1, 2),  # Bob - Charlie
        (3, 4),  # David - Eve
    ]

    for user1, user2 in friendships:
        uf.union(user1, user2)

    print("\nAmizades:")
    for user1, user2 in friendships:
        print(f"  - {users[user1]} ↔ {users[user2]}")

    # Verificar conexões
    print("\n✅ Verificações:")
    print(f"  Alice e Charlie conectados? {uf.is_connected(0, 2)}")  # True (via Bob)
    print(f"  Alice e David conectados? {uf.is_connected(0, 3)}")  # False
    print(f"  David e Eve conectados? {uf.is_connected(3, 4)}")  # True

    # Contar grupos
    print(f"\n✅ Número de grupos de amigos: {uf.count_components()}")
    # 3 grupos: {Alice, Bob, Charlie}, {David, Eve}, {Frank}


# =====================================
# MAIN
# =====================================

if __name__ == "__main__":
    print("\n⛰️  HEAPS, TRIES & SPECIALIZED STRUCTURES\n")
    print("Demonstração de estruturas avançadas para casos específicos")

    # Exemplos
    example_top_k_posts()
    example_priority_queue()
    example_merge_k_lists()
    example_autocomplete()
    example_union_find()

    print("\n" + "="*60)
    print("✅ CONCLUSÃO")
    print("="*60)
    print("""
HEAPS:
- Top K elements: O(n log k) << O(n log n)
- Priority queue: Email, tasks, rate limiting
- Merge K sorted lists: Multi-shard queries

TRIES:
- Autocomplete: O(m + n) onde m=prefix, n=results
- Spell checking
- IP routing

UNION-FIND:
- Grupos conectados: O(α(n)) ≈ O(1)
- Network connectivity
- Friend groups

QUANDO USAR:
- Heap: "Top 10", "Priority", "Merge sorted"
- Trie: "Starts with", "Autocomplete", "Prefix"
- Union-Find: "Connected?", "Groups", "Cycles"

APLICAÇÕES REAIS:
- Google Search: Trie para autocomplete
- Email services: Heap para priority
- Social networks: Union-Find para groups
- Database sharding: Heap para merge
    """)
