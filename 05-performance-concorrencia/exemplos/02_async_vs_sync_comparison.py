"""
Módulo 05 - Performance: Async/Await vs Sync

Este exemplo demonstra:
1. Sync vs Async vs Threading vs Multiprocessing
2. Quando usar cada abordagem
3. I/O-bound vs CPU-bound tasks
4. Async database queries
5. Connection pooling
6. Pitfalls comuns (blocking the event loop)

Execute:
    python 02_async_vs_sync_comparison.py
"""

import time
import asyncio
import requests
import aiohttp
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# EXEMPLO 1: I/O-BOUND TASKS (Network requests)
# ============================================================================

def exemplo_io_bound():
    """
    I/O-bound: maior parte do tempo esperando I/O (rede, disco, DB)

    Exemplos:
    - HTTP requests
    - Database queries
    - Leitura/escrita de arquivos
    - Chamadas a APIs externas

    Melhor abordagem: ASYNC ou THREADS
    """
    print("\n" + "="*70)
    print("EXEMPLO 1: I/O-BOUND TASKS (HTTP Requests)")
    print("="*70)

    urls = [
        "https://httpbin.org/delay/1",  # Delay de 1 segundo
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
    ]

    # -------------------------------------------------------------------------
    # Abordagem 1: SYNC (Sequential)
    # -------------------------------------------------------------------------
    print("\n🐌 Abordagem 1: SYNC (Sequential)")

    def fetch_sync(url: str) -> dict:
        """Fetch síncrono (bloqueante)"""
        response = requests.get(url, timeout=10)
        return response.json()

    start = time.time()
    results = []
    for url in urls:
        result = fetch_sync(url)
        results.append(result)

    sync_time = time.time() - start
    print(f"✅ 5 requests em {sync_time:.2f}s")
    print(f"   Throughput: {len(urls) / sync_time:.2f} req/s")

    # -------------------------------------------------------------------------
    # Abordagem 2: ASYNC (Event Loop)
    # -------------------------------------------------------------------------
    print("\n⚡ Abordagem 2: ASYNC (Event Loop)")

    async def fetch_async(session: aiohttp.ClientSession, url: str) -> dict:
        """Fetch assíncrono (não-bloqueante)"""
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            return await response.json()

    async def fetch_all_async(urls: List[str]):
        """Fetch múltiplas URLs em paralelo"""
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_async(session, url) for url in urls]
            return await asyncio.gather(*tasks)

    start = time.time()
    results = asyncio.run(fetch_all_async(urls))
    async_time = time.time() - start

    print(f"✅ 5 requests em {async_time:.2f}s")
    print(f"   Throughput: {len(urls) / async_time:.2f} req/s")
    print(f"   Speedup: {sync_time / async_time:.1f}x mais rápido")

    # -------------------------------------------------------------------------
    # Abordagem 3: THREADS (ThreadPoolExecutor)
    # -------------------------------------------------------------------------
    print("\n🧵 Abordagem 3: THREADS (ThreadPoolExecutor)")

    def fetch_threaded(url: str) -> dict:
        """Fetch com threads"""
        return requests.get(url, timeout=10).json()

    start = time.time()
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_threaded, urls))
    thread_time = time.time() - start

    print(f"✅ 5 requests em {thread_time:.2f}s")
    print(f"   Throughput: {len(urls) / thread_time:.2f} req/s")
    print(f"   Speedup: {sync_time / thread_time:.1f}x mais rápido")

    # -------------------------------------------------------------------------
    # Comparação
    # -------------------------------------------------------------------------
    print("\n📊 COMPARAÇÃO:")
    print(f"   Sync:   {sync_time:.2f}s  (baseline)")
    print(f"   Async:  {async_time:.2f}s  ({sync_time / async_time:.1f}x)")
    print(f"   Thread: {thread_time:.2f}s  ({sync_time / thread_time:.1f}x)")
    print("\n   ✅ Async é a melhor para I/O-bound!")


# ============================================================================
# EXEMPLO 2: CPU-BOUND TASKS (Computação pesada)
# ============================================================================

