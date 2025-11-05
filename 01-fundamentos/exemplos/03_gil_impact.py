"""
Exemplo 3: Medindo o Impacto do GIL

Execute: python 03_gil_impact.py
"""

import time
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import sys


# ============================================
# DEMONSTRAÇÃO VISUAL DO GIL
# ============================================

def contador_com_gil():
    """Demonstra GIL limitando concorrência"""
    print("=" * 60)
    print("🔒 DEMONSTRAÇÃO: GIL em Ação")
    print("=" * 60)
    print()

    contador = 0
    lock = threading.Lock()

    def incrementar_sem_lock():
        """RACE CONDITION - threads competem pelo mesmo recurso"""
        nonlocal contador
        for _ in range(1_000_000):
            contador += 1

    def incrementar_com_lock():
        """PROTEGIDO - mas serializa a execução"""
        nonlocal contador
        for _ in range(1_000_000):
            with lock:
                contador += 1

    # Teste 1: SEM lock (race condition)
    print("1️⃣  SEM Lock (Race Condition)...")
    contador = 0
    threads = []
    inicio = time.time()

    for _ in range(2):
        t = threading.Thread(target=incrementar_sem_lock)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    tempo = time.time() - inicio
    print(f"   Esperado: 2,000,000")
    print(f"   Obtido:   {contador:,}")
    print(f"   ❌ Perdeu {2_000_000 - contador:,} incrementos!")
    print(f"   ⏱️  Tempo: {tempo:.2f}s\n")

    # Teste 2: COM lock (seguro mas lento)
    print("2️⃣  COM Lock (Thread-Safe)...")
    contador = 0
    threads = []
    inicio = time.time()

    for _ in range(2):
        t = threading.Thread(target=incrementar_com_lock)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    tempo = time.time() - inicio
    print(f"   Esperado: 2,000,000")
    print(f"   Obtido:   {contador:,}")
    print(f"   ✅ Correto!")
    print(f"   ⏱️  Tempo: {tempo:.2f}s")
    print("   ⚠️  Mas lock serializa = sem paralelismo!\n")


# ============================================
# GIL: CPU vs I/O
# ============================================

def gil_cpu_vs_io():
    """Compara impacto do GIL em CPU vs I/O"""
    print("=" * 60)
    print("⚡ GIL: CPU-Bound vs I/O-Bound")
    print("=" * 60)
    print()

    # CPU-Bound
    def cpu_trabalho():
        """Operação CPU intensiva"""
        total = 0
        for i in range(5_000_000):
            total += i ** 2
        return total

    # I/O-Bound
    def io_trabalho():
        """Simula operação I/O"""
        time.sleep(1)  # Simula I/O
        return "done"

    # Teste CPU-Bound
    print("1️⃣  CPU-BOUND com Threading...")
    inicio = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(cpu_trabalho) for _ in range(4)]
        [f.result() for f in futures]
    tempo_cpu_thread = time.time() - inicio
    print(f"   ⏱️  4 threads: {tempo_cpu_thread:.2f}s")

    print("   CPU-BOUND com Processing...")
    inicio = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(cpu_trabalho) for _ in range(4)]
        [f.result() for f in futures]
    tempo_cpu_process = time.time() - inicio
    print(f"   ⏱️  4 processes: {tempo_cpu_process:.2f}s")
    print(f"   📊 Process é {tempo_cpu_thread/tempo_cpu_process:.1f}x mais rápido!\n")

    # Teste I/O-Bound
    print("2️⃣  I/O-BOUND com Threading...")
    inicio = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(io_trabalho) for _ in range(4)]
        [f.result() for f in futures]
    tempo_io_thread = time.time() - inicio
    print(f"   ⏱️  4 threads: {tempo_io_thread:.2f}s")

    print("   I/O-BOUND com Processing...")
    inicio = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(io_trabalho) for _ in range(4)]
        [f.result() for f in futures]
    tempo_io_process = time.time() - inicio
    print(f"   ⏱️  4 processes: {tempo_io_process:.2f}s")
    print(f"   📊 Ambos ~{max(tempo_io_thread, tempo_io_process):.1f}s (I/O libera GIL)\n")

    print("💡 CONCLUSÃO:")
    print("   CPU-Bound: GIL LIMITA threads (use processes)")
    print("   I/O-Bound: GIL é LIBERADO (threads funcionam bem)\n")


# ============================================
# VISUALIZANDO GIL
# ============================================

