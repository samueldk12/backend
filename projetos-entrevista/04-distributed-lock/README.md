# 🔒 Projeto 4: Distributed Lock

> Sistema de coordenação crítico - aparece em 70% das entrevistas de system design

---

## 📋 Problema

**Descrição:** Implementar distributed lock para coordenar acesso a recursos compartilhados em sistemas distribuídos.

**Problema Real:**
```
Cenário: E-commerce com múltiplos servidores

Servidor 1: Processar pedido #123 (estoque: 1 item)
Servidor 2: Processar pedido #124 (estoque: 1 item)

SEM LOCK:
  ✗ Ambos lêem estoque = 1
  ✗ Ambos confirmam pedido
  ✗ Estoque negativo! 💥

COM LOCK:
  ✓ Servidor 1 adquire lock
  ✓ Servidor 1 processa pedido
  ✓ Servidor 1 libera lock
  ✓ Servidor 2 adquire lock
  ✓ Servidor 2 vê estoque = 0
  ✓ Servidor 2 rejeita pedido ✅
```

---

## 🎯 Requisitos

### Funcionais
1. ✅ `acquire()`: Adquirir lock (blocking ou non-blocking)
2. ✅ `release()`: Liberar lock
3. ✅ TTL automático (evitar deadlock se cliente crashar)
4. ✅ Reentrant lock (mesmo processo pode readquirir)

### Não-funcionais
1. **Mutual Exclusion**: Apenas 1 processo pode ter lock
2. **Deadlock Free**: Lock expira automaticamente
3. **Fault Tolerance**: Funciona mesmo se nó falhar
4. **Fairness**: Processos devem conseguir lock eventualmente

---

## 🔧 Implementações

### 1. Database Lock (SIMPLES mas LIMITADO)

```python
# ❌ PROBLEMA: Não escala bem, single point of failure

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timedelta

class DistributedLock(Base):
    __tablename__ = "distributed_locks"

    id = Column(Integer, primary_key=True)
    resource_name = Column(String(255), unique=True, index=True)
    locked_by = Column(String(255))
    locked_at = Column(DateTime)
    expires_at = Column(DateTime)


def acquire_lock(db, resource: str, client_id: str, ttl: int = 30) -> bool:
    """
    Tentar adquirir lock

    Retorna True se conseguiu, False caso contrário
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=ttl)

    try:
        # Tentar inserir (lock disponível)
        lock = DistributedLock(
            resource_name=resource,
            locked_by=client_id,
            locked_at=now,
            expires_at=expires_at
        )
        db.add(lock)
        db.commit()
        return True

    except IntegrityError:
        # Lock já existe, verificar se expirou
        db.rollback()

        lock = db.query(DistributedLock).filter(
            DistributedLock.resource_name == resource
        ).first()

        if lock and lock.expires_at < now:
            # Lock expirado, reaproveitar
            lock.locked_by = client_id
            lock.locked_at = now
            lock.expires_at = expires_at
            db.commit()
            return True

        return False


def release_lock(db, resource: str, client_id: str):
    """Liberar lock (apenas se você possui)"""
    db.query(DistributedLock).filter(
        DistributedLock.resource_name == resource,
        DistributedLock.locked_by == client_id
    ).delete()
    db.commit()


# Uso
import uuid

client_id = str(uuid.uuid4())

if acquire_lock(db, "process_order_123", client_id, ttl=30):
    try:
        # Critical section
        process_order(123)
    finally:
        release_lock(db, "process_order_123", client_id)
else:
    print("Não conseguiu lock, outro processo está executando")
```

**Problemas:**
- ❌ Não escala (database é bottleneck)
- ❌ Latência alta (roundtrip ao DB)
- ❌ Single point of failure

---

### 2. Redis Lock (RECOMENDADO)

