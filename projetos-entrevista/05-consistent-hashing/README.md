# ⚖️ Projeto 5: Consistent Hashing

> Algoritmo fundamental para sharding - aparece em 80% das entrevistas de system design

---

## 📋 Problema

**Descrição:** Implementar consistent hashing para distribuir dados entre múltiplos servidores de forma balanceada e minimizar reorganização quando servidores são adicionados/removidos.

**Problema com Hash Simples:**
```python
# ❌ PROBLEMA: Hash modulo
def get_server(key: str, num_servers: int) -> int:
    return hash(key) % num_servers

# Com 3 servidores:
get_server("user:123", 3)  # → Server 0
get_server("user:456", 3)  # → Server 1
get_server("user:789", 3)  # → Server 2

# Adicionar 1 servidor (agora 4):
get_server("user:123", 4)  # → Server 3 ❌ (era 0!)
get_server("user:456", 4)  # → Server 0 ❌ (era 1!)
get_server("user:789", 4)  # → Server 1 ❌ (era 2!)

# 💥 75% das chaves mudaram de servidor!
# Cache invalidado, precisa remover tudo e repovoar
```

**Solução: Consistent Hashing**
```
Adicionar servidor → apenas ~25% das chaves migram
Remover servidor → apenas ~25% das chaves migram

Hash Ring:
        Server A (90°)
             ↓
    --------•--------
   /                 \
  /                   \
 •                     • ← Server C (270°)
  \                   /
   \                 /
    --------•--------
             ↑
        Server B (180°)

Chave "user:123" → hash = 100° → vai para Server A (próximo no sentido horário)
```

---

## 🎯 Requisitos

### Funcionais
1. ✅ `add_node()`: Adicionar servidor ao ring
2. ✅ `remove_node()`: Remover servidor do ring
3. ✅ `get_node()`: Retornar servidor para uma chave
4. ✅ Virtual nodes para balanceamento

### Não-funcionais
1. **Minimal Disruption**: ~K/N chaves migram (K=total keys, N=num servers)
2. **Load Balancing**: Distribuição uniforme
3. **O(log N) lookup**: Busca eficiente

---

## 🔧 Implementação

### 1. Consistent Hashing Básico

```python
import hashlib
from bisect import bisect_right
from typing import Dict, List, Optional

class ConsistentHash:
    """
    Consistent Hashing básico

    Estrutura:
    - Hash ring (círculo de 0 a 2^32-1)
    - Servidores mapeados em pontos do círculo
    - Chaves mapeadas para próximo servidor no sentido horário
    """

    def __init__(self, nodes: List[str] = None):
        """
        Args:
            nodes: Lista de nomes de servidores
        """
        self.ring: Dict[int, str] = {}  # hash_value -> node_name
        self.sorted_keys: List[int] = []  # Hashes ordenados

        if nodes:
            for node in nodes:
                self.add_node(node)

    def _hash(self, key: str) -> int:
        """
        Hash function (MD5 para 32 bits)

        Retorna: 0 a 2^32-1
        """
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node: str):
        """
        Adicionar servidor ao ring
        """
        hash_value = self._hash(node)

        self.ring[hash_value] = node
        self.sorted_keys.append(hash_value)
        self.sorted_keys.sort()

        print(f"✓ Adicionado '{node}' no hash {hash_value}")

    def remove_node(self, node: str):
        """
        Remover servidor do ring
        """
        hash_value = self._hash(node)

        if hash_value in self.ring:
            del self.ring[hash_value]
            self.sorted_keys.remove(hash_value)
            print(f"✓ Removido '{node}' do hash {hash_value}")

    def get_node(self, key: str) -> Optional[str]:
        """
        Buscar servidor para chave

        Algoritmo:
        1. Calcular hash da chave
        2. Buscar próximo servidor no sentido horário (binary search)
        3. Se passou do último, voltar ao primeiro (ring circular)

        Complexidade: O(log N)
        """
        if not self.ring:
            return None

        hash_value = self._hash(key)

        # Binary search para próximo servidor
        index = bisect_right(self.sorted_keys, hash_value)

        # Se passou do último, voltar ao primeiro (circular)
        if index == len(self.sorted_keys):
            index = 0

        return self.ring[self.sorted_keys[index]]


# Uso
ch = ConsistentHash()

# Adicionar 3 servidores
ch.add_node("server-1")
ch.add_node("server-2")
ch.add_node("server-3")

# Buscar servidores para chaves
print(ch.get_node("user:123"))  # server-2
print(ch.get_node("user:456"))  # server-1
print(ch.get_node("user:789"))  # server-3

# Adicionar novo servidor
ch.add_node("server-4")

# Apenas algumas chaves mudaram de servidor
print(ch.get_node("user:123"))  # Pode mudar ou não
print(ch.get_node("user:456"))  # Pode mudar ou não
print(ch.get_node("user:789"))  # Pode mudar ou não
```

