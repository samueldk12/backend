"""
Exemplo 02: Threads vs Processes vs Async

Demonstra as diferenças entre threading, multiprocessing e async/await,
mostrando quando usar cada abordagem.
"""

import time
import threading
import multiprocessing
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


# ============================================================================
# TAREFAS DE TESTE
# ============================================================================

def tarefa_cpu_bound(n):
    """
    Tarefa que usa CPU intensivamente (cálculos).
    Exemplo: processamento de imagens, machine learning, criptografia.
    """
    total = 0
    for i in range(n):
        total += i ** 2
    return total


def tarefa_io_bound():
    """
    Tarefa que espera por I/O (rede, disco, banco de dados).
    Exemplo: requisições HTTP, consultas SQL, leitura de arquivos.
    """
    time.sleep(1)  # Simula chamada de API ou query de banco
    return "Dados recebidos"


async def tarefa_async_io():
    """
    Tarefa assíncrona que espera por I/O.
    """
    await asyncio.sleep(1)  # Simula I/O assíncrono
    return "Dados recebidos (async)"


# ============================================================================
# EXEMPLO 1: CPU-BOUND - THREADS vs PROCESSES
# ============================================================================

def exemplo_cpu_bound():
    """
    Threads NÃO ajudam com CPU-bound devido ao GIL.
    Processes SIM ajudam pois cada processo tem seu próprio GIL.
    """
    print("\n" + "=" * 60)
    print("EXEMPLO 1: CPU-BOUND (cálculos pesados)")
    print("=" * 60)

    n_tarefas = 4
    tamanho = 5_000_000

    # 1. SÍNCRONO (baseline)
    print("\n1. Execução SÍNCRONA:")
    start = time.time()
    for _ in range(n_tarefas):
        tarefa_cpu_bound(tamanho)
    tempo_sync = time.time() - start
    print(f"   Tempo: {tempo_sync:.2f}s")

    # 2. THREADS (não ajuda devido ao GIL!)
    print("\n2. Execução com THREADS:")
    start = time.time()
    threads = []
    for _ in range(n_tarefas):
        t = threading.Thread(target=tarefa_cpu_bound, args=(tamanho,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    tempo_threads = time.time() - start
    print(f"   Tempo: {tempo_threads:.2f}s")
    print(f"   Speedup: {tempo_sync / tempo_threads:.2f}x")
    print(f"   ❌ Threads não ajudaram! (GIL impede paralelismo real)")

    # 3. PROCESSES (funciona!)
    print("\n3. Execução com PROCESSES:")
    start = time.time()

    with ProcessPoolExecutor(max_workers=n_tarefas) as executor:
        futures = [executor.submit(tarefa_cpu_bound, tamanho) for _ in range(n_tarefas)]
        resultados = [f.result() for f in futures]

    tempo_processes = time.time() - start
    print(f"   Tempo: {tempo_processes:.2f}s")
    print(f"   Speedup: {tempo_sync / tempo_processes:.2f}x")
    print(f"   ✅ Processes funcionaram! (cada processo tem seu GIL)")

    print("\n📊 RESUMO:")
    print(f"   Síncrono:   {tempo_sync:.2f}s (baseline)")
    print(f"   Threads:    {tempo_threads:.2f}s ({tempo_sync/tempo_threads:.2f}x)")
    print(f"   Processes:  {tempo_processes:.2f}s ({tempo_sync/tempo_processes:.2f}x)")


# ============================================================================
# EXEMPLO 2: I/O-BOUND - THREADS vs ASYNC
# ============================================================================

def exemplo_io_bound():
    """
    Para I/O-bound, tanto threads quanto async funcionam bem.
    Async geralmente é mais eficiente (menos overhead).
    """
    print("\n" + "=" * 60)
    print("EXEMPLO 2: I/O-BOUND (espera por rede/disco)")
    print("=" * 60)

    n_tarefas = 10

    # 1. SÍNCRONO (baseline)
    print("\n1. Execução SÍNCRONA:")
    start = time.time()
    for _ in range(n_tarefas):
        tarefa_io_bound()
    tempo_sync = time.time() - start
    print(f"   Tempo: {tempo_sync:.2f}s")
    print(f"   (Cada tarefa demora 1s, total = {n_tarefas}s)")

    # 2. THREADS (funciona bem!)
    print("\n2. Execução com THREADS:")
    start = time.time()

    with ThreadPoolExecutor(max_workers=n_tarefas) as executor:
        futures = [executor.submit(tarefa_io_bound) for _ in range(n_tarefas)]
        resultados = [f.result() for f in futures]

    tempo_threads = time.time() - start
    print(f"   Tempo: {tempo_threads:.2f}s")
    print(f"   Speedup: {tempo_sync / tempo_threads:.2f}x")
    print(f"   ✅ Threads funcionaram! (I/O libera o GIL)")

    # 3. ASYNC (mais eficiente!)
    print("\n3. Execução com ASYNC:")
    start = time.time()

    async def executar_async():
        tasks = [tarefa_async_io() for _ in range(n_tarefas)]
        return await asyncio.gather(*tasks)

    asyncio.run(executar_async())

    tempo_async = time.time() - start
    print(f"   Tempo: {tempo_async:.2f}s")
    print(f"   Speedup: {tempo_sync / tempo_async:.2f}x")
    print(f"   ✅ Async funcionou! (menos overhead que threads)")

    print("\n📊 RESUMO:")
    print(f"   Síncrono:  {tempo_sync:.2f}s (baseline)")
    print(f"   Threads:   {tempo_threads:.2f}s ({tempo_sync/tempo_threads:.2f}x)")
    print(f"   Async:     {tempo_async:.2f}s ({tempo_sync/tempo_async:.2f}x)")


# ============================================================================
# EXEMPLO 3: OVERHEAD DE CRIAÇÃO
# ============================================================================

def tarefa_rapida():
    """Tarefa muito rápida para medir overhead."""
    return sum(range(1000))


def exemplo_overhead():
    """
    Comparar overhead de criação de threads vs processes.
    """
    print("\n" + "=" * 60)
    print("EXEMPLO 3: OVERHEAD DE CRIAÇÃO")
    print("=" * 60)

    n_tarefas = 100

    # Threads (overhead baixo)
    print("\n1. Criando 100 THREADS:")
    start = time.time()
    threads = [threading.Thread(target=tarefa_rapida) for _ in range(n_tarefas)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    tempo_threads = time.time() - start
    print(f"   Tempo: {tempo_threads:.3f}s")

    # Processes (overhead alto)
    print("\n2. Criando 100 PROCESSES:")
    start = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:  # Pool reutiliza workers
        futures = [executor.submit(tarefa_rapida) for _ in range(n_tarefas)]
        [f.result() for f in futures]
    tempo_processes = time.time() - start
    print(f"   Tempo: {tempo_processes:.3f}s")

    print("\n📊 CONCLUSÃO:")
    print(f"   Threads são {tempo_processes/tempo_threads:.1f}x mais rápidas para criar")
    print(f"   Use processes apenas quando o trabalho compensar o overhead!")


# ============================================================================
# EXEMPLO 4: COMPARTILHAMENTO DE MEMÓRIA
# ============================================================================

# Variável global
contador_global = 0
lock = threading.Lock()


def incrementar_sem_lock():
    """PROBLEMA: Race condition!"""
    global contador_global
    for _ in range(100_000):
        contador_global += 1  # Operação NÃO atômica!


def incrementar_com_lock():
    """SOLUÇÃO: Usar lock."""
    global contador_global
    for _ in range(100_000):
        with lock:
            contador_global += 1


def exemplo_compartilhamento():
    """
    Threads compartilham memória → Race conditions!
    Processes têm memória isolada → Sem race conditions, mas precisa IPC.
    """
    print("\n" + "=" * 60)
    print("EXEMPLO 4: COMPARTILHAMENTO DE MEMÓRIA")
    print("=" * 60)

    global contador_global

    # Problema: Race condition com threads
    print("\n1. THREADS SEM LOCK (race condition):")
    contador_global = 0
    threads = [threading.Thread(target=incrementar_sem_lock) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"   Esperado: 400.000")
    print(f"   Obtido:   {contador_global:,}")
    print(f"   ❌ Resultado incorreto! (race condition)")

    # Solução: Lock
    print("\n2. THREADS COM LOCK (correto mas lento):")
    contador_global = 0
    start = time.time()
    threads = [threading.Thread(target=incrementar_com_lock) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"   Esperado: 400.000")
    print(f"   Obtido:   {contador_global:,}")
    print(f"   Tempo:    {time.time() - start:.3f}s")
    print(f"   ✅ Resultado correto, mas locks têm overhead!")

    # Processes: memória isolada
    print("\n3. PROCESSES (memória isolada):")
    print("   Cada processo tem sua própria cópia das variáveis")
    print("   Não há race conditions, mas precisa usar multiprocessing.Value")
    print("   ou Queue para comunicação entre processos.")


# ============================================================================
# EXEMPLO 5: CASOS DE USO REAIS
# ============================================================================

def exemplo_casos_de_uso():
    """
    Guia de quando usar cada abordagem.
    """
    print("\n" + "=" * 60)
    print("EXEMPLO 5: QUANDO USAR CADA ABORDAGEM?")
    print("=" * 60)

    print("""
┌─────────────────┬──────────────┬─────────────┬──────────────┐
│ Cenário         │ Síncrono     │ Threads     │ Processes    │
├─────────────────┼──────────────┼─────────────┼──────────────┤
│ Web Scraping    │ ❌ Muito     │ ✅ Bom      │ ⚠️ Overkill  │
│ (muitas URLs)   │    lento     │             │              │
├─────────────────┼──────────────┼─────────────┼──────────────┤
│ API Requests    │ ❌ Muito     │ ✅ Bom      │ ⚠️ Overkill  │
│ (I/O-bound)     │    lento     │             │              │
├─────────────────┼──────────────┼─────────────┼──────────────┤
│ Async/Await     │ ❌ Lento     │ ⚠️ Misto    │ ❌ Não usa   │
│ (I/O-bound)     │              │             │              │
├─────────────────┼──────────────┼─────────────┼──────────────┤
│ Image           │ ❌ Muito     │ ❌ GIL      │ ✅ Perfeito  │
│ Processing      │    lento     │  bloqueia   │              │
├─────────────────┼──────────────┼─────────────┼──────────────┤
│ Machine         │ ❌ Muito     │ ❌ GIL      │ ✅ Perfeito  │
│ Learning        │    lento     │  bloqueia   │              │
├─────────────────┼──────────────┼─────────────┼──────────────┤
│ Video Encoding  │ ❌ Muito     │ ❌ GIL      │ ✅ Perfeito  │
│ (FFmpeg)        │    lento     │  bloqueia   │              │
├─────────────────┼──────────────┼─────────────┼──────────────┤
│ Database        │ ⚠️ OK para  │ ✅ Melhor   │ ⚠️ Overkill  │
│ Queries         │  poucos      │             │              │
└─────────────────┴──────────────┴─────────────┴──────────────┘

🎯 REGRAS DE OURO:

1. CPU-bound (cálculos pesados)
   → Use MULTIPROCESSING ou bibliotecas em C (NumPy, Pandas)

2. I/O-bound (rede, disco, DB)
   → Use ASYNC/AWAIT (melhor) ou THREADS (mais simples)

3. I/O-bound com biblioteca síncrona (requests, não aiohttp)
   → Use THREADS (não pode usar async)

4. Mix de CPU e I/O
   → Use ASYNC + ProcessPoolExecutor para CPU parts

5. Muitas tarefas pequenas
   → Use ThreadPoolExecutor ou ProcessPoolExecutor (pools reutilizam workers)

6. Real-time / Low latency
   → Use ASYNC (menos overhead de context switching)
    """)


# ============================================================================
# EXEMPLO 6: PADRÃO HÍBRIDO (ASYNC + PROCESSES)
# ============================================================================

async def exemplo_hibrido():
    """
    Combinar async para I/O com processes para CPU.
    Padrão usado em aplicações reais!
    """
    print("\n" + "=" * 60)
    print("EXEMPLO 6: PADRÃO HÍBRIDO (ASYNC + PROCESSES)")
    print("=" * 60)

    print("\nCenário: Baixar imagens (I/O) e processar (CPU)")

    async def baixar_imagem(url_id):
        """Simula download de imagem (I/O-bound)"""
        await asyncio.sleep(0.1)  # Simula latência de rede
        return f"imagem_{url_id}.jpg", [url_id] * 1000  # Dados da imagem

    def processar_imagem(dados):
        """Simula processamento de imagem (CPU-bound)"""
        nome, pixels = dados
        # Processamento pesado
        resultado = sum([p ** 2 for p in pixels])
        return f"{nome}_processada", resultado

    # Executar híbrido
    start = time.time()

    # Passo 1: Download assíncrono (I/O-bound)
    print("\n1. Baixando 10 imagens (async)...")
    imagens = await asyncio.gather(*[baixar_imagem(i) for i in range(10)])
    print(f"   Download completo: {time.time() - start:.2f}s")

    # Passo 2: Processamento paralelo (CPU-bound)
    print("\n2. Processando imagens (multiprocessing)...")
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=4) as executor:
        # Usar run_in_executor para integrar com async
        futures = [
            loop.run_in_executor(executor, processar_imagem, img)
            for img in imagens
        ]
        resultados = await asyncio.gather(*futures)

    tempo_total = time.time() - start
    print(f"   Processamento completo: {tempo_total:.2f}s")
    print(f"\n✅ Total: {tempo_total:.2f}s")
    print("   Melhor dos dois mundos: async para I/O + processes para CPU!")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("THREADS vs PROCESSES vs ASYNC")
    print("=" * 60)

    exemplo_cpu_bound()
    exemplo_io_bound()
    exemplo_overhead()
    exemplo_compartilhamento()
    exemplo_casos_de_uso()

    # Exemplo híbrido (async)
    print("\n" + "=" * 60)
    asyncio.run(exemplo_hibrido())

    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    print("""
✅ CPU-BOUND:     Use MULTIPROCESSING
✅ I/O-BOUND:     Use ASYNC/AWAIT (ou THREADS se biblioteca é síncrona)
✅ HÍBRIDO:       Combine ASYNC (I/O) + PROCESSES (CPU)
✅ SIMPLICIDADE:  Use ThreadPoolExecutor/ProcessPoolExecutor

❌ NUNCA:         Use threads para CPU-bound (GIL vai bloquear)
❌ CUIDADO:       Threads + memória compartilhada = race conditions
    """)


if __name__ == "__main__":
    # Note: Em alguns sistemas, multiprocessing precisa de if __name__ == "__main__"
    main()