def exemplo_cpu_bound():
    """
    CPU-bound: maior parte do tempo fazendo computação

    Exemplos:
    - Processamento de imagem/vídeo
    - Criptografia
    - Compressão
    - Machine learning inference

    Melhor abordagem: MULTIPROCESSING (não async!)
    """
    print("\n" + "="*70)
    print("EXEMPLO 2: CPU-BOUND TASKS (Computação Pesada)")
    print("="*70)

    def cpu_intensive_task(n: int) -> int:
        """Tarefa CPU-bound: calcular números primos"""
        def is_prime(num):
            if num < 2:
                return False
            for i in range(2, int(num ** 0.5) + 1):
                if num % i == 0:
                    return False
            return True

        count = 0
        for num in range(2, n):
            if is_prime(num):
                count += 1
        return count

    numbers = [100000, 100000, 100000, 100000]

    # -------------------------------------------------------------------------
    # Abordagem 1: SYNC
    # -------------------------------------------------------------------------
    print("\n🐌 Abordagem 1: SYNC (Sequential)")

    start = time.time()
    results = []
    for n in numbers:
        result = cpu_intensive_task(n)
        results.append(result)
    sync_time = time.time() - start

    print(f"✅ 4 tasks em {sync_time:.2f}s")

    # -------------------------------------------------------------------------
    # Abordagem 2: ASYNC (NÃO AJUDA!)
    # -------------------------------------------------------------------------
    print("\n⚠️  Abordagem 2: ASYNC (Não funciona para CPU-bound!)")

    async def cpu_task_async(n: int) -> int:
        """Async não ajuda em CPU-bound!"""
        return cpu_intensive_task(n)  # Bloqueante!

    async def run_all_async():
        tasks = [cpu_task_async(n) for n in numbers]
        return await asyncio.gather(*tasks)

    start = time.time()
    results = asyncio.run(run_all_async())
    async_time = time.time() - start

    print(f"❌ 4 tasks em {async_time:.2f}s (mesmo tempo que sync!)")
    print("   Async NÃO funciona para CPU-bound porque bloqueia event loop")

    # -------------------------------------------------------------------------
    # Abordagem 3: THREADS (NÃO AJUDA - GIL!)
    # -------------------------------------------------------------------------
    print("\n⚠️  Abordagem 3: THREADS (GIL impede paralelismo)")

    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(cpu_intensive_task, numbers))
    thread_time = time.time() - start

    print(f"❌ 4 tasks em {thread_time:.2f}s (GIL impede paralelismo)")
    print("   Python GIL permite apenas 1 thread executar Python bytecode por vez")

    # -------------------------------------------------------------------------
    # Abordagem 4: MULTIPROCESSING (FUNCIONA!)
    # -------------------------------------------------------------------------
    print("\n⚡ Abordagem 4: MULTIPROCESSING (Múltiplos processos)")

    start = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(cpu_intensive_task, numbers))
    process_time = time.time() - start

    print(f"✅ 4 tasks em {process_time:.2f}s")
    print(f"   Speedup: {sync_time / process_time:.1f}x mais rápido")

    # -------------------------------------------------------------------------
    # Comparação
    # -------------------------------------------------------------------------
    print("\n📊 COMPARAÇÃO:")
    print(f"   Sync:           {sync_time:.2f}s  (baseline)")
    print(f"   Async:          {async_time:.2f}s  (não ajuda)")
    print(f"   Thread:         {thread_time:.2f}s  (GIL impede)")
    print(f"   Multiprocess:   {process_time:.2f}s  ({sync_time / process_time:.1f}x)")
    print("\n   ✅ Multiprocessing é a única que funciona para CPU-bound!")


# ============================================================================
# EXEMPLO 3: Async Database Queries
# ============================================================================

