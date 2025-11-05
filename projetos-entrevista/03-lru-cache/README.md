# 💾 Projeto 3: LRU Cache

> Estrutura de dados fundamental - aparece em 60% das entrevistas de coding

---

## 📋 Problema

**Descrição:** Implementar cache LRU (Least Recently Used) com operações O(1).

**LRU Policy:** Quando cache está cheio, remover o item MENOS recentemente usado.

**Exemplo:**
```
Capacity: 3

put(1, "a")  → Cache: {1: "a"}
put(2, "b")  → Cache: {1: "a", 2: "b"}
put(3, "c")  → Cache: {1: "a", 2: "b", 3: "c"}
get(1)       → "a"  Cache: {2: "b", 3: "c", 1: "a"}  (1 move to end)
put(4, "d")  → Cache: {3: "c", 1: "a", 4: "d"}  (evict 2, least used)
```

---

## 🎯 Requisitos

### Funcionais
1. ✅ `get(key)`: Buscar valor, retorna -1 se não existe
2. ✅ `put(key, value)`: Inserir ou atualizar
3. ✅ Cache size é limitado (capacity)
4. ✅ Quando cheio, remover least recently used

### Não-funcionais
1. **Complexidade**: O(1) para get e put
2. **Thread-safe**: Suportar acesso concorrente
3. **Memory efficient**: Não vazar memória

---

## 🔧 Implementação

### Abordagem Ingênua (ERRADA)

```python
# ❌ ERRADO: O(n) complexity
class NaiveLRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> (value, last_used_time)
        self.time = 0

    def get(self, key: int) -> int:
        if key in self.cache:
            value, _ = self.cache[key]
            self.time += 1
            self.cache[key] = (value, self.time)
            return value
        return -1

    def put(self, key: int, value: int):
        self.time += 1

        if key in self.cache:
            self.cache[key] = (value, self.time)
        else:
            if len(self.cache) >= self.capacity:
                # ❌ O(n): procurar LRU
                lru_key = min(self.cache, key=lambda k: self.cache[k][1])
                del self.cache[lru_key]

            self.cache[key] = (value, self.time)
```

**Problema:** `put()` é O(n) para achar LRU!

---

### Solução Ótima: HashMap + Doubly Linked List

**Estrutura:**
```
HashMap: key -> Node
Doubly Linked List: mantém ordem de uso

Head ←→ [MRU] ←→ [second] ←→ ... ←→ [LRU] ←→ Tail

get(key): move para MRU (head)
put(key): adiciona no MRU, remove LRU se cheio
```

**Implementação Completa:**

```python
class DLLNode:
    """Node de Doubly Linked List"""
    def __init__(self, key: int = 0, value: int = 0):
        self.key = key
        self.value = value
        self.prev: DLLNode = None
        self.next: DLLNode = None


class LRUCache:
    """
    LRU Cache com O(1) get e put

    Estrutura:
    - HashMap: key -> Node (O(1) lookup)
    - DLL: manter ordem LRU (O(1) move/remove)

    Head ←→ [MRU] ←→ ... ←→ [LRU] ←→ Tail
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> DLLNode

        # Sentinels (dummy nodes)
        self.head = DLLNode()  # MRU end
        self.tail = DLLNode()  # LRU end
        self.head.next = self.tail
        self.tail.prev = self.head

    def _add_to_head(self, node: DLLNode):
        """Adicionar node depois do head (MRU position)"""
        node.prev = self.head
        node.next = self.head.next

        self.head.next.prev = node
        self.head.next = node

    def _remove_node(self, node: DLLNode):
        """Remover node da lista"""
        prev_node = node.prev
        next_node = node.next

        prev_node.next = next_node
        next_node.prev = prev_node

    def _move_to_head(self, node: DLLNode):
        """Mover node para head (mark as recently used)"""
        self._remove_node(node)
        self._add_to_head(node)

    def _pop_tail(self) -> DLLNode:
        """Remover node antes do tail (LRU)"""
        lru = self.tail.prev
        self._remove_node(lru)
        return lru

    def get(self, key: int) -> int:
        """
        Buscar valor

        Complexidade: O(1)
        """
        if key not in self.cache:
            return -1

        node = self.cache[key]

        # Mover para head (mark as recently used)
        self._move_to_head(node)

        return node.value

    def put(self, key: int, value: int):
        """
        Inserir ou atualizar

        Complexidade: O(1)
        """
        if key in self.cache:
            # Atualizar existente
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            # Novo node
            node = DLLNode(key, value)
            self.cache[key] = node
            self._add_to_head(node)

            # Se cheio, remover LRU
            if len(self.cache) > self.capacity:
                lru = self._pop_tail()
                del self.cache[lru.key]


# Uso
cache = LRUCache(capacity=3)

cache.put(1, 100)
cache.put(2, 200)
cache.put(3, 300)

print(cache.get(1))  # 100 (move 1 to MRU)

cache.put(4, 400)  # Evict 2 (LRU)

print(cache.get(2))  # -1 (evicted)
print(cache.get(3))  # 300
print(cache.get(4))  # 400
```