def visualizar_gil():
    """Visualiza comportamento do GIL"""
    print("=" * 60)
    print("👁️  VISUALIZANDO O GIL")
    print("=" * 60)
    print()

    import threading
    import time

    resultados = []
    lock = threading.Lock()

    def worker(id, tipo):
        """Worker que registra quando executa"""
        inicio = time.time()

        if tipo == "cpu":
            # CPU-Bound: GIL limita
            total = 0
            for i in range(10_000_000):
                total += i
        else:
            # I/O-Bound: GIL liberado
            time.sleep(0.5)

        fim = time.time()

        with lock:
            resultados.append({
                'id': id,
                'tipo': tipo,
                'inicio': inicio,
                'fim': fim,
                'duracao': fim - inicio
            })

    print("1️⃣  CPU-Bound (GIL limitando)...")
    resultados = []
    threads = []
    inicio_teste = time.time()

    for i in range(4):
        t = threading.Thread(target=worker, args=(i, "cpu"))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("   Thread | Início | Fim    | Duração")
    print("   -------|--------|--------|--------")
    for r in sorted(resultados, key=lambda x: x['inicio']):
        print(f"   T{r['id']}     | {r['inicio']-inicio_teste:.2f}s  | {r['fim']-inicio_teste:.2f}s | {r['duracao']:.2f}s")

    print(f"   \n   ⏱️  Tempo total: {time.time()-inicio_teste:.2f}s")
    print("   ⚠️  Threads executam SERIALMENTE (GIL)\n")

    print("2️⃣  I/O-Bound (GIL liberado)...")
    resultados = []
    threads = []
    inicio_teste = time.time()

    for i in range(4):
        t = threading.Thread(target=worker, args=(i, "io"))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("   Thread | Início | Fim    | Duração")
    print("   -------|--------|--------|--------")
    for r in sorted(resultados, key=lambda x: x['inicio']):
        print(f"   T{r['id']}     | {r['inicio']-inicio_teste:.2f}s  | {r['fim']-inicio_teste:.2f}s | {r['duracao']:.2f}s")

    print(f"   \n   ⏱️  Tempo total: {time.time()-inicio_teste:.2f}s")
    print("   ✅ Threads executam EM PARALELO!\n")


# ============================================
# BYTE CODE EXECUTION
# ============================================

def gil_e_bytecode():
    """Mostra como GIL funciona no nível de bytecode"""
    print("=" * 60)
    print("🔬 GIL e Python Bytecode")
    print("=" * 60)
    print()

    print("Python executa bytecode linha por linha.")
    print("GIL garante que apenas 1 thread execute bytecode por vez.\n")

    codigo = """
x = 0
x += 1
    """

    import dis
    print("Bytecode de 'x += 1':")
    print("-" * 40)
    dis.dis(compile("x += 1", "", "exec"))
    print()

    print("💡 O que acontece:")
    print("   1. LOAD_NAME      (carrega x)")
    print("   2. LOAD_CONST     (carrega 1)")
    print("   3. INPLACE_ADD    (soma)")
    print("   4. STORE_NAME     (salva x)")
    print()
    print("   ⚠️  Entre essas operações, outra thread pode")
    print("       executar e mudar x = RACE CONDITION!")
    print()
    print("   🔒 GIL impede múltiplas threads executarem")
    print("       bytecode simultaneamente, MAS:")
    print("       - Thread switch pode ocorrer entre operações")
    print("       - Por isso precisa de Lock!\n")


# ============================================
# MAIN
# ============================================

def main():
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "MEDINDO IMPACTO DO GIL" + " " * 20 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Teste 1: Race Condition
    contador_com_gil()
    input("Press ENTER para continuar...")
    print("\n")

    # Teste 2: CPU vs I/O
    gil_cpu_vs_io()
    input("Press ENTER para continuar...")
    print("\n")

    # Teste 3: Visualizar
    visualizar_gil()
    input("Press ENTER para continuar...")
    print("\n")

    # Teste 4: Bytecode
    gil_e_bytecode()

    print("=" * 60)
    print("📚 RESUMO FINAL")
    print("=" * 60)
    print()
    print("🔒 GIL (Global Interpreter Lock):")
    print("   • Permite apenas 1 thread executar Python bytecode")
    print("   • Protege estruturas internas do CPython")
    print("   • É LIBERADO durante operações I/O")
    print("   • NÃO é liberado durante operações CPU")
    print()
    print("✅ Quando GIL NÃO importa:")
    print("   • I/O-Bound operations (network, disk)")
    print("   • Usando C extensions que liberam GIL")
    print("   • Multiprocessing (cada processo = seu GIL)")
    print()
    print("❌ Quando GIL importa:")
    print("   • CPU-Bound operations (cálculos pesados)")
    print("   • Processamento paralelo em threads")
    print("   • Machine Learning em CPU (use GPU ou multiprocessing)")
    print()


if __name__ == '__main__':
    main()