async def exemplo_async_database():
    """
    Database queries são I/O-bound

    Usar async permite múltiplas queries simultâneas
    """
    print("\n" + "="*70)
    print("EXEMPLO 3: Async Database Queries")
    print("="*70)

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import declarative_base
    from sqlalchemy import Column, Integer, String, select

    # Criar engine assíncrono
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",  # SQLite em memória
        echo=False
    )

    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        name = Column(String(50))

    # Criar tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Criar sessão
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # -------------------------------------------------------------------------
    # Popular banco
    # -------------------------------------------------------------------------
    async with AsyncSessionLocal() as session:
        for i in range(100):
            session.add(User(name=f"User {i}"))
        await session.commit()

    # -------------------------------------------------------------------------
    # Sync approach
    # -------------------------------------------------------------------------
    print("\n🐌 Sync: Queries sequenciais")

    async def get_user_sync(session, user_id: int):
        """Query síncrona (uma por vez)"""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    start = time.time()
    async with AsyncSessionLocal() as session:
        users = []
        for user_id in range(1, 11):  # Buscar 10 usuários
            user = await get_user_sync(session, user_id)
            users.append(user)

    sync_db_time = time.time() - start
    print(f"✅ 10 queries em {sync_db_time:.4f}s")

    # -------------------------------------------------------------------------
    # Async approach
    # -------------------------------------------------------------------------
    print("\n⚡ Async: Queries em paralelo")

    async def get_users_async(session, user_ids: List[int]):
        """Queries em paralelo"""
        tasks = []
        for user_id in user_ids:
            task = session.execute(select(User).where(User.id == user_id))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return [result.scalar_one() for result in results]

    start = time.time()
    async with AsyncSessionLocal() as session:
        users = await get_users_async(session, list(range(1, 11)))

    async_db_time = time.time() - start
    print(f"✅ 10 queries em {async_db_time:.4f}s")
    print(f"   Speedup: {sync_db_time / async_db_time:.1f}x mais rápido")

    await engine.dispose()


# ============================================================================
# EXEMPLO 4: PITFALLS (Erros Comuns)
# ============================================================================

async def exemplo_pitfalls():
    """
    Erros comuns ao usar async/await
    """
    print("\n" + "="*70)
    print("EXEMPLO 4: PITFALLS (Erros Comuns)")
    print("="*70)

    # -------------------------------------------------------------------------
    # Pitfall 1: Bloquear event loop
    # -------------------------------------------------------------------------
    print("\n❌ Pitfall 1: Bloquear o Event Loop")

    async def bad_sleep():
        """ERRADO: time.sleep bloqueia event loop!"""
        print("   Iniciando bad_sleep (vai bloquear tudo)")
        time.sleep(2)  # ❌ Bloqueante!
        print("   Fim bad_sleep")

    async def good_sleep():
        """CORRETO: asyncio.sleep não bloqueia"""
        print("   Iniciando good_sleep (não bloqueia)")
        await asyncio.sleep(2)  # ✅ Não-bloqueante
        print("   Fim good_sleep")

    print("\n   Exemplo ERRADO:")
    start = time.time()
    await asyncio.gather(bad_sleep(), bad_sleep())  # Sequential!
    print(f"   Tempo: {time.time() - start:.2f}s (deveria ser 2s, mas é 4s!)")

    print("\n   Exemplo CORRETO:")
    start = time.time()
    await asyncio.gather(good_sleep(), good_sleep())  # Paralelo!
    print(f"   Tempo: {time.time() - start:.2f}s (2s, paralelo!)")

    # -------------------------------------------------------------------------
    # Pitfall 2: Não usar await
    # -------------------------------------------------------------------------
    print("\n❌ Pitfall 2: Esquecer `await`")

    async def fetch_data():
        await asyncio.sleep(0.1)
        return {"data": "importante"}

    # Errado: sem await
    result = fetch_data()  # ❌ Retorna coroutine, não executa!
    print(f"   Sem await: {result}")  # <coroutine object>

    # Correto: com await
    result = await fetch_data()  # ✅ Executa e retorna resultado
    print(f"   Com await: {result}")  # {'data': 'importante'}

    # -------------------------------------------------------------------------
    # Pitfall 3: Usar biblioteca síncrona em código async
    # -------------------------------------------------------------------------
    print("\n❌ Pitfall 3: Usar biblioteca síncrona em código async")

    async def bad_http_request():
        """ERRADO: requests é bloqueante"""
        # requests.get() bloqueia event loop!
        # Use aiohttp ao invés
        print("   ❌ Nunca use requests em código async")

    async def good_http_request():
        """CORRETO: aiohttp é não-bloqueante"""
        print("   ✅ Use aiohttp ou httpx em código async")

    await bad_http_request()
    await good_http_request()

    # -------------------------------------------------------------------------
    # Pitfall 4: CPU-bound em async
    # -------------------------------------------------------------------------
    print("\n❌ Pitfall 4: CPU-bound task em async")

    def cpu_intensive():
        """Tarefa CPU-bound"""
        total = 0
        for i in range(10_000_000):
            total += i
        return total

    async def bad_cpu_task():
        """ERRADO: bloqueia event loop"""
        result = cpu_intensive()  # ❌ Bloqueante!
        return result

    async def good_cpu_task():
        """CORRETO: rodar em thread ou process"""
        loop = asyncio.get_event_loop()
        # Rodar em thread pool
        result = await loop.run_in_executor(None, cpu_intensive)
        return result

    print("\n   Exemplo ERRADO:")
    start = time.time()
    await bad_cpu_task()
    print(f"   Bloqueou por {time.time() - start:.2f}s")

    print("\n   Exemplo CORRETO:")
    start = time.time()
    await good_cpu_task()
    print(f"   Não bloqueou: {time.time() - start:.2f}s")


