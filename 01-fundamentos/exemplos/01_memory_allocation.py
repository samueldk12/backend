"""
Exemplo 01: Demonstração de alocação de memória - Stack vs Heap

Este exemplo mostra como Python gerencia memória e como podemos
observar o comportamento de stack e heap.
"""

import sys
import tracemalloc


def exemplo_stack():
    """
    Variáveis simples (números, booleanos) e referências
    são armazenadas na stack.
    """
    print("\n=== EXEMPLO 1: Stack ===")

    # Variáveis locais na stack
    x = 10  # Inteiro pequeno (pode ser interned)
    y = 20
    z = x + y

    print(f"x = {x}, y = {y}, z = {z}")
    print(f"Tamanho de int: {sys.getsizeof(x)} bytes")

    # Quando a função termina, x, y, z são removidos da stack automaticamente


def exemplo_heap():
    """
    Objetos complexos (listas, dicts, objetos) são alocados no heap.
    """
    print("\n=== EXEMPLO 2: Heap ===")

    # Lista é criada no heap
    lista = [1, 2, 3, 4, 5]
    print(f"Lista: {lista}")
    print(f"Tamanho da lista: {sys.getsizeof(lista)} bytes")

    # Dict é criado no heap
    dados = {"nome": "João", "idade": 30}
    print(f"Dict: {dados}")
    print(f"Tamanho do dict: {sys.getsizeof(dados)} bytes")

    # Objetos grandes no heap
    lista_grande = list(range(1_000_000))
    print(f"Lista grande (1M elementos): {sys.getsizeof(lista_grande)} bytes")
    print(f"Isso é ~{sys.getsizeof(lista_grande) / 1024 / 1024:.2f} MB")


def exemplo_referencias():
    """
    Python usa referências. Variáveis na stack apontam para objetos no heap.
    """
    print("\n=== EXEMPLO 3: Referências ===")

    # Duas variáveis apontando para o mesmo objeto
    a = [1, 2, 3]
    b = a  # b aponta para o mesmo objeto que a

    print(f"a = {a}, id(a) = {id(a)}")
    print(f"b = {b}, id(b) = {id(b)}")
    print(f"a is b: {a is b}")  # True - mesmo objeto

    # Modificar através de uma variável afeta a outra
    b.append(4)
    print(f"\nDepois de b.append(4):")
    print(f"a = {a}")  # [1, 2, 3, 4] - foi modificado!
    print(f"b = {b}")  # [1, 2, 3, 4]

    # Para criar uma cópia independente
    c = a.copy()  # ou list(a) ou a[:]
    c.append(5)
    print(f"\nDepois de c = a.copy() e c.append(5):")
    print(f"a = {a}")  # [1, 2, 3, 4] - não mudou
    print(f"c = {c}")  # [1, 2, 3, 4, 5]


def exemplo_reference_counting():
    """
    Python usa reference counting para gerenciar memória.
    """
    print("\n=== EXEMPLO 4: Reference Counting ===")

    # Criar um objeto
    x = [1, 2, 3]
    print(f"x = {x}, refcount = {sys.getrefcount(x)}")  # 2 (x + getrefcount)

    # Adicionar mais referências
    y = x
    print(f"Depois de y = x, refcount = {sys.getrefcount(x)}")  # 3

    z = x
    print(f"Depois de z = x, refcount = {sys.getrefcount(x)}")  # 4

    # Remover referências
    del y
    print(f"Depois de del y, refcount = {sys.getrefcount(x)}")  # 3

    del z
    print(f"Depois de del z, refcount = {sys.getrefcount(x)}")  # 2

    # Quando refcount chega a 0, objeto é deletado imediatamente


def exemplo_memoria_profiling():
    """
    Usar tracemalloc para ver alocações de memória.
    """
    print("\n=== EXEMPLO 5: Memory Profiling ===")

    # Iniciar tracking de memória
    tracemalloc.start()

    # Snapshot inicial
    snapshot1 = tracemalloc.take_snapshot()

    # Alocar memória
    dados = []
    for i in range(100_000):
        dados.append({"id": i, "valor": f"item_{i}"})

    # Snapshot após alocação
    snapshot2 = tracemalloc.take_snapshot()

    # Comparar snapshots
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')

    print("\nTop 5 maiores alocações:")
    for stat in top_stats[:5]:
        print(f"{stat.size_diff / 1024 / 1024:.2f} MB - {stat}")

    # Memória atual
    current, peak = tracemalloc.get_traced_memory()
    print(f"\nMemória atual: {current / 1024 / 1024:.2f} MB")
    print(f"Pico de memória: {peak / 1024 / 1024:.2f} MB")

    tracemalloc.stop()