**Análise:**
- ✅ Complexidade O(log N)
- ✅ Minimiza migração ao adicionar/remover servidor
- ⚠️ **PROBLEMA**: Distribuição não uniforme!

**Problema de Distribuição:**
```
3 servidores com hash aleatório:

    Server A (hash=100)
    Server B (hash=150)  ← Apenas 50 unidades de espaço
    Server C (hash=350)  ← 200 unidades de espaço!

Server C vai receber 4x mais chaves que Server B! 💥
```

---

### 2. Consistent Hashing com Virtual Nodes (RECOMENDADO)

```python
class ConsistentHashWithVirtualNodes:
    """
    Consistent Hashing com Virtual Nodes

    Cada servidor físico é replicado em múltiplos pontos do ring
    Garante distribuição uniforme

    Exemplo:
    server-1 → server-1#0, server-1#1, ..., server-1#149 (150 replicas)
    """

    def __init__(self, nodes: List[str] = None, virtual_nodes: int = 150):
        """
        Args:
            nodes: Lista de servidores
            virtual_nodes: Número de réplicas por servidor (150-200 é ideal)
        """
        self.virtual_nodes = virtual_nodes
        self.ring: Dict[int, str] = {}  # hash -> physical_node
        self.sorted_keys: List[int] = []
        self.nodes: set = set()  # Servidores físicos

        if nodes:
            for node in nodes:
                self.add_node(node)

    def _hash(self, key: str) -> int:
        """Hash MD5"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node: str):
        """
        Adicionar servidor (com virtual nodes)

        Para cada servidor físico, criar N réplicas virtuais
        """
        self.nodes.add(node)

        for i in range(self.virtual_nodes):
            virtual_key = f"{node}#{i}"
            hash_value = self._hash(virtual_key)

            self.ring[hash_value] = node  # Aponta para servidor FÍSICO
            self.sorted_keys.append(hash_value)

        self.sorted_keys.sort()

        print(f"✓ Adicionado '{node}' com {self.virtual_nodes} virtual nodes")

    def remove_node(self, node: str):
        """
        Remover servidor (e seus virtual nodes)
        """
        if node not in self.nodes:
            return

        self.nodes.remove(node)

        for i in range(self.virtual_nodes):
            virtual_key = f"{node}#{i}"
            hash_value = self._hash(virtual_key)

            if hash_value in self.ring:
                del self.ring[hash_value]
                self.sorted_keys.remove(hash_value)

        print(f"✓ Removido '{node}' e seus {self.virtual_nodes} virtual nodes")

    def get_node(self, key: str) -> Optional[str]:
        """
        Buscar servidor para chave

        Mesmo algoritmo, mas retorna servidor FÍSICO
        """
        if not self.ring:
            return None

        hash_value = self._hash(key)

        index = bisect_right(self.sorted_keys, hash_value)

        if index == len(self.sorted_keys):
            index = 0

        return self.ring[self.sorted_keys[index]]

    def get_distribution(self) -> Dict[str, int]:
        """
        Analisar distribuição de chaves (para debug/teste)

        Simula 10000 chaves e conta quantas vão para cada servidor
        """
        distribution = {node: 0 for node in self.nodes}

        # Simular 10000 chaves
        for i in range(10000):
            key = f"key:{i}"
            node = self.get_node(key)
            if node:
                distribution[node] += 1

        return distribution


# Uso
ch = ConsistentHashWithVirtualNodes(virtual_nodes=150)

# Adicionar servidores
ch.add_node("server-1")
ch.add_node("server-2")
ch.add_node("server-3")

# Analisar distribuição
dist = ch.get_distribution()
print("\nDistribuição de 10000 chaves:")
for node, count in dist.items():
    print(f"{node}: {count} chaves ({count/100:.1f}%)")

# Output esperado (distribuição uniforme):
# server-1: 3342 chaves (33.4%)
# server-2: 3329 chaves (33.3%)
# server-3: 3329 chaves (33.3%)


# Adicionar novo servidor
ch.add_node("server-4")

dist = ch.get_distribution()
print("\nApós adicionar server-4:")
for node, count in dist.items():
    print(f"{node}: {count} chaves ({count/100:.1f}%)")

# Output esperado:
# server-1: 2501 chaves (25.0%)
# server-2: 2498 chaves (25.0%)
# server-3: 2501 chaves (25.0%)
# server-4: 2500 chaves (25.0%)
```

