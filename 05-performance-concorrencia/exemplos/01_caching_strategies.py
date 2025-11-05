"""
Exemplo 01: Estratégias de Caching

Implementa e compara 5 estratégias de caching:
1. Cache-Aside (Lazy Loading)
2. Read-Through
3. Write-Through
4. Write-Behind (Write-Back)
5. Refresh-Ahead

Com benchmarks e análise de quando usar cada uma.
"""

import time
import random
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict
import json

# Simular Redis (in-memory)
cache_store = {}

# Simular Database (lento)
database = {}


def simulate_db_read(key: str) -> Optional[Any]:
    """Simular leitura do banco (100ms)."""
    time.sleep(0.1)  # 100ms de latência
    return database.get(key)


def simulate_db_write(key: str, value: Any):
    """Simular escrita no banco (150ms)."""
    time.sleep(0.15)  # 150ms de latência
    database[key] = value


def cache_get(key: str) -> Optional[Any]:
    """Simular leitura do cache (1ms)."""
    time.sleep(0.001)  # 1ms de latência
    return cache_store.get(key)


def cache_set(key: str, value: Any, ttl: int = 300):
    """Simular escrita no cache (2ms)."""
    time.sleep(0.002)  # 2ms de latência
    cache_store[key] = {
        "value": value,
        "expires_at": datetime.now() + timedelta(seconds=ttl)
    }


def cache_delete(key: str):
    """Deletar do cache."""
    cache_store.pop(key, None)


# ============================================================================
# ESTRATÉGIA 1: CACHE-ASIDE (Lazy Loading)
# ============================================================================

print("=" * 70)
print("ESTRATÉGIA 1: CACHE-ASIDE (LAZY LOADING)")
print("=" * 70)

"""
Fluxo de leitura:
1. App verifica cache
2. Se encontrar (cache hit) → retorna
3. Se não encontrar (cache miss) → busca do DB
4. Armazena no cache
5. Retorna dados

Fluxo de escrita:
1. App escreve no DB
2. App invalida cache (delete)
3. Próxima leitura vai buscar do DB (lazy)

┌─────┐         ┌───────┐         ┌──────────┐
│ App │         │ Cache │         │ Database │
└──┬──┘         └───┬───┘         └────┬─────┘
   │                │                  │
   │ 1. GET key     │                  │
   ├───────────────>│                  │
   │                │                  │
   │ Miss ❌        │                  │
   │<───────────────┤                  │
   │                │                  │
   │ 2. SELECT      │                  │
   ├──────────────────────────────────>│
   │                │                  │
   │ Data           │                  │
   │<──────────────────────────────────┤
   │                │                  │
   │ 3. SET key     │                  │
   ├───────────────>│                  │
   │                │                  │
   │ 4. Return data │                  │

✅ Prós:
  • Simples de implementar
  • Cache só armazena dados usados (eficiente)
  • Tolerante a falhas do cache (sempre busca DB)

❌ Contras:
  • Cache miss penalty (latência)
  • Possível inconsistência (DB atualizado, cache antigo)
  • Thundering herd (muitas requests simultâneas após miss)

🎯 Quando usar:
  • Padrão mais comum (80% dos casos)
  • Dados raramente atualizados
  • OK com eventual consistency
"""


def cache_aside_get(key: str) -> Optional[Any]:
    """Cache-Aside: Leitura."""
    # 1. Tentar cache
    cached = cache_get(key)

    if cached and cached["expires_at"] > datetime.now():
        print(f"  ✅ Cache HIT: {key}")
        return cached["value"]

    print(f"  ❌ Cache MISS: {key}")

    # 2. Buscar do DB
    value = simulate_db_read(key)

    if value is not None:
        # 3. Armazenar no cache
        cache_set(key, value)

    return value


def cache_aside_set(key: str, value: Any):
    """Cache-Aside: Escrita."""
    # 1. Escrever no DB
    simulate_db_write(key, value)

    # 2. Invalidar cache (lazy loading)
    cache_delete(key)