def exemplo_stack_overflow():
    """
    Demonstração de stack overflow (recursão profunda).
    """
    print("\n=== EXEMPLO 6: Stack Overflow (Recursão) ===")

    # Ver limite de recursão
    print(f"Limite de recursão atual: {sys.getrecursionlimit()}")

    def recursao(n):
        if n <= 0:
            return "Fim!"
        return recursao(n - 1)

    try:
        # Isso vai funcionar
        resultado = recursao(100)
        print(f"recursao(100): OK")

        # Isso vai falhar (limite padrão é ~1000)
        # resultado = recursao(10000)
        print(f"\nrecursao(10000) causaria RecursionError")
        print("(Descomente o código acima para ver o erro)")

    except RecursionError as e:
        print(f"ERRO: {e}")
        print("Stack overflow! Muitas chamadas de função na stack.")


def exemplo_memory_leak_prevencao():
    """
    Como evitar memory leaks em Python.
    """
    print("\n=== EXEMPLO 7: Prevenindo Memory Leaks ===")

    import weakref

    # PROBLEMA: Referência circular
    print("\n1. Referências circulares:")

    class Node:
        def __init__(self, value):
            self.value = value
            self.next = None

    a = Node(1)
    b = Node(2)
    a.next = b
    b.next = a  # Ciclo!

    print(f"Refcount de a: {sys.getrefcount(a)}")
    print(f"Refcount de b: {sys.getrefcount(b)}")
    print("Ciclo criado! Garbage collector vai limpar eventualmente.")

    # SOLUÇÃO: Weakref
    print("\n2. Usando weakref:")

    class NodeFixed:
        def __init__(self, value):
            self.value = value
            self._next = None

        @property
        def next(self):
            return self._next() if self._next else None

        @next.setter
        def next(self, node):
            self._next = weakref.ref(node) if node else None

    c = NodeFixed(1)
    d = NodeFixed(2)
    c.next = d
    d.next = c  # Não cria ciclo forte!

    print("Weakref evita ciclos fortes!")

    # PROBLEMA: Closures mantendo referências
    print("\n3. Closures:")

    def criar_funcoes():
        dados_grandes = [0] * 1_000_000  # 1M elementos

        def funcao():
            return len(dados_grandes)  # Mantém referência!

        return funcao

    f = criar_funcoes()
    print("Closure mantém referência a dados_grandes mesmo após retornar!")
    print(f"Resultado: {f()}")


def comparar_estruturas_dados():
    """
    Comparar uso de memória de diferentes estruturas.
    """
    print("\n=== EXEMPLO 8: Comparando Estruturas de Dados ===")

    n = 1000

    # List
    lista = list(range(n))
    print(f"List ({n} elementos): {sys.getsizeof(lista)} bytes")

    # Tuple (mais eficiente)
    tupla = tuple(range(n))
    print(f"Tuple ({n} elementos): {sys.getsizeof(tupla)} bytes")

    # Set
    conjunto = set(range(n))
    print(f"Set ({n} elementos): {sys.getsizeof(conjunto)} bytes")

    # Dict
    dicionario = {i: i for i in range(n)}
    print(f"Dict ({n} pares): {sys.getsizeof(dicionario)} bytes")

    # Generator (quase zero memória!)
    gerador = (i for i in range(n))
    print(f"Generator ({n} elementos): {sys.getsizeof(gerador)} bytes")
    print("  → Generator não armazena elementos, gera sob demanda!")


def main():
    """Executar todos os exemplos."""
    print("=" * 60)
    print("EXEMPLOS DE ALOCAÇÃO DE MEMÓRIA EM PYTHON")
    print("=" * 60)

    exemplo_stack()
    exemplo_heap()
    exemplo_referencias()
    exemplo_reference_counting()
    exemplo_memoria_profiling()
    exemplo_stack_overflow()
    exemplo_memory_leak_prevencao()
    comparar_estruturas_dados()

    print("\n" + "=" * 60)
    print("CONCLUSÕES:")
    print("=" * 60)
    print("""
1. Stack: rápida, limitada, automática (variáveis locais)
2. Heap: flexível, maior, gerenciada por GC (objetos)
3. Python usa reference counting + cycle detector
4. Evite referências circulares ou use weakref
5. Use generators para economizar memória
6. Profile sua aplicação com tracemalloc
    """)


if __name__ == "__main__":
    main()