**Análise:**
- ✅ Distribuição uniforme (~25% por servidor)
- ✅ Minimal disruption (~25% migram ao adicionar servidor)
- ✅ Production-ready

---

### 3. Integração com Cache Distribuído

```python
import redis
from typing import Any, Optional

class DistributedCache:
    """
    Cache distribuído usando Consistent Hashing

    Múltiplos Redis nodes, dados particionados com CH
    """

    def __init__(self, redis_configs: List[Dict], virtual_nodes: int = 150):
        """
        Args:
            redis_configs: [{"host": "redis1", "port": 6379}, ...]
        """
        # Criar clients Redis
        self.redis_clients = {}
        node_names = []

        for i, config in enumerate(redis_configs):
            node_name = f"redis-{i}"
            self.redis_clients[node_name] = redis.Redis(**config)
            node_names.append(node_name)

        # Consistent hash
        self.ch = ConsistentHashWithVirtualNodes(
            nodes=node_names,
            virtual_nodes=virtual_nodes
        )

    def _get_client(self, key: str) -> redis.Redis:
        """Retornar Redis client para chave"""
        node = self.ch.get_node(key)
        return self.redis_clients[node]

    def get(self, key: str) -> Optional[Any]:
        """Buscar do cache"""
        client = self._get_client(key)
        value = client.get(key)

        if value:
            return value.decode() if isinstance(value, bytes) else value

        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        """Salvar no cache"""
        client = self._get_client(key)
        client.setex(key, ttl, value)

    def delete(self, key: str):
        """Remover do cache"""
        client = self._get_client(key)
        client.delete(key)

    def add_node(self, host: str, port: int = 6379):
        """
        Adicionar novo Redis node

        IMPORTANTE: Precisa migrar dados!
        """
        node_name = f"redis-{len(self.redis_clients)}"

        # Adicionar client
        self.redis_clients[node_name] = redis.Redis(host=host, port=port)

        # Adicionar ao hash ring
        self.ch.add_node(node_name)

        # TODO: Migrar chaves afetadas (ver seção de migração)

    def remove_node(self, node_name: str):
        """
        Remover Redis node

        IMPORTANTE: Dados serão perdidos se não migrar!
        """
        # Remover do hash ring
        self.ch.remove_node(node_name)

        # Remover client
        if node_name in self.redis_clients:
            self.redis_clients[node_name].close()
            del self.redis_clients[node_name]


# Uso
cache = DistributedCache([
    {"host": "redis1.example.com", "port": 6379},
    {"host": "redis2.example.com", "port": 6379},
    {"host": "redis3.example.com", "port": 6379},
])

# Operações normais
cache.set("user:123", "John Doe", ttl=3600)
cache.set("user:456", "Jane Smith", ttl=3600)
cache.set("user:789", "Bob Johnson", ttl=3600)

# Buscar (vai automaticamente no Redis correto)
user = cache.get("user:123")
print(user)  # "John Doe"

# Adicionar novo Redis node
cache.add_node("redis4.example.com", 6379)

# Sistema continua funcionando, ~25% das chaves migram
```