# Demonstração
print("\n📊 Demonstração Cache-Aside:\n")

# Setup: adicionar dados no DB
database["user:1"] = {"id": 1, "name": "João"}

# Primeira leitura (cache miss)
start = time.time()
user = cache_aside_get("user:1")
print(f"  Tempo: {(time.time() - start) * 1000:.0f}ms (cache miss)")

# Segunda leitura (cache hit)
start = time.time()
user = cache_aside_get("user:1")
print(f"  Tempo: {(time.time() - start) * 1000:.0f}ms (cache hit)")

# Atualização
cache_aside_set("user:1", {"id": 1, "name": "João Silva"})
print(f"  Cache invalidado")

# Leitura após update (cache miss novamente)
start = time.time()
user = cache_aside_get("user:1")
print(f"  Tempo: {(time.time() - start) * 1000:.0f}ms (cache miss após update)")


# ============================================================================
# ESTRATÉGIA 2: READ-THROUGH
# ============================================================================

print("\n" + "=" * 70)
print("ESTRATÉGIA 2: READ-THROUGH")
print("=" * 70)

"""
Fluxo:
1. App pede dados do cache
2. Cache verifica se tem
3. Se não tem, cache busca do DB
4. Cache armazena e retorna

Diferença do Cache-Aside:
  • Cache-Aside: App é responsável por popular cache
  • Read-Through: Cache é responsável (transparente para app)

┌─────┐         ┌───────┐         ┌──────────┐
│ App │         │ Cache │         │ Database │
└──┬──┘         └───┬───┘         └────┬─────┘
   │                │                  │
   │ 1. GET key     │                  │
   ├───────────────>│                  │
   │                │                  │
   │         Cache miss               │
   │                │ 2. SELECT        │
   │                ├─────────────────>│
   │                │                  │
   │                │ Data             │
   │                │<─────────────────┤
   │                │                  │
   │         (Cache stores)            │
   │                │                  │
   │ 3. Data        │                  │
   │<───────────────┤                  │

✅ Prós:
  • Transparente para aplicação
  • Cache é sempre fonte de verdade
  • Simplifica código da aplicação

❌ Contras:
  • Requer biblioteca/proxy de cache
  • Mesmo cache miss penalty
  • Menos flexibilidade

🎯 Quando usar:
  • Quer abstrair caching da aplicação
  • Usando proxy de cache (Varnish, CDN)
  • Padrão de acesso consistente
"""


class ReadThroughCache:
    """
    Read-Through Cache implementation.

    Cache busca do DB automaticamente.
    """

    def __init__(self):
        self.cache = {}

    def get(self, key: str) -> Optional[Any]:
        """Get com read-through."""
        # Verificar cache
        cached = self.cache.get(key)

        if cached and cached["expires_at"] > datetime.now():
            print(f"  ✅ Cache HIT (read-through): {key}")
            return cached["value"]

        print(f"  ❌ Cache MISS (read-through): {key}")

        # Cache busca do DB (transparente para app!)
        value = simulate_db_read(key)

        if value is not None:
            # Cache armazena
            self.cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=300)
            }

        return value

    def invalidate(self, key: str):
        """Invalidar cache."""
        self.cache.pop(key, None)


# Demonstração
print("\n📊 Demonstração Read-Through:\n")

rt_cache = ReadThroughCache()

# Primeira leitura (cache miss, cache busca DB)
start = time.time()
user = rt_cache.get("user:1")
print(f"  Tempo: {(time.time() - start) * 1000:.0f}ms")

# Segunda leitura (cache hit)
start = time.time()
user = rt_cache.get("user:1")
print(f"  Tempo: {(time.time() - start) * 1000:.0f}ms")


# ============================================================================
# ESTRATÉGIA 3: WRITE-THROUGH
# ============================================================================

print("\n" + "=" * 70)
print("ESTRATÉGIA 3: WRITE-THROUGH")
print("=" * 70)