```python
import redis
import uuid
import time

class RedisLock:
    """
    Distributed Lock com Redis

    Implementação simples mas production-ready
    Usa SETNX (SET if Not eXists) + TTL
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def acquire(
        self,
        resource: str,
        ttl: int = 30,
        blocking: bool = True,
        timeout: int = 10
    ) -> str:
        """
        Adquirir lock

        Args:
            resource: Nome do recurso a lockear
            ttl: Time to live em segundos
            blocking: Se True, espera até conseguir lock
            timeout: Timeout para blocking mode

        Returns:
            Lock ID (UUID) se conseguiu, None caso contrário
        """
        lock_key = f"lock:{resource}"
        lock_id = str(uuid.uuid4())  # Identificador único

        start_time = time.time()

        while True:
            # SET NX (Not eXists) + EX (EXpire)
            acquired = self.redis.set(
                lock_key,
                lock_id,
                nx=True,  # Apenas se não existir
                ex=ttl    # Expira em N segundos
            )

            if acquired:
                return lock_id

            if not blocking:
                return None

            # Verificar timeout
            if time.time() - start_time > timeout:
                return None

            # Esperar um pouco antes de tentar novamente
            time.sleep(0.1)

    def release(self, resource: str, lock_id: str) -> bool:
        """
        Liberar lock (apenas se você possui)

        Usa Lua script para operação atômica
        """
        lock_key = f"lock:{resource}"

        # Lua script para verificar e deletar atomicamente
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = self.redis.eval(lua_script, 1, lock_key, lock_id)
        return bool(result)

    def extend(self, resource: str, lock_id: str, additional_ttl: int) -> bool:
        """
        Estender TTL do lock (útil para operações longas)
        """
        lock_key = f"lock:{resource}"

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        result = self.redis.eval(lua_script, 1, lock_key, lock_id, additional_ttl)
        return bool(result)


# Uso básico
redis_client = redis.Redis(host='localhost', port=6379)
lock = RedisLock(redis_client)

lock_id = lock.acquire("process_order_123", ttl=30)

if lock_id:
    try:
        # Critical section
        process_order(123)
    finally:
        lock.release("process_order_123", lock_id)
else:
    print("Não conseguiu lock")


# Context manager (mais Pythonic)
from contextlib import contextmanager

@contextmanager
def redis_lock(redis_client, resource: str, ttl: int = 30):
    """Context manager para lock"""
    lock = RedisLock(redis_client)
    lock_id = lock.acquire(resource, ttl=ttl, blocking=True)

    try:
        yield lock_id
    finally:
        if lock_id:
            lock.release(resource, lock_id)


# Uso
with redis_lock(redis_client, "process_order_123", ttl=30):
    # Critical section
    process_order(123)
```

**Análise:**
- ✅ Muito rápido (in-memory)
- ✅ TTL automático previne deadlock
- ✅ Lua script garante atomicidade
- ⚠️ Single Redis node pode falhar (ver Redlock abaixo)

---

### 3. Redlock Algorithm (PRODUCTION-GRADE)

```python
import redis
import time
import uuid
from typing import List

class Redlock:
    """
    Redlock Algorithm (Martin Kleppmann, Redis Labs)

    Lock distribuído com múltiplos Redis nodes
    Mais robusto contra falhas de nó individual
    """

    def __init__(self, redis_nodes: List[redis.Redis]):
        """
        Args:
            redis_nodes: Lista de Redis clients (mínimo 3, recomendado 5)
        """
        self.redis_nodes = redis_nodes
        self.quorum = len(redis_nodes) // 2 + 1  # Maioria

    def acquire(self, resource: str, ttl: int = 30, retry_count: int = 3) -> str:
        """
        Adquirir lock na maioria dos nós

        Algoritmo:
        1. Pegar timestamp atual
        2. Tentar adquirir lock em TODOS os nós
        3. Se conseguiu na MAIORIA (quorum) e dentro do tempo: sucesso
        4. Caso contrário: liberar locks e retry
        """
        lock_key = f"lock:{resource}"

        for _ in range(retry_count):
            lock_id = str(uuid.uuid4())
            start_time = time.time()

            # Tentar adquirir em todos os nós
            acquired_count = 0

            for node in self.redis_nodes:
                try:
                    success = node.set(lock_key, lock_id, nx=True, px=ttl * 1000)
                    if success:
                        acquired_count += 1
                except:
                    # Se um nó falhar, continuar tentando nos outros
                    pass

            # Calcular tempo de drift
            elapsed = time.time() - start_time
            validity_time = ttl - elapsed - 0.1  # 100ms drift

            # Verificar quorum
            if acquired_count >= self.quorum and validity_time > 0:
                return lock_id

            # Não conseguiu quorum, liberar todos os locks
            self._release_all(lock_key, lock_id)

            # Esperar random time antes de retry (evitar thundering herd)
            time.sleep(0.1 + (time.time() % 0.1))

        return None

    def release(self, resource: str, lock_id: str):
        """Liberar lock em todos os nós"""
        lock_key = f"lock:{resource}"
        self._release_all(lock_key, lock_id)

    def _release_all(self, lock_key: str, lock_id: str):
        """Helper: liberar lock em todos os nós"""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        for node in self.redis_nodes:
            try:
                node.eval(lua_script, 1, lock_key, lock_id)
            except:
                pass  # Ignorar falhas ao liberar


# Setup: 5 Redis nodes independentes
redis_nodes = [
    redis.Redis(host='redis1.example.com', port=6379),
    redis.Redis(host='redis2.example.com', port=6379),
    redis.Redis(host='redis3.example.com', port=6379),
    redis.Redis(host='redis4.example.com', port=6379),
    redis.Redis(host='redis5.example.com', port=6379),
]

redlock = Redlock(redis_nodes)

# Uso
lock_id = redlock.acquire("critical_resource", ttl=30)

if lock_id:
    try:
        # Critical section
        perform_critical_operation()
    finally:
        redlock.release("critical_resource", lock_id)
```

