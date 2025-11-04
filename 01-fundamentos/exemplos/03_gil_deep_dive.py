"""
Exemplo 03: Deep Dive no GIL (Global Interpreter Lock)

Demonstra como o GIL funciona, suas limitações e como contorná-lo.
"""

import time
import threading
import multiprocessing
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def mostrar_info_gil():
    """Informações sobre o GIL."""
    print("=" * 60)
    print("O QUE É O GIL?")
    print("=" * 60)
    print("""
O Global Interpreter Lock (GIL) é um mutex que protege acesso aos
objetos Python, impedindo que múltiplas threads executem código
Python simultaneamente.

┌─────────────────────────────────────────────────────────┐
│              Por que o GIL existe?                      │
├─────────────────────────────────────────────────────────┤
│ 1. Simplificar gerenciamento de memória (refcount)     │
│ 2. Facilitar integração com bibliotecas C              │
│ 3. Implementação mais simples do interpretador         │
│ 4. Melhor performance single-threaded                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│            Quando o GIL é liberado?                     │
├─────────────────────────────────────────────────────────┤
│ ✅ Durante operações de I/O (read, write, network)     │
│ ✅ Durante chamadas a bibliotecas C (NumPy, PIL)       │
│ ✅ Durante time.sleep()                                 │
│ ❌ Durante execução de bytecode Python puro            │
└─────────────────────────────────────────────────────────┘
    """)
    print(f"Versão do Python: {sys.version}")
    print(f"GIL switch interval: {sys.getswitchinterval()}s")
    print("(Python troca de thread a cada 5ms por padrão)")


# ============================================================================
# DEMONSTRAÇÃO 1: GIL EM AÇÃO
# ============================================================================