**Análise de Complexidade:**
- `get()`: O(1) - HashMap lookup + DLL move
- `put()`: O(1) - HashMap insert + DLL add/remove
- Espaço: O(capacity)

---

## 🔒 Thread-Safe Version

```python
import threading

class ThreadSafeLRUCache(LRUCache):
    """LRU Cache thread-safe"""

    def __init__(self, capacity: int):
        super().__init__(capacity)
        self.lock = threading.RLock()  # Reentrant lock

    def get(self, key: int) -> int:
        with self.lock:
            return super().get(key)

    def put(self, key: int, value: int):
        with self.lock:
            return super().put(key, value)


# Uso concorrente
cache = ThreadSafeLRUCache(capacity=100)

def worker(cache, key, value):
    cache.put(key, value)
    result = cache.get(key)
    print(f"Thread {threading.current_thread().name}: get({key}) = {result}")

threads = []
for i in range(10):
    t = threading.Thread(target=worker, args=(cache, i, i * 100))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

---

## 🚀 Variações

### 1. LFU Cache (Least Frequently Used)

```python
from collections import defaultdict

class LFUCache:
    """
    LFU: Remove item com MENOR frequência de acesso

    Estrutura:
    - cache: key -> (value, freq)
    - freq_map: freq -> set of keys
    - min_freq: track minimum frequency
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> (value, freq)
        self.freq_map = defaultdict(set)  # freq -> {keys}
        self.min_freq = 0

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1

        value, freq = self.cache[key]

        # Incrementar frequência
        self.freq_map[freq].discard(key)
        if not self.freq_map[freq] and freq == self.min_freq:
            self.min_freq += 1

        new_freq = freq + 1
        self.cache[key] = (value, new_freq)
        self.freq_map[new_freq].add(key)

        return value

    def put(self, key: int, value: int):
        if self.capacity == 0:
            return

        if key in self.cache:
            # Atualizar
            _, freq = self.cache[key]
            self.cache[key] = (value, freq)
            self.get(key)  # Incrementar freq
        else:
            # Novo
            if len(self.cache) >= self.capacity:
                # Remover LFU
                evict_key = self.freq_map[self.min_freq].pop()
                del self.cache[evict_key]

            self.cache[key] = (value, 1)
            self.freq_map[1].add(key)
            self.min_freq = 1
```

---

### 2. TTL Cache (Time To Live)

```python
import time

class TTLCache:
    """
    Cache com expiração

    Cada item tem TTL (time to live)
    """

    def __init__(self, capacity: int, ttl: int):
        self.capacity = capacity
        self.ttl = ttl  # seconds
        self.cache = {}  # key -> (value, expire_time)
        self.lru = LRUCache(capacity)

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1

        value, expire_time = self.cache[key]

        # Verificar se expirou
        if time.time() > expire_time:
            del self.cache[key]
            return -1

        # Atualizar LRU
        self.lru.get(key)

        return value

    def put(self, key: int, value: int):
        expire_time = time.time() + self.ttl

        if key in self.cache:
            self.cache[key] = (value, expire_time)
        else:
            if len(self.cache) >= self.capacity:
                # Remover LRU
                lru_key = self.lru._pop_tail().key
                if lru_key in self.cache:
                    del self.cache[lru_key]

            self.cache[key] = (value, expire_time)

        self.lru.put(key, value)
```

---

## 🎯 Python Built-in: functools.lru_cache

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n):
    """
    Fibonacci com memoization

    lru_cache automaticamente cacheia resultados
    """
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)


# Sem cache: O(2^n)
# Com cache: O(n)

print(fibonacci(100))  # Instantâneo!

# Ver estatísticas
print(fibonacci.cache_info())
# CacheInfo(hits=98, misses=101, maxsize=128, currsize=101)
```

---

## 🏗️ Redis Implementation

```python
import redis
import json

class RedisLRUCache:
    """
    LRU Cache distribuído com Redis

    Redis tem LRU eviction policy built-in!
    """

    def __init__(self, redis_client, prefix: str = "cache"):
        self.redis = redis_client
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def get(self, key: str):
        """Buscar do cache"""
        redis_key = self._make_key(key)
        value = self.redis.get(redis_key)

        if value:
            return json.loads(value)

        return None

    def put(self, key: str, value, ttl: int = 3600):
        """Salvar no cache com TTL"""
        redis_key = self._make_key(key)
        self.redis.setex(
            redis_key,
            ttl,
            json.dumps(value)
        )

    def delete(self, key: str):
        """Remover do cache"""
        redis_key = self._make_key(key)
        self.redis.delete(redis_key)


# Configurar Redis com LRU eviction
"""
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
"""

redis_client = redis.Redis(host='localhost', port=6379)
cache = RedisLRUCache(redis_client)

# Uso
cache.put("user:123", {"name": "João", "age": 30})
user = cache.get("user:123")
print(user)  # {'name': 'João', 'age': 30}
```

---

## 🧪 Testes

```python
import pytest

def test_lru_basic():
    cache = LRUCache(capacity=2)

    cache.put(1, 100)
    cache.put(2, 200)

    assert cache.get(1) == 100
    assert cache.get(2) == 200


def test_lru_eviction():
    cache = LRUCache(capacity=2)

    cache.put(1, 100)
    cache.put(2, 200)
    cache.put(3, 300)  # Evict 1 (LRU)

    assert cache.get(1) == -1  # Evicted
    assert cache.get(2) == 200
    assert cache.get(3) == 300


def test_lru_update_moves_to_mru():
    cache = LRUCache(capacity=2)

    cache.put(1, 100)
    cache.put(2, 200)
    cache.get(1)  # Access 1 (now MRU)
    cache.put(3, 300)  # Evict 2 (LRU)

    assert cache.get(1) == 100
    assert cache.get(2) == -1  # Evicted
    assert cache.get(3) == 300


def test_lru_overwrite():
    cache = LRUCache(capacity=2)

    cache.put(1, 100)
    cache.put(1, 999)  # Overwrite

    assert cache.get(1) == 999


def test_lru_thread_safety():
    cache = ThreadSafeLRUCache(capacity=100)

    def worker(key, value):
        cache.put(key, value)
        result = cache.get(key)
        assert result == value

    threads = [
        threading.Thread(target=worker, args=(i, i * 100))
        for i in range(100)
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Por que usar Doubly Linked List ao invés de List?"

**Você:** "Doubly Linked List permite remover e inserir em O(1) quando temos ponteiro para o node. List normal seria O(n) para remover do meio."

---

**Interviewer:** "Como você faria isso thread-safe?"

**Você:** "Adiciono lock (threading.RLock) em torno de get() e put(). RLock permite reentrance, importante se métodos internos chamam uns aos outros. Para alta concorrência, usaria sharding (múltiplos caches com lock separado)."

---

**Interviewer:** "LRU vs LFU, quando usar cada?"

**Você:**
- **LRU**: Assume que dados recentes serão acessados novamente. Bom para temporal locality (80% dos casos).
- **LFU**: Assume que dados frequentes continuarão frequentes. Bom quando padrão de acesso é estável (ex: produtos populares em e-commerce).

---

**Interviewer:** "Como você escalaria isso para distribuído?"

**Você:** "Para sistema distribuído, usaria Redis com LRU eviction policy built-in. Redis já implementa LRU approximado que é suficiente para 99% dos casos. Para 100% precisão, usaria consistent hashing para particionar cache entre múltiplos Redis nodes."

---

## ✅ Checklist da Entrevista

- [ ] Explicar problema (cache com capacity limit)
- [ ] Discutir abordagem ingênua (por que O(n) é ruim)
- [ ] Propor HashMap + DLL (O(1) para ambos)
- [ ] Desenhar estrutura de dados
- [ ] Implementar get() e put()
- [ ] Discutir thread safety (lock)
- [ ] Variações (LFU, TTL)
- [ ] Escalabilidade (Redis, sharding)
- [ ] Complexidade (tempo e espaço)

---

## 📊 Aplicações Reais

**Onde LRU Cache é usado:**

1. **CPU Cache** (L1, L2, L3)
2. **Database Buffer Pool**
3. **Web Browser Cache**
4. **CDN Edge Caching**
5. **Redis** (maxmemory-policy allkeys-lru)
6. **Operating System** (Page replacement)

---

**Estrutura de dados fundamental! 💾**

Empresas: Google, Meta, Amazon, Microsoft, Apple, Netflix...