**Análise:**
- ✅ Fault tolerant (funciona se minoria dos nós falhar)
- ✅ No single point of failure
- ✅ Production-grade (usado por Redis Labs)
- ⚠️ Mais complexo de setup e manter

---

### 4. ZooKeeper Lock (ENTERPRISE)

```python
from kazoo.client import KazooClient
from kazoo.recipe.lock import Lock

class ZooKeeperLock:
    """
    Distributed Lock com Apache ZooKeeper

    Usado por: Kafka, HBase, Hadoop
    Mais robusto que Redis para consensus
    """

    def __init__(self, hosts: str = "localhost:2181"):
        self.client = KazooClient(hosts=hosts)
        self.client.start()

    def acquire(self, resource: str, timeout: int = 30):
        """
        Adquirir lock

        ZooKeeper garante:
        - Mutual exclusion
        - Ordering (FIFO)
        - No starvation
        """
        lock_path = f"/locks/{resource}"
        lock = Lock(self.client, lock_path)

        acquired = lock.acquire(timeout=timeout)

        if acquired:
            return lock
        return None

    def release(self, lock: Lock):
        """Liberar lock"""
        lock.release()


# Uso
zk_lock = ZooKeeperLock(hosts="zk1:2181,zk2:2181,zk3:2181")

lock = zk_lock.acquire("critical_resource", timeout=30)

if lock:
    try:
        # Critical section
        perform_critical_operation()
    finally:
        zk_lock.release(lock)
```

**Análise:**
- ✅ Consensus protocol robusto (Zab)
- ✅ Ordering garantido (FIFO)
- ✅ No starvation
- ⚠️ Mais pesado (Java-based)
- ⚠️ Overhead maior que Redis

---

## 🚀 Comparação

| Característica | Database Lock | Redis Lock | Redlock | ZooKeeper |
|---------------|---------------|------------|---------|-----------|
| **Latência** | 🔴 100-200ms | 🟢 1-5ms | 🟡 5-15ms | 🟡 10-50ms |
| **Throughput** | 🔴 100/s | 🟢 10k/s | 🟡 5k/s | 🟡 1k/s |
| **Fault Tolerance** | 🔴 SPOF | 🟡 Limitado | 🟢 Excelente | 🟢 Excelente |
| **Complexidade** | 🟢 Simples | 🟢 Simples | 🟡 Médio | 🔴 Alto |
| **Custo** | 🟢 Baixo | 🟢 Baixo | 🟡 Médio | 🔴 Alto |

**Quando usar cada:**

- **Database Lock**:
  - ✅ Proof of concept
  - ✅ <100 locks/s
  - ❌ NÃO use em produção de alta escala