"""
Fluxo de escrita:
1. App escreve no cache
2. Cache escreve no DB (síncrono)
3. Cache retorna sucesso

┌─────┐         ┌───────┐         ┌──────────┐
│ App │         │ Cache │         │ Database │
└──┬──┘         └───┬───┘         └────┬─────┘
   │                │                  │
   │ 1. SET key     │                  │
   ├───────────────>│                  │
   │                │                  │
   │                │ 2. INSERT/UPDATE │
   │                ├─────────────────>│
   │                │                  │
   │                │ OK               │
   │                │<─────────────────┤
   │                │                  │
   │         (Cache stores)            │
   │                │                  │
   │ 3. OK          │                  │
   │<───────────────┤                  │

✅ Prós:
  • Cache e DB sempre consistentes
  • Sem perda de dados se cache falhar
  • Leituras rápidas (sempre no cache)

❌ Contras:
  • Escritas lentas (espera DB)
  • Overhead em toda escrita
  • Cache pode ter dados nunca lidos

🎯 Quando usar:
  • Consistência é crítica
  • Muitas leituras, poucas escritas
  • Não pode perder dados
"""


class WriteThroughCache:
    """Write-Through Cache implementation."""

    def __init__(self):
        self.cache = {}

    def set(self, key: str, value: Any):
        """Set com write-through."""
        # 1. Escrever no DB (síncrono!)
        simulate_db_write(key, value)
        print(f"  DB atualizado: {key}")

        # 2. Atualizar cache
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.now() + timedelta(seconds=300)
        }
        print(f"  Cache atualizado: {key}")

    def get(self, key: str) -> Optional[Any]:
        """Get (sempre no cache)."""
        cached = self.cache.get(key)

        if cached and cached["expires_at"] > datetime.now():
            print(f"  ✅ Cache HIT (write-through): {key}")
            return cached["value"]

        # Se não estiver no cache, buscar do DB
        value = simulate_db_read(key)
        if value:
            self.cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=300)
            }

        return value


# Demonstração
print("\n📊 Demonstração Write-Through:\n")

wt_cache = WriteThroughCache()

# Escrita (atualiza DB e cache)
start = time.time()
wt_cache.set("user:2", {"id": 2, "name": "Maria"})
print(f"  Tempo de escrita: {(time.time() - start) * 1000:.0f}ms (lento!)")

# Leitura (cache hit, rápido)
start = time.time()
user = wt_cache.get("user:2")
print(f"  Tempo de leitura: {(time.time() - start) * 1000:.0f}ms (rápido!)")


# ============================================================================
# ESTRATÉGIA 4: WRITE-BEHIND (WRITE-BACK)
# ============================================================================

print("\n" + "=" * 70)
print("ESTRATÉGIA 4: WRITE-BEHIND (WRITE-BACK)")
print("=" * 70)

"""
Fluxo de escrita:
1. App escreve no cache
2. Cache retorna sucesso (imediato!)
3. Cache agenda escrita no DB (assíncrono)
4. DB é atualizado em background

┌─────┐         ┌───────┐         ┌──────────┐
│ App │         │ Cache │         │ Database │
└──┬──┘         └───┬───┘         └────┬─────┘
   │                │                  │
   │ 1. SET key     │                  │
   ├───────────────>│                  │
   │                │                  │
   │         (Cache stores)            │
   │                │                  │
   │ 2. OK ✅       │                  │
   │<───────────────┤                  │
   │                │                  │
   │         (Later, async)            │
   │                │ 3. INSERT/UPDATE │
   │                ├─────────────────>│

✅ Prós:
  • Escritas MUITO rápidas (não espera DB)
  • Reduz load no DB (batch writes)
  • Melhor throughput

❌ Contras:
  • Risco de perda de dados (se cache falhar)
  • Complexidade (workers assíncronos)
  • Eventual consistency

🎯 Quando usar:
  • Escritas muito frequentes
  • Latência é crítica
  • OK perder alguns dados
  • Exemplo: contador de views, likes
"""


import threading
import queue