# ============================================================================
# GUIA DE DECISÃO
# ============================================================================

def print_decision_guide():
    """Guia visual para escolher abordagem"""
    guide = """
═══════════════════════════════════════════════════════════════════════════
                        GUIA DE DECISÃO
═══════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────┐
│                          É I/O-bound?                                   │
│          (rede, DB, arquivos, APIs externas)                            │
└───────────────────────┬─────────────────────────────────────────────────┘
                        │
           ┌────────────┴────────────┐
           │                         │
          SIM                       NÃO (CPU-bound)
           │                         │
           v                         v
    ┌──────────────┐          ┌──────────────┐
    │ Use ASYNC    │          │ Use          │
    │ ou           │          │ MULTIPROC    │
    │ THREADS      │          │              │
    └──────┬───────┘          └──────┬───────┘
           │                         │
           v                         v
    Qual escolher?            Quando usar cada?

    ASYNC quando:                MULTIPROCESS:
    - ✅ Muito I/O               - ✅ Processamento pesado
    - ✅ Alta concorrência       - ✅ Múltiplos cores
    - ✅ Python 3.7+             - ✅ Independência entre tasks
    - ✅ Bibliotecas async       - ❌ Overhead de criar processos
      disponíveis
                                 THREADS:
    THREADS quando:              - ⚠️  Não funciona para CPU-bound
    - ✅ Bibliotecas síncronas     em Python (GIL)
      apenas                     - ✅ Use apenas para I/O-bound
    - ✅ Código legado             quando async não disponível
    - ❌ Menos eficiente que
      async para I/O

═══════════════════════════════════════════════════════════════════════════
                          TABELA COMPARATIVA
═══════════════════════════════════════════════════════════════════════════

┌──────────────┬──────────┬────────────┬─────────┬──────────────┬─────────┐
│ Abordagem    │ I/O-bound│ CPU-bound  │ Overhead│ Concorrência │ Memória │
├──────────────┼──────────┼────────────┼─────────┼──────────────┼─────────┤
│ Sync         │ ⭐       │ ⭐         │ Baixo   │ 1            │ Baixa   │
│ (Sequential) │          │            │         │              │         │
├──────────────┼──────────┼────────────┼─────────┼──────────────┼─────────┤
│ Async        │ ⭐⭐⭐⭐⭐│ ⭐         │ Baixo   │ Milhares     │ Baixa   │
│ (Event Loop) │          │            │         │              │         │
├──────────────┼──────────┼────────────┼─────────┼──────────────┼─────────┤
│ Threads      │ ⭐⭐⭐   │ ⭐         │ Médio   │ Centenas     │ Média   │
│ (Thread Pool)│          │ (GIL)      │         │              │         │
├──────────────┼──────────┼────────────┼─────────┼──────────────┼─────────┤
│ Multiprocess │ ⭐⭐     │ ⭐⭐⭐⭐⭐  │ Alto    │ # CPUs       │ Alta    │
│ (Processes)  │          │            │         │              │         │
└──────────────┴──────────┴────────────┴─────────┴──────────────┴─────────┘

═══════════════════════════════════════════════════════════════════════════
                      CASOS DE USO REAIS
═══════════════════════════════════════════════════════════════════════════

🌐 WEB API (FastAPI):
   └─> Use ASYNC
       - Múltiplas requests simultâneas
       - Database queries com asyncpg/sqlalchemy async
       - HTTP calls com aiohttp
       - Redis com aioredis

🎬 VIDEO ENCODING:
   └─> Use MULTIPROCESSING
       - FFmpeg em processos separados
       - Cada vídeo em um processo
       - Utiliza todos os cores da CPU

📊 DATA PROCESSING:
   └─> Use MULTIPROCESSING
       - Pandas, NumPy (liberam GIL)
       - Machine Learning inference
       - Image/video processing

🤖 WEB SCRAPING:
   └─> Use ASYNC
       - Centenas de requests simultâneas
       - aiohttp + asyncio
       - Muito mais rápido que threads

📧 EMAIL SENDING:
   └─> Use CELERY (async task queue)
       - Background jobs
       - Retry automático
       - Não bloqueia API

═══════════════════════════════════════════════════════════════════════════
                      BIBLIOTECAS IMPORTANTES
═══════════════════════════════════════════════════════════════════════════

SYNC:
  - requests       → HTTP
  - psycopg2       → PostgreSQL
  - pymongo        → MongoDB
  - redis          → Redis

ASYNC:
  - aiohttp        → HTTP client/server
  - httpx          → HTTP (suporta sync e async)
  - asyncpg        → PostgreSQL (mais rápido)
  - motor          → MongoDB
  - aioredis       → Redis
  - aiomysql       → MySQL
  - sqlalchemy     → ORM (suporta async desde 1.4)

═══════════════════════════════════════════════════════════════════════════
"""
    print(guide)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║          MÓDULO 05: ASYNC/AWAIT VS SYNC VS THREADS VS MULTIPROC         ║