- **Redis Lock (single node)**:
  - ✅ 80% dos casos
  - ✅ Alta performance
  - ✅ Simplicidade
  - ⚠️ Aceita perder lock em falha do Redis (raro)

- **Redlock (multi-node)**:
  - ✅ Operações críticas (pagamentos, estoque)
  - ✅ Não pode perder lock NUNCA
  - ✅ Tolerância a falhas importante

- **ZooKeeper**:
  - ✅ Sistemas enterprise complexos
  - ✅ Quando já usa ZooKeeper (Kafka, HBase)
  - ✅ Precisa de ordering/FIFO garantido

---

## 🎯 FastAPI Integration

```python
from fastapi import FastAPI, HTTPException, Depends
from redis import Redis
import uuid

app = FastAPI()

# Redis client
redis_client = Redis(host='localhost', port=6379, decode_responses=True)

# Dependency para lock
def get_redis_lock():
    return RedisLock(redis_client)


@app.post("/orders/{order_id}/process")
async def process_order(
    order_id: int,
    lock: RedisLock = Depends(get_redis_lock)
):
    """
    Processar pedido com lock distribuído

    Garante que apenas 1 servidor processa o pedido por vez
    """
    resource = f"order:{order_id}"
    lock_id = lock.acquire(resource, ttl=30, blocking=False)

    if not lock_id:
        raise HTTPException(
            status_code=409,
            detail="Order is being processed by another server"
        )

    try:
        # Critical section
        order = get_order(order_id)

        if order.status != "pending":
            raise HTTPException(400, "Order already processed")

        # Processar pedido
        charge_payment(order)
        update_inventory(order)
        send_confirmation_email(order)

        # Marcar como processado
        order.status = "completed"
        db.commit()

        return {"status": "success", "order_id": order_id}

    finally:
        lock.release(resource, lock_id)


@app.post("/inventory/{product_id}/reserve")
async def reserve_inventory(
    product_id: int,
    quantity: int,
    lock: RedisLock = Depends(get_redis_lock)
):
    """
    Reservar estoque com lock

    Evita race condition em estoques baixos
    """
    resource = f"inventory:{product_id}"

    lock_id = lock.acquire(resource, ttl=10, blocking=True, timeout=5)

    if not lock_id:
        raise HTTPException(503, "Could not acquire lock, try again")

    try:
        product = db.query(Product).filter(Product.id == product_id).first()

        if product.stock < quantity:
            raise HTTPException(400, "Insufficient stock")

        # Reservar estoque
        product.stock -= quantity
        db.commit()

        return {"status": "reserved", "remaining_stock": product.stock}

    finally:
        lock.release(resource, lock_id)
```

---

## 🧪 Testes