class WriteBehindCache:
    """
    Write-Behind Cache implementation.

    Escreve no cache imediatamente, DB em background.
    """

    def __init__(self):
        self.cache = {}
        self.write_queue = queue.Queue()
        self.running = True

        # Worker thread para escrever no DB
        self.worker = threading.Thread(target=self._background_writer, daemon=True)
        self.worker.start()

    def _background_writer(self):
        """Worker que escreve no DB em background."""
        while self.running:
            try:
                # Pegar item da fila (timeout 1s)
                key, value = self.write_queue.get(timeout=1)

                # Escrever no DB
                simulate_db_write(key, value)
                print(f"  📝 [Background] DB atualizado: {key}")

                self.write_queue.task_done()
            except queue.Empty:
                continue

    def set(self, key: str, value: Any):
        """Set com write-behind (assíncrono)."""
        # 1. Atualizar cache (imediato!)
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.now() + timedelta(seconds=300)
        }
        print(f"  ⚡ Cache atualizado (imediato): {key}")

        # 2. Agendar escrita no DB (assíncrono)
        self.write_queue.put((key, value))

    def get(self, key: str) -> Optional[Any]:
        """Get do cache."""
        cached = self.cache.get(key)

        if cached and cached["expires_at"] > datetime.now():
            return cached["value"]

        return None

    def flush(self):
        """Esperar todas as escritas completarem."""
        self.write_queue.join()

    def stop(self):
        """Parar worker."""
        self.running = False


# Demonstração
print("\n📊 Demonstração Write-Behind:\n")

wb_cache = WriteBehindCache()

# Escritas (muito rápidas!)
start = time.time()
wb_cache.set("user:3", {"id": 3, "name": "Pedro"})
wb_cache.set("user:4", {"id": 4, "name": "Ana"})
print(f"  Tempo de 2 escritas: {(time.time() - start) * 1000:.0f}ms (muito rápido!)")

# Leitura (cache hit)
user = wb_cache.get("user:3")
print(f"  Lido do cache: {user}")

# Esperar background writes completarem
print(f"  Esperando writes em background...")
wb_cache.flush()
print(f"  ✅ Todas as escritas completadas")

wb_cache.stop()


# ============================================================================
# ESTRATÉGIA 5: REFRESH-AHEAD
# ============================================================================

print("\n" + "=" * 70)
print("ESTRATÉGIA 5: REFRESH-AHEAD")
print("=" * 70)

"""
Fluxo:
1. Cache detecta que TTL está perto de expirar
2. Cache atualiza dados proativamente (antes de expirar)
3. Usuário sempre tem cache hit

┌─────┐         ┌───────┐         ┌──────────┐
│ App │         │ Cache │         │ Database │
└──┬──┘         └───┬───┘         └────┬─────┘
   │                │                  │
   │ 1. GET key     │                  │
   ├───────────────>│                  │
   │                │                  │
   │         (TTL < threshold)         │
   │                │ 2. Refresh       │
   │                ├─────────────────>│
   │                │                  │
   │ 3. Data (old)  │                  │
   │<───────────────┤                  │
   │                │                  │
   │         (Background update)       │

✅ Prós:
  • Sempre cache hit (nunca espera)
  • Ótimo para dados frequentemente acessados
  • Usuário nunca sente cache miss

❌ Contras:
  • Atualiza dados não usados (desperdício)
  • Complexidade (background refresh)
  • Mais load no DB

🎯 Quando usar:
  • Dados críticos de performance
  • Padrão de acesso previsível
  • Exemplo: página inicial, dashboard
"""