║         Entenda quando usar cada abordagem e otimize performance         ║
╚══════════════════════════════════════════════════════════════════════════╝

Escolha um exemplo:
1. I/O-bound tasks (HTTP requests)
2. CPU-bound tasks (Computação pesada)
3. Async database queries
4. Pitfalls (erros comuns)
5. Ver guia de decisão

Digite o número (ou 0 para todos): """)

    choice = input().strip()

    if choice == "1":
        exemplo_io_bound()
    elif choice == "2":
        exemplo_cpu_bound()
    elif choice == "3":
        asyncio.run(exemplo_async_database())
    elif choice == "4":
        asyncio.run(exemplo_pitfalls())
    elif choice == "5":
        print_decision_guide()
    elif choice == "0":
        exemplo_io_bound()
        exemplo_cpu_bound()
        asyncio.run(exemplo_async_database())
        asyncio.run(exemplo_pitfalls())
        print_decision_guide()
    else:
        print("❌ Opção inválida")

    print("\n" + "="*70)
    print("💡 CONCEITOS APRENDIDOS:")
    print("="*70)
    print("""
1. ✅ I/O-bound: Use ASYNC ou THREADS (async é melhor)
2. ✅ CPU-bound: Use MULTIPROCESSING (único que funciona)
3. ✅ GIL: Python Global Interpreter Lock impede CPU parallelism em threads
4. ✅ Event Loop: Async executa múltiplas tasks sem threads
5. ✅ await: Libera event loop para outras tasks
6. ✅ Pitfall: Não bloquear event loop com código síncrono
7. ✅ Async libraries: aiohttp, asyncpg, aioredis
8. ✅ run_in_executor: Rodar código bloqueante em thread pool

⚠️  REGRAS DE OURO:

✅ I/O-bound → ASYNC
✅ CPU-bound → MULTIPROCESSING
✅ Sempre use bibliotecas async em código async (aiohttp, não requests)
✅ Nunca bloqueie event loop (time.sleep → asyncio.sleep)
✅ Use asyncio.gather() para executar múltiplas coroutines em paralelo
✅ FastAPI suporta async nativo (async def routes)

❌ NUNCA:
❌ Use requests em código async (use aiohttp)
❌ Use time.sleep em código async (use asyncio.sleep)
❌ Use threads para CPU-bound (GIL impede, use multiprocessing)
❌ Esqueça `await` em coroutines
""")