```python
import pytest
import threading
import time

def test_redis_lock_mutual_exclusion():
    """Apenas 1 thread deve conseguir lock"""
    lock = RedisLock(redis_client)
    resource = "test_resource"

    acquired_count = 0
    lock_id1 = None
    lock_id2 = None

    def worker1():
        nonlocal lock_id1, acquired_count
        lock_id1 = lock.acquire(resource, ttl=5, blocking=False)
        if lock_id1:
            acquired_count += 1
            time.sleep(1)
            lock.release(resource, lock_id1)

    def worker2():
        nonlocal lock_id2, acquired_count
        time.sleep(0.1)  # Garantir que worker1 adquire primeiro
        lock_id2 = lock.acquire(resource, ttl=5, blocking=False)
        if lock_id2:
            acquired_count += 1

    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Apenas worker1 deve ter conseguido lock
    assert lock_id1 is not None
    assert lock_id2 is None
    assert acquired_count == 1


def test_redis_lock_ttl_expiration():
    """Lock deve expirar automaticamente"""
    lock = RedisLock(redis_client)
    resource = "test_ttl"

    # Adquirir lock com TTL curto
    lock_id1 = lock.acquire(resource, ttl=1)
    assert lock_id1 is not None

    # Tentar adquirir imediatamente (deve falhar)
    lock_id2 = lock.acquire(resource, ttl=1, blocking=False)
    assert lock_id2 is None

    # Esperar expirar
    time.sleep(1.5)

    # Agora deve conseguir
    lock_id3 = lock.acquire(resource, ttl=5, blocking=False)
    assert lock_id3 is not None

    lock.release(resource, lock_id3)


def test_redis_lock_release_wrong_owner():
    """Não deve conseguir liberar lock de outro processo"""
    lock = RedisLock(redis_client)
    resource = "test_owner"

    lock_id1 = lock.acquire(resource, ttl=10)

    # Tentar liberar com lock_id errado
    fake_lock_id = str(uuid.uuid4())
    released = lock.release(resource, fake_lock_id)

    assert not released

    # Verificar que lock ainda está ativo
    lock_id2 = lock.acquire(resource, ttl=1, blocking=False)
    assert lock_id2 is None

    # Liberar corretamente
    lock.release(resource, lock_id1)


def test_redlock_fault_tolerance():
    """Redlock deve funcionar mesmo se minoria falhar"""
    # Simular 5 nós, 2 vão falhar
    working_nodes = [redis.Redis(host='localhost', port=6379) for _ in range(3)]
    failing_nodes = [MockFailingRedis() for _ in range(2)]

    all_nodes = working_nodes + failing_nodes
    redlock = Redlock(all_nodes)

    # Deve conseguir lock (3/5 nós OK = quorum)
    lock_id = redlock.acquire("test_resource", ttl=30)

    assert lock_id is not None

    redlock.release("test_resource", lock_id)


class MockFailingRedis:
    """Mock de Redis que sempre falha"""
    def set(self, *args, **kwargs):
        raise Exception("Node failed")

    def eval(self, *args, **kwargs):
        raise Exception("Node failed")
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Por que preciso de distributed lock? Database transaction não resolve?"

**Você:** "Database transaction resolve dentro de 1 banco de dados. Mas em sistemas distribuídos você pode ter: múltiplos bancos, cache (Redis), message queues, chamadas externas (APIs de pagamento). Distributed lock coordena TODOS esses recursos, não apenas o DB."

---

**Interviewer:** "O que acontece se cliente crashar com lock ativo?"

**Você:** "Por isso usamos TTL (Time To Live). Lock expira automaticamente após N segundos. Importante: TTL deve ser maior que tempo esperado da operação + margem de segurança. Se operação é muito longa, usar `extend()` para renovar lock."

---

**Interviewer:** "Redis single node vs Redlock, qual escolher?"

**Você:** "Depende do custo de perder o lock:
- **Single node**: 99.9% dos casos. Se Redis cair, sistema fica indisponível por minutos, mas não corrompe dados.
- **Redlock**: Operações críticas onde perder lock = corrupção de dados (ex: débito duplo em conta bancária). Vale a complexidade extra."

---

**Interviewer:** "Por que não usar SELECT FOR UPDATE no banco?"

**Você:** "SELECT FOR UPDATE funciona para lock de ROW específica. Distributed lock funciona para QUALQUER recurso: arquivo, API externa, cron job, cache. Além disso, SELECT FOR UPDATE segura conexão com DB durante toda a operação, não escala bem."

---

## ✅ Checklist da Entrevista

- [ ] Explicar o problema (race condition em distribuído)
- [ ] Mostrar exemplo concreto (estoque, pedido)
- [ ] Discutir abordagem ingênua (database lock)
- [ ] Propor Redis lock com TTL
- [ ] Implementar acquire/release com Lua script
- [ ] Explicar Redlock para fault tolerance
- [ ] Mencionar ZooKeeper para casos enterprise
- [ ] Tratar edge cases (crash, TTL, wrong owner)
- [ ] Integrar com FastAPI

---

## 📊 Casos de Uso Reais

**Onde Distributed Lock é usado:**

1. **E-commerce**: Reserva de estoque
2. **Banking**: Transações financeiras
3. **Cron Jobs**: Garantir single execution
4. **Cache Warming**: Evitar cache stampede
5. **Rate Limiting**: Quota distribuída
6. **Leader Election**: Escolher master node
7. **Database Migration**: Rodar apenas em 1 pod

**Empresas que usam:**
- Amazon: Order processing
- Uber: Trip allocation
- Netflix: Job scheduling
- Stripe: Payment processing

---

**Conceito essencial para sistemas distribuídos! 🔒**