def demonstrar_gil_cpu():
    """Mostrar que GIL impede paralelismo em CPU-bound."""
    print("\n" + "=" * 60)
    print("DEMO 1: GIL IMPEDINDO PARALELISMO (CPU-BOUND)")
    print("=" * 60)

    def trabalho_cpu(n, nome):
        """Tarefa CPU-bound."""
        print(f"  [{nome}] Iniciando...")
        resultado = 0
        for i in range(n):
            resultado += i ** 2
        print(f"  [{nome}] Concluído!")
        return resultado

    n = 10_000_000

    # 1 Thread (baseline)
    print("\n1. UMA THREAD:")
    start = time.time()
    trabalho_cpu(n, "T1")
    tempo_1_thread = time.time() - start
    print(f"Tempo: {tempo_1_thread:.2f}s")

    # 2 Threads (não deve ser 2x mais rápido devido ao GIL!)
    print("\n2. DUAS THREADS:")
    start = time.time()
    t1 = threading.Thread(target=trabalho_cpu, args=(n, "T1"))
    t2 = threading.Thread(target=trabalho_cpu, args=(n, "T2"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    tempo_2_threads = time.time() - start
    print(f"Tempo: {tempo_2_threads:.2f}s")
    print(f"Speedup: {tempo_1_thread / tempo_2_threads:.2f}x")
    print(f"❌ Não é 2x mais rápido! GIL força serialização.")

    # 2 Processes (deve ser ~2x mais rápido!)
    print("\n3. DOIS PROCESSOS:")
    start = time.time()
    p1 = multiprocessing.Process(target=trabalho_cpu, args=(n, "P1"))
    p2 = multiprocessing.Process(target=trabalho_cpu, args=(n, "P2"))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    tempo_2_processes = time.time() - start
    print(f"Tempo: {tempo_2_processes:.2f}s")
    print(f"Speedup: {tempo_1_thread / tempo_2_processes:.2f}x")
    print(f"✅ Quase 2x mais rápido! Cada processo tem seu GIL.")


# ============================================================================
# DEMONSTRAÇÃO 2: GIL SENDO LIBERADO (I/O)
# ============================================================================

def demonstrar_gil_io():
    """Mostrar que GIL é liberado durante I/O."""
    print("\n" + "=" * 60)
    print("DEMO 2: GIL SENDO LIBERADO (I/O-BOUND)")
    print("=" * 60)

    def trabalho_io(duracao, nome):
        """Tarefa I/O-bound."""
        print(f"  [{nome}] Iniciando sleep({duracao}s)...")
        time.sleep(duracao)  # GIL é liberado aqui!
        print(f"  [{nome}] Acordou!")
        return nome

    # Sequencial
    print("\n1. SEQUENCIAL:")
    start = time.time()
    trabalho_io(1, "T1")
    trabalho_io(1, "T2")
    trabalho_io(1, "T3")
    tempo_seq = time.time() - start
    print(f"Tempo: {tempo_seq:.2f}s")

    # Threads (deve ser ~3x mais rápido!)
    print("\n2. TRÊS THREADS:")
    start = time.time()
    threads = [
        threading.Thread(target=trabalho_io, args=(1, f"T{i}"))
        for i in range(1, 4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    tempo_threads = time.time() - start
    print(f"Tempo: {tempo_threads:.2f}s")
    print(f"Speedup: {tempo_seq / tempo_threads:.2f}x")
    print(f"✅ Threads funcionaram! GIL foi liberado durante sleep.")


# ============================================================================
# DEMONSTRAÇÃO 3: BIBLIOTECAS C LIBERAM GIL
# ============================================================================

def demonstrar_bibliotecas_c():
    """Mostrar que bibliotecas em C liberam o GIL."""
    print("\n" + "=" * 60)
    print("DEMO 3: BIBLIOTECAS C LIBERAM O GIL")
    print("=" * 60)

    try:
        import numpy as np

        def trabalho_numpy(tamanho):
            """Operação NumPy (C code)."""
            arr = np.arange(tamanho)
            return np.sum(arr ** 2)  # NumPy libera GIL!

        tamanho = 10_000_000

        # 1 Thread
        print("\n1. UMA THREAD (NumPy):")
        start = time.time()
        trabalho_numpy(tamanho)
        tempo_1 = time.time() - start
        print(f"Tempo: {tempo_1:.2f}s")

        # 4 Threads
        print("\n2. QUATRO THREADS (NumPy):")
        start = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(trabalho_numpy, tamanho) for _ in range(4)]
            [f.result() for f in futures]
        tempo_4 = time.time() - start
        print(f"Tempo: {tempo_4:.2f}s")
        print(f"Speedup: {tempo_1 * 4 / tempo_4:.2f}x")
        print(f"✅ NumPy libera GIL, threads funcionam em paralelo!")

    except ImportError:
        print("\n❌ NumPy não instalado. Execute: pip install numpy")
        print("NumPy é escrito em C e libera o GIL durante operações.")


# ============================================================================
# DEMONSTRAÇÃO 4: GIL CONTENTION (COMPETIÇÃO)
# ============================================================================

def demonstrar_gil_contention():
    """
    Mostrar que muitas threads competindo pelo GIL podem ser
    PIORES que código single-threaded devido ao overhead.
    """
    print("\n" + "=" * 60)
    print("DEMO 4: GIL CONTENTION (THRASHING)")
    print("=" * 60)

    def trabalho_leve():
        """Trabalho muito leve (mais tempo trocando GIL que trabalhando)."""
        total = 0
        for i in range(100_000):
            total += i
        return total

    # 1 Thread
    print("\n1. SEQUENCIAL (100 tarefas):")
    start = time.time()
    for _ in range(100):
        trabalho_leve()
    tempo_seq = time.time() - start
    print(f"Tempo: {tempo_seq:.3f}s")

    # Muitas threads (overhead de GIL switching!)
    print("\n2. 100 THREADS (100 tarefas):")
    start = time.time()
    threads = [threading.Thread(target=trabalho_leve) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    tempo_threads = time.time() - start
    print(f"Tempo: {tempo_threads:.3f}s")
    print(f"Speedup: {tempo_seq / tempo_threads:.2f}x")
    if tempo_threads > tempo_seq:
        print(f"❌ Threads foram MAIS LENTAS! (GIL contention)")
    else:
        print(f"⚠️ Threads não trouxeram benefício significativo.")

    # ThreadPool (reutiliza threads, menos overhead)
    print("\n3. THREADPOOL com 4 workers (100 tarefas):")
    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(trabalho_leve) for _ in range(100)]
        [f.result() for f in futures]
    tempo_pool = time.time() - start
    print(f"Tempo: {tempo_pool:.3f}s")
    print(f"Speedup: {tempo_seq / tempo_pool:.2f}x")
    print(f"✅ ThreadPool é melhor (menos overhead de criação).")


# ============================================================================
# DEMONSTRAÇÃO 5: COMO CONTORNAR O GIL
# ============================================================================

def demonstrar_solucoes():
    """Estratégias para lidar com o GIL."""
    print("\n" + "=" * 60)
    print("DEMO 5: ESTRATÉGIAS PARA LIDAR COM O GIL")
    print("=" * 60)

    print("""
┌────────────────────────────────────────────────────────────┐
│              SOLUÇÕES PARA O GIL                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ 1️⃣ MULTIPROCESSING                                        │
│    ✅ Contorna GIL (cada processo tem seu próprio)        │
│    ❌ Overhead de criação e comunicação                   │
│    📝 Use para: CPU-bound tasks                           │
│                                                            │
│ 2️⃣ ASYNC/AWAIT                                            │
│    ✅ Eficiente para I/O-bound                            │
│    ✅ Menos overhead que threads                          │
│    ❌ Não ajuda com CPU-bound                             │
│    📝 Use para: APIs, web scraping, database queries      │
│                                                            │
│ 3️⃣ BIBLIOTECAS EM C                                       │
│    ✅ NumPy, Pandas, PIL liberam GIL                      │
│    ✅ Performance próxima de C                            │
│    📝 Use para: processamento de dados, ML                │
│                                                            │
│ 4️⃣ JYTHON / IronPython                                    │
│    ✅ Não têm GIL                                         │
│    ❌ Menos bibliotecas disponíveis                       │
│    ❌ Não tão atualizados                                 │
│                                                            │
│ 5️⃣ PYPY (JIT Compiler)                                    │
│    ✅ Mais rápido que CPython                             │
│    ⚠️ Ainda tem GIL                                       │
│    📝 Use para: CPU-bound pure Python                     │
│                                                            │
│ 6️⃣ NOGIL PROJECT (Python 3.13+)                           │
│    🚧 Em desenvolvimento                                  │
│    🎯 Remover GIL do CPython                              │
│    ⏳ Futuro do Python                                    │
│                                                            │
└────────────────────────────────────────────────────────────┘

📊 ÁRVORE DE DECISÃO:

Seu código é CPU-bound ou I/O-bound?
│
├─ CPU-BOUND (cálculos, processamento)
│  │
│  ├─ Pode usar NumPy/Pandas?
│  │  └─ SIM → Use NumPy/Pandas (libera GIL) ✅
│  │
│  └─ Python puro?
│     └─ Use multiprocessing.Pool ✅
│
└─ I/O-BOUND (network, disk, database)
   │
   ├─ Bibliotecas suportam async?
   │  └─ SIM → Use async/await ✅ (melhor)
   │
   └─ Bibliotecas são síncronas?
      └─ Use ThreadPoolExecutor ✅

    """)


# ============================================================================
# DEMONSTRAÇÃO 6: EXEMPLO PRÁTICO (Web Scraping)
# ============================================================================

def demonstrar_caso_real():
    """Caso real: web scraping."""
    print("\n" + "=" * 60)
    print("DEMO 6: CASO REAL - WEB SCRAPING")
    print("=" * 60)

    def simular_download(url_id):
        """Simula download de uma página web."""
        time.sleep(0.1)  # Simula latência de rede
        return f"Conteúdo da URL {url_id}"

    n_urls = 20

    # Sequencial
    print(f"\n1. SEQUENCIAL ({n_urls} URLs):")
    start = time.time()
    for i in range(n_urls):
        simular_download(i)
    tempo_seq = time.time() - start
    print(f"Tempo: {tempo_seq:.2f}s")

    # Threads (ideal para I/O!)
    print(f"\n2. THREADS ({n_urls} URLs):")
    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(simular_download, i) for i in range(n_urls)]
        resultados = [f.result() for f in futures]
    tempo_threads = time.time() - start
    print(f"Tempo: {tempo_threads:.2f}s")
    print(f"Speedup: {tempo_seq / tempo_threads:.2f}x")
    print(f"✅ {tempo_threads:.2f}s vs {tempo_seq:.2f}s sequencial!")


# ============================================================================
# MAIN
# ============================================================================

def main():
    mostrar_info_gil()
    demonstrar_gil_cpu()
    demonstrar_gil_io()
    demonstrar_bibliotecas_c()
    demonstrar_gil_contention()
    demonstrar_solucoes()
    demonstrar_caso_real()

    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    print("""
🔒 GIL: Global Interpreter Lock
   └─ Mutex que impede execução paralela de código Python

✅ QUANDO GIL NÃO É PROBLEMA:
   • I/O-bound tasks (GIL é liberado)
   • Bibliotecas em C (NumPy, Pandas, PIL)
   • Single-threaded code

❌ QUANDO GIL É PROBLEMA:
   • CPU-bound com threads
   • Processamento paralelo em Python puro

🎯 SOLUÇÕES:
   • CPU-bound → multiprocessing
   • I/O-bound → async/await ou threads
   • Mix → async + ProcessPoolExecutor

🚀 FUTURO:
   • Python 3.13+ pode remover GIL (nogil project)
   • Enquanto isso, use as soluções acima!
    """)


if __name__ == "__main__":
    main()