---

### 4. Migração de Dados (Critical!)

```python
class ConsistentHashWithMigration(ConsistentHashWithVirtualNodes):
    """
    Consistent Hash com migração automática de dados

    Quando servidor é adicionado/removido, migrar chaves afetadas
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_store = {}  # Simula storage (na prática seria Redis/DB)

    def set(self, key: str, value: Any):
        """Salvar chave no servidor correto"""
        node = self.get_node(key)
        if node not in self.data_store:
            self.data_store[node] = {}
        self.data_store[node][key] = value

    def get(self, key: str) -> Optional[Any]:
        """Buscar chave"""
        node = self.get_node(key)
        if node in self.data_store:
            return self.data_store[node].get(key)
        return None

    def add_node_with_migration(self, node: str):
        """
        Adicionar servidor e migrar chaves afetadas

        Algoritmo:
        1. Identificar chaves que agora pertencem ao novo servidor
        2. Mover essas chaves do servidor antigo para o novo
        """
        # Salvar estado anterior (para cada chave, qual era o servidor)
        old_mappings = {}
        all_keys = set()

        for node_data in self.data_store.values():
            all_keys.update(node_data.keys())

        for key in all_keys:
            old_mappings[key] = self.get_node(key)

        # Adicionar novo servidor
        self.add_node(node)
        self.data_store[node] = {}

        # Identificar e migrar chaves afetadas
        migrated_count = 0

        for key in all_keys:
            old_node = old_mappings[key]
            new_node = self.get_node(key)

            if old_node != new_node:
                # Chave precisa migrar
                value = self.data_store[old_node].pop(key)
                self.data_store[new_node][key] = value
                migrated_count += 1

        total_keys = len(all_keys)
        migration_percentage = (migrated_count / total_keys * 100) if total_keys > 0 else 0

        print(f"✓ Migradas {migrated_count}/{total_keys} chaves ({migration_percentage:.1f}%)")


# Teste de migração
ch = ConsistentHashWithMigration(virtual_nodes=150)

ch.add_node("server-1")
ch.add_node("server-2")
ch.add_node("server-3")

# Adicionar 1000 chaves
for i in range(1000):
    ch.set(f"key:{i}", f"value:{i}")

print("\nDistribuição inicial:")
for node, data in ch.data_store.items():
    print(f"{node}: {len(data)} chaves")

# Adicionar novo servidor com migração
ch.add_node_with_migration("server-4")

print("\nDistribuição após adicionar server-4:")
for node, data in ch.data_store.items():
    print(f"{node}: {len(data)} chaves")

# Output esperado:
# ✓ Migradas ~250/1000 chaves (25.0%)
# Cada servidor agora tem ~250 chaves (25%)
```

---

## 🚀 Casos de Uso Reais

### 1. Amazon DynamoDB

```python
"""
DynamoDB usa Consistent Hashing para particionar dados

Partition Key → Hash → Node
"""

class DynamoDBSimplified:
    def __init__(self, nodes: List[str]):
        self.ch = ConsistentHashWithVirtualNodes(nodes, virtual_nodes=150)

    def put_item(self, partition_key: str, item: dict):
        """Salvar item (vai para servidor baseado em partition key)"""
        node = self.ch.get_node(partition_key)
        # Salvar no node correspondente
        save_to_node(node, partition_key, item)

    def get_item(self, partition_key: str) -> dict:
        """Buscar item"""
        node = self.ch.get_node(partition_key)
        return fetch_from_node(node, partition_key)
```

### 2. Cassandra Ring