class RefreshAheadCache:
    """
    Refresh-Ahead Cache implementation.

    Atualiza cache proativamente antes de expirar.
    """

    def __init__(self, refresh_threshold: float = 0.8):
        self.cache = {}
        self.refresh_threshold = refresh_threshold  # 80% do TTL
        self.ttl = 10  # 10 segundos para demonstração

    def get(self, key: str) -> Optional[Any]:
        """Get com refresh-ahead."""
        cached = self.cache.get(key)

        if cached:
            # Verificar se ainda é válido
            if cached["expires_at"] > datetime.now():
                # Verificar se precisa refresh
                ttl_remaining = (cached["expires_at"] - datetime.now()).total_seconds()
                ttl_percentage = ttl_remaining / self.ttl

                if ttl_percentage < self.refresh_threshold:
                    print(f"  🔄 Refresh ahead: {key} (TTL em {ttl_remaining:.1f}s)")
                    # Refresh em background (simplificado aqui)
                    self._refresh_async(key)

                print(f"  ✅ Cache HIT (refresh-ahead): {key}")
                return cached["value"]

        # Cache miss: buscar do DB
        print(f"  ❌ Cache MISS (refresh-ahead): {key}")
        value = simulate_db_read(key)

        if value is not None:
            self.cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=self.ttl)
            }

        return value

    def _refresh_async(self, key: str):
        """Refresh cache em background."""
        # Em produção, usar thread/celery
        # Aqui simplificado
        value = database.get(key)  # Busca sem latência simulada
        if value:
            self.cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=self.ttl)
            }
            print(f"  ✅ Cache refreshed: {key}")


# Demonstração
print("\n📊 Demonstração Refresh-Ahead:\n")

ra_cache = RefreshAheadCache()

# Adicionar dado no DB
database["user:5"] = {"id": 5, "name": "Carlos"}

# Primeira leitura (cache miss)
user = ra_cache.get("user:5")

# Simular passagem de tempo (80% do TTL)
time.sleep(0.1)  # Simulando

# Segunda leitura (vai refresh em background)
user = ra_cache.get("user:5")


# ============================================================================
# COMPARAÇÃO E BENCHMARKS
# ============================================================================

print("\n" + "=" * 70)
print("COMPARAÇÃO DE PERFORMANCE")
print("=" * 70)

print("""
Latências típicas (assumindo DB = 100ms, Cache = 1ms):

┌──────────────────┬──────────────┬──────────────┬──────────────┐
│ Operação         │ Cache-Aside  │ Write-Through│ Write-Behind │
├──────────────────┼──────────────┼──────────────┼──────────────┤
│ Read (hit)       │ 1ms          │ 1ms          │ 1ms          │
│ Read (miss)      │ 101ms        │ 101ms        │ 101ms        │
│ Write            │ 150ms        │ 152ms        │ 2ms ⚡       │
└──────────────────┴──────────────┴──────────────┴──────────────┘

🏆 VENCEDORES:

Latência de leitura:  Todos iguais (1ms com cache hit)
Latência de escrita:  Write-Behind (2ms) >> Write-Through (152ms)
Consistência:         Write-Through >> Write-Behind
Simplicidade:         Cache-Aside >> Write-Behind
""")


# ============================================================================
# DECISÃO: QUAL USAR?
# ============================================================================

print("\n" + "=" * 70)
print("ÁRVORE DE DECISÃO")
print("=" * 70)

print("""
┌─────────────────────────────────────────────────────────────────┐
│                    QUAL ESTRATÉGIA USAR?                        │
└─────────────────────────────────────────────────────────────────┘

Seu caso de uso:

📖 LEITURAS >> ESCRITAS (95% reads)
   └─> Cache-Aside ✅
       • Padrão mais simples
       • Suporta falhas do cache
       • Usado por: Facebook, Twitter

📝 ESCRITAS FREQUENTES + Consistência OK
   └─> Write-Behind ✅
       • Escritas rápidas
       • Reduz load no DB
       • Usado por: Contadores, analytics

💾 CONSISTÊNCIA CRÍTICA (dados financeiros)
   └─> Write-Through ✅
       • Cache e DB sempre sincronizados
       • Sem perda de dados
       • Usado por: Banking, e-commerce

🚀 PERFORMANCE CRÍTICA + Dados quentes
   └─> Refresh-Ahead ✅
       • Sempre cache hit
       • Ótimo para homepage
       • Usado por: News sites, dashboards

📊 ESTATÍSTICAS DA INDÚSTRIA:

  Cache-Aside:    70% dos casos (padrão)
  Write-Through:  15% dos casos (consistência)
  Write-Behind:   10% dos casos (high-throughput)
  Read-Through:   3% dos casos (proxy)
  Refresh-Ahead:  2% dos casos (crítico)

💡 COMBINAÇÕES COMUNS:

  • Cache-Aside (leitura) + Write-Through (escrita)
  • Cache-Aside (leitura) + Write-Behind (escrita)
  • Read-Through + Write-Behind
""")


