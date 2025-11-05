"""
Exemplo 2: Thread vs Process - CPU-Bound vs I/O-Bound

Execute: python 02_thread_vs_process.py
"""

import time
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import requests


# ============================================
# CPU-BOUND: Cálculos pesados
# ============================================

def calcular_fibonacci(n):
    """Operação CPU-bound: cálculo recursivo"""
    if n <= 1:
        return n
    return calcular_fibonacci(n-1) + calcular_fibonacci(n-2)


def test_cpu_bound():
    """Testa CPU-bound com Threads vs Processes"""
    print("=" * 60)
    print("🔢 TESTE CPU-BOUND: Fibonacci(35) x 4 vezes")
    print("=" * 60)
    print()

    numeros = [35, 35, 35, 35]

    # 1. Single Thread (baseline)
    print("1️⃣  SINGLE THREAD...")
    inicio = time.time()
    for n in numeros:
        calcular_fibonacci(n)
    tempo_single = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_single:.2f}s\n")

    # 2. Multi-Threading (não ajuda por causa do GIL!)
    print("2️⃣  MULTI-THREADING (4 threads)...")
    inicio = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(calcular_fibonacci, numeros))
    tempo_thread = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_thread:.2f}s")
    print(f"   📊 Speedup: {tempo_single/tempo_thread:.2f}x")
    print("   ⚠️  GIL impede paralelismo real!\n")

    # 3. Multi-Processing (ajuda muito!)
    print("3️⃣  MULTI-PROCESSING (4 processos)...")
    inicio = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        list(executor.map(calcular_fibonacci, numeros))
    tempo_process = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_process:.2f}s")
    print(f"   📊 Speedup: {tempo_single/tempo_process:.2f}x")
    print("   ✅ Cada processo tem seu GIL!\n")

    print("💡 CONCLUSÃO CPU-BOUND:")
    print("   Threading: Não ajuda (GIL)")
    print("   Multiprocessing: Speedup ≈ número de cores\n")


# ============================================
# I/O-BOUND: Network requests
# ============================================

def fetch_url(url):
    """Operação I/O-bound: requisição HTTP"""
    response = requests.get(url, timeout=5)
    return len(response.content)


def test_io_bound():
    """Testa I/O-bound com Threads vs Processes"""
    print("=" * 60)
    print("🌐 TESTE I/O-BOUND: HTTP requests x 10")
    print("=" * 60)
    print()

    urls = ['https://httpbin.org/delay/1'] * 10

    # 1. Single Thread (baseline)
    print("1️⃣  SINGLE THREAD...")
    inicio = time.time()
    for url in urls:
        try:
            fetch_url(url)
        except:
            pass
    tempo_single = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_single:.2f}s\n")

    # 2. Multi-Threading (ÓTIMO para I/O!)
    print("2️⃣  MULTI-THREADING (10 threads)...")
    inicio = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        try:
            list(executor.map(fetch_url, urls))
        except:
            pass
    tempo_thread = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_thread:.2f}s")
    print(f"   📊 Speedup: {tempo_single/tempo_thread:.2f}x")
    print("   ✅ GIL é liberado durante I/O!\n")

    # 3. Multi-Processing (overhead desnecessário)
    print("3️⃣  MULTI-PROCESSING (10 processos)...")
    inicio = time.time()
    with ProcessPoolExecutor(max_workers=10) as executor:
        try:
            list(executor.map(fetch_url, urls))
        except:
            pass
    tempo_process = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_process:.2f}s")
    print(f"   📊 Speedup: {tempo_single/tempo_process:.2f}x")
    print("   ⚠️  Overhead de criar processos!\n")

    print("💡 CONCLUSÃO I/O-BOUND:")
    print("   Threading: Excelente (leve e rápido)")
    print("   Multiprocessing: Funciona mas tem overhead\n")


# ============================================
# MEMORY SHARING
# ============================================

def test_memory_sharing():
    """Demonstra diferença de memória entre Thread e Process"""
    print("=" * 60)
    print("🧠 TESTE MEMORY SHARING")
    print("=" * 60)
    print()

    # Lista grande compartilhada
    dados_compartilhados = list(range(10_000_000))  # ~76 MB

    def processar_thread(dados):
        """Thread acessa a mesma memória"""
        return sum(dados[:1000])

    def processar_process(inicio):
        """Process precisa copiar ou usar shared memory"""
        # Cada processo recebe uma CÓPIA dos dados
        return sum(range(inicio, inicio + 1000))

    # Threads - Memória compartilhada
    print("1️⃣  THREADS (memória compartilhada)...")
    inicio = time.time()
    threads = []
    for i in range(4):
        t = threading.Thread(target=processar_thread, args=(dados_compartilhados,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    tempo_thread = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_thread:.4f}s")
    print("   ✅ Todas threads acessam a MESMA lista (76MB)\n")

    # Processes - Memória copiada
    print("2️⃣  PROCESSES (memória copiada)...")
    inicio = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        list(executor.map(processar_process, [0, 1000, 2000, 3000]))
    tempo_process = time.time() - inicio
    print(f"   ⏱️  Tempo: {tempo_process:.4f}s")
    print("   ⚠️  Cada processo cria CÓPIA (76MB x 4 = 304MB!)\n")

    print("💡 CONCLUSÃO MEMÓRIA:")
    print("   Threading: Compartilha memória (eficiente)")
    print("   Multiprocessing: Copia memória (overhead)\n")


# ============================================
# MAIN
# ============================================

def main():
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "THREAD vs PROCESS - COMPARAÇÃO" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Teste 1: CPU-Bound
    test_cpu_bound()

    print("Press ENTER para continuar para I/O-Bound...")
    input()

    # Teste 2: I/O-Bound
    test_io_bound()

    print("Press ENTER para continuar para Memory Sharing...")
    input()

    # Teste 3: Memory Sharing
    test_memory_sharing()

    print("=" * 60)
    print("📚 RESUMO GERAL")
    print("=" * 60)
    print()
    print("┌─────────────┬──────────────┬──────────────┐")
    print("│ Operação    │ Threading    │ Processing   │")
    print("├─────────────┼──────────────┼──────────────┤")
    print("│ CPU-Bound   │ ❌ GIL       │ ✅ Paralelo  │")
    print("│ I/O-Bound   │ ✅ Rápido    │ ⚠️  Overhead │")
    print("│ Memória     │ ✅ Shared    │ ❌ Copiada   │")
    print("│ Overhead    │ ✅ Leve      │ ⚠️  Pesado   │")
    print("└─────────────┴──────────────┴──────────────┘")
    print()


if __name__ == '__main__':
    main()