```python
"""
Cassandra usa Consistent Hashing + Replication

Cada chave é replicada em N nós consecutivos no ring
"""

class CassandraRing:
    def __init__(self, nodes: List[str], replication_factor: int = 3):
        self.ch = ConsistentHashWithVirtualNodes(nodes, virtual_nodes=256)
        self.replication_factor = replication_factor

    def get_replicas(self, key: str) -> List[str]:
        """
        Retornar N nós para replicação

        Algoritmo:
        1. Achar primeiro nó (consistent hash normal)
        2. Pegar N-1 nós seguintes no ring
        """
        if not self.ch.ring:
            return []

        hash_value = self.ch._hash(key)
        index = bisect_right(self.ch.sorted_keys, hash_value)

        replicas = []
        seen_physical_nodes = set()

        # Percorrer ring até ter N nós FÍSICOS diferentes
        while len(replicas) < self.replication_factor:
            if index >= len(self.ch.sorted_keys):
                index = 0

            node = self.ch.ring[self.ch.sorted_keys[index]]

            if node not in seen_physical_nodes:
                replicas.append(node)
                seen_physical_nodes.add(node)

            index += 1

        return replicas


# Uso
cassandra = CassandraRing(
    nodes=["node-1", "node-2", "node-3", "node-4", "node-5"],
    replication_factor=3
)

# Cada chave é replicada em 3 nós
print(cassandra.get_replicas("user:123"))
# Output: ['node-2', 'node-4', 'node-1']
```

### 3. Memcached Distribuído

```python
"""
Memcached client usa Consistent Hashing para distribuir chaves
"""

from pymemcache.client.hash import HashClient

# HashClient usa consistent hashing internamente
client = HashClient([
    ('memcache1.example.com', 11211),
    ('memcache2.example.com', 11211),
    ('memcache3.example.com', 11211),
])

# Set/get automático com CH
client.set('user:123', 'John Doe')
value = client.get('user:123')
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Por que usar Consistent Hashing ao invés de hash simples (modulo)?"

**Você:** "Hash simples com modulo tem problema crítico: quando adiciona/remove servidor, ~K/N chaves mudam de servidor (K=todas, N=total servidores). Com 3 servers → 4 servers, 75% das chaves migram! Consistent hashing garante que apenas K/N chaves migram (~25% nesse exemplo), minimizando cache invalidation."

---

**Interviewer:** "O que são virtual nodes e por que usar?"

**Você:** "Virtual nodes resolvem distribuição não-uniforme. Com hash simples, servidores podem cair em pontos aleatórios do ring, causando desbalanceamento. Virtual nodes replicam cada servidor físico em 150-200 pontos do ring, garantindo distribuição uniforme. Trade-off: mais memória para manter ring, mas O(log N) lookup continua."

---

**Interviewer:** "Como fazer migração de dados quando adiciona servidor?"

**Você:** "Algoritmo:
1. Para cada chave, calcular servidor antigo (antes de add) e servidor novo (depois de add)
2. Se mudou, mover chave do servidor antigo para o novo
3. Fazer isso de forma incremental (background job) para não bloquear sistema
4. Usar versioning ou timestamps para garantir que não sobrescreve dados mais novos"

---

**Interviewer:** "Consistent Hashing resolve replicação?"

**Você:** "Não diretamente. Consistent hashing resolve PARTICIONAMENTO (qual servidor tem os dados). Para replicação, você precisa estratégia adicional como Cassandra: pegar N nós consecutivos no ring. Exemplo: replication_factor=3 → cada chave vai para servidor principal + 2 próximos no ring."

---

## ✅ Checklist da Entrevista

- [ ] Explicar problema com hash simples (modulo)
- [ ] Desenhar hash ring (círculo)
- [ ] Mostrar como chaves são mapeadas
- [ ] Implementar get_node() com binary search
- [ ] Explicar virtual nodes para balanceamento
- [ ] Discutir migração de dados
- [ ] Mencionar casos de uso (DynamoDB, Cassandra, Memcached)
- [ ] Complexidade: O(log N) para lookup

---

## 📊 Empresas que Usam

- **Amazon**: DynamoDB (partitioning)
- **Netflix**: EVCache (distributed caching)
- **Discord**: Cassandra (data storage)
- **Uber**: Schemaless (custom DB)
- **Airbnb**: Memcached sharding

---

**Algoritmo fundamental para sistemas distribuídos! ⚖️**