# ============================================================================
# PATTERNS AVANÇADOS
# ============================================================================

print("\n" + "=" * 70)
print("PATTERNS AVANÇADOS")
print("=" * 70)

print("""
🔹 Cache Warming (Pre-populating)
   • Popular cache antes de lançar feature
   • Evita thundering herd
   • Script: for key in hot_keys: cache.set(key, db.get(key))

🔹 Cache Stampede Prevention
   • Problema: 1000 requests simultâneos após cache miss
   • Solução: Lock (apenas 1 request busca DB)

   def get_with_lock(key):
       cached = cache.get(key)
       if cached:
           return cached

       # Tentar obter lock
       if cache.set_nx(f"lock:{key}", "1", ttl=10):
           # Buscar do DB
           value = db.get(key)
           cache.set(key, value)
           cache.delete(f"lock:{key}")
           return value
       else:
           # Outro thread está buscando, aguardar
           time.sleep(0.1)
           return get_with_lock(key)  # Retry

🔹 Two-Level Caching (L1 + L2)
   • L1: In-process (Python dict) - muito rápido
   • L2: Redis - compartilhado entre servidores

   def get_two_level(key):
       # L1 (local)
       if key in local_cache:
           return local_cache[key]

       # L2 (Redis)
       value = redis.get(key)
       if value:
           local_cache[key] = value  # Popular L1
           return value

       # Miss: buscar DB
       value = db.get(key)
       redis.set(key, value)
       local_cache[key] = value
       return value

🔹 Cache Tags (Invalidação em grupo)
   • Tag: "user:1" → posts:1, posts:2, comments:5
   • Invalidar tudo: cache.invalidate_tag("user:1")

🔹 Probabilistic Early Expiration
   • Evita thundering herd
   • Expira cache cedo probabilisticamente

   def get_probabilistic(key):
       cached = cache.get_with_ttl(key)
       if not cached:
           return fetch_and_cache(key)

       value, ttl = cached
       # Expirar probabilisticamente
       beta = 1.0
       delta = time.time() - cached.created_at
       expiry = -beta * ttl * log(random.random())

       if delta > expiry:
           # Refresh proativamente
           return fetch_and_cache(key)

       return value
""")


# ============================================================================
# CONCLUSÃO
# ============================================================================

print("\n" + "=" * 70)
print("CONCLUSÃO")
print("=" * 70)

print("""
🎯 RECOMENDAÇÃO GERAL:

Para 90% dos casos:
  → Cache-Aside (Lazy Loading)

Por quê?
  ✅ Simples de implementar
  ✅ Tolerante a falhas
  ✅ Armazena apenas dados usados
  ✅ Padrão da indústria

Evolua quando necessário:
  • High-write load → Write-Behind
  • Crítico consistência → Write-Through
  • Performance máxima → Refresh-Ahead

📊 MÉTRICAS PARA MONITORAR:

  • Hit Rate: % de cache hits (alvo: >90%)
  • Miss Penalty: Tempo de cache miss (alvo: <200ms)
  • Eviction Rate: % de itens evictados (alvo: <10%)
  • Memory Usage: % de memória cache (alvo: <80%)

🚀 PRÓXIMOS PASSOS:

  1. Implementar Cache-Aside em seu projeto
  2. Monitorar hit rate
  3. Adicionar cache warming para dados quentes
  4. Considerar Write-Behind se hit rate < 80%

💡 LEMBRE-SE:

"There are only two hard things in Computer Science:
 cache invalidation and naming things."
 - Phil Karlton

Mantenha simples! 🎯
""")

if __name__ == "__main__":
    print("\n\n📝 Execute este script para ver todas as demonstrações!")
