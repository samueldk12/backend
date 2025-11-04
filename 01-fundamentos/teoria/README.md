# Módulo 01 - Fundamentos e Low-Level Architecture

## 🎯 Objetivo

Entender como o código que escrevemos é executado pelo computador, desde o hardware até o runtime do Python. Este conhecimento é fundamental para:
- Debugar problemas de performance
- Entender limitações de linguagens e frameworks
- Tomar decisões arquiteturais informadas
- Otimizar código de forma inteligente

---

## 📚 Conteúdo

1. [Arquitetura de Computadores](#1-arquitetura-de-computadores)
2. [CPU e Execução de Código](#2-cpu-e-execução-de-código)
3. [Memória: Stack vs Heap](#3-memória-stack-vs-heap)
4. [Processos e Threads](#4-processos-e-threads)
5. [System Calls e Kernel](#5-system-calls-e-kernel)
6. [Como Python Executa Código](#6-como-python-executa-código)

---

## 1. Arquitetura de Computadores

### 1.1 Componentes Básicos

```
┌─────────────────────────────────────────────────────┐
│                       CPU                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Core 1  │  │  Core 2  │  │  Core N  │          │
│  │          │  │          │  │          │          │
│  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │          │
│  │ │L1 Cac││  │ │L1 Cac││  │ │L1 Cac││          │
│  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│         │              │              │             │
│         └──────────────┴──────────────┘             │
│                        │                            │
│                 ┌──────────────┐                    │
│                 │  L2/L3 Cache │                    │
│                 └──────────────┘                    │
└─────────────────────┬───────────────────────────────┘
                      │
              ┌───────┴────────┐
              │   RAM Memory   │
              │  (Main Memory) │
              └───────┬────────┘
                      │
              ┌───────┴────────┐
              │  Storage (SSD) │
              └────────────────┘
```

### 1.2 Hierarquia de Memória

| Tipo | Velocidade | Tamanho | Latência |
|------|-----------|---------|----------|
| **CPU Registers** | Mais rápido | ~1KB | 0.5ns |
| **L1 Cache** | Muito rápido | 32-64KB por core | 1-2ns |
| **L2 Cache** | Rápido | 256KB-1MB por core | 4-10ns |
| **L3 Cache** | Médio | 8-32MB compartilhado | 10-20ns |
| **RAM** | Lento | 8-128GB | 50-100ns |
| **SSD** | Muito lento | 256GB-4TB | 50-150μs |
| **HDD** | Extremamente lento | 1-10TB | 1-10ms |

### 💡 Por que isso importa?

```python
# Exemplo: Acesso sequencial vs aleatório
import time
import random

# Dados de teste
data = list(range(10_000_000))

# ACESSO SEQUENCIAL - Cache-friendly
start = time.time()
sum_sequential = 0
for i in range(len(data)):
    sum_sequential += data[i]
print(f"Sequencial: {time.time() - start:.4f}s")

# ACESSO ALEATÓRIO - Cache-unfriendly
random_indices = random.sample(range(len(data)), len(data))
start = time.time()
sum_random = 0
for i in random_indices:
    sum_random += data[i]
print(f"Aleatório: {time.time() - start:.4f}s")

# Resultado: Sequencial é 2-3x mais rápido devido a cache hits!
```

**Resultado esperado:**
- Sequencial: ~0.3s
- Aleatório: ~0.8s

**Por quê?** CPU cache prefetching funciona bem com acesso sequencial.

---

## 2. CPU e Execução de Código

### 2.1 O que a CPU faz?

A CPU executa **instruções** em ciclos:

```
┌─────────────────────────────────────────┐
│  Ciclo de Instrução (Fetch-Decode-      │
│         Execute-Store)                   │
└─────────────────────────────────────────┘
    │
    ├─> 1. FETCH: Busca instrução da memória
    │
    ├─> 2. DECODE: Decodifica o que fazer
    │
    ├─> 3. EXECUTE: Executa a operação
    │
    └─> 4. STORE: Salva resultado
```

### 2.2 Do Python ao Assembly

```python
# Python de alto nível
def add(a, b):
    return a + b

result = add(5, 3)
```

```python
# Bytecode Python (intermediário)
import dis
dis.dis(add)

# Output:
#   2           0 LOAD_FAST                0 (a)
#               2 LOAD_FAST                1 (b)
#               4 BINARY_ADD
#               6 RETURN_VALUE
```

```assembly
; Assembly x86-64 (aproximado do que CPU executa)
mov eax, [rbp-4]    ; Carrega 'a' em registrador
add eax, [rbp-8]    ; Soma com 'b'
ret                  ; Retorna resultado
```

### 💡 Implicações

1. **Interpretado vs Compilado**:
   - Python: código → bytecode → interpretado pela VM
   - C/Rust: código → assembly → executado direto pela CPU
   - **Resultado**: Python é 10-100x mais lento, mas mais produtivo

2. **JIT Compilation** (PyPy, Numba):
   - Compila bytecode para assembly em runtime
   - Aproxima performance de linguagens compiladas

---

## 3. Memória: Stack vs Heap

### 3.1 Stack (Pilha)

**Características:**
- Memória automática e rápida (LIFO - Last In First Out)
- Tamanho fixo e limitado (~1-8MB)
- Gerenciada automaticamente
- Usada para: variáveis locais, chamadas de função

```python
def funcao_a():
    x = 10  # Alocado na stack
    funcao_b()
    print(x)  # x ainda existe

def funcao_b():
    y = 20  # Alocado na stack
    print(y)
    # Quando funcao_b termina, y é automaticamente removida da stack

funcao_a()
```

**Visualização da Stack:**

```
┌─────────────┐
│  main()     │ ← Stack pointer
├─────────────┤
│  funcao_a() │
│  x = 10     │
├─────────────┤
│  funcao_b() │
│  y = 20     │ ← Topo da stack
└─────────────┘
    ↓
(funcao_b termina)
    ↓
┌─────────────┐
│  main()     │
├─────────────┤
│  funcao_a() │
│  x = 10     │ ← Stack pointer
└─────────────┘
```

### 3.2 Heap

**Características:**
- Memória dinâmica e mais lenta
- Tamanho flexível (limitado pela RAM)
- Gerenciada pelo programador (C) ou Garbage Collector (Python)
- Usada para: objetos, listas, dicionários

```python
# Python aloca automaticamente no heap
lista = [1, 2, 3, 4, 5]  # Lista criada no heap
dados = {"nome": "João"}  # Dict criado no heap

# Em C, seria manual:
# int* lista = malloc(5 * sizeof(int));  // Aloca no heap
# free(lista);  // Precisa liberar manualmente
```

### 3.3 Stack vs Heap - Comparação

| Aspecto | Stack | Heap |
|---------|-------|------|
| **Velocidade** | Rápida (cache-friendly) | Mais lenta |
| **Tamanho** | Limitado (~MB) | Grande (~GB) |
| **Alocação** | Automática | Manual/GC |
| **Fragmentação** | Não ocorre | Pode ocorrer |
| **Thread-safe** | Sim (cada thread tem sua stack) | Não (requer sincronização) |

### 💡 Problema: Stack Overflow

```python
def recursao_infinita(n):
    print(n)
    return recursao_infinita(n + 1)  # Cada chamada usa stack!

# recursao_infinita(0)  # RecursionError: maximum recursion depth exceeded
# Python limita a ~1000 chamadas por padrão
import sys
print(f"Limite de recursão: {sys.getrecursionlimit()}")
```

### 💡 Problema: Memory Leak (Python tem GC, mas pode ocorrer)

```python
import weakref

# PROBLEMA: Referências circulares
class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

a = Node(1)
b = Node(2)
a.next = b
b.next = a  # Referência circular!
# Mesmo deletando, objetos ficam na memória até GC rodar

# SOLUÇÃO: Usar weakref
class NodeFixed:
    def __init__(self, value):
        self.value = value
        self.next = None  # Use weakref.ref() para evitar ciclos
```

---

## 4. Processos e Threads

### 4.1 Processo

Um **processo** é uma instância de um programa em execução.

**Características:**
- Espaço de memória isolado
- Pesado (cria cópia de memória)
- Comunicação via IPC (pipes, sockets)
- Crash de um processo não afeta outros

```
┌──────────────────────────────────────┐
│         Processo 1                   │
│  ┌────────────────────────────────┐  │
│  │  Código                        │  │
│  ├────────────────────────────────┤  │
│  │  Stack                         │  │
│  ├────────────────────────────────┤  │
│  │  Heap                          │  │
│  ├────────────────────────────────┤  │
│  │  Variáveis Globais             │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│         Processo 2 (isolado)         │
│  ┌────────────────────────────────┐  │
│  │  Código (cópia)                │  │
│  ├────────────────────────────────┤  │
│  │  Stack                         │  │
│  ├────────────────────────────────┤  │
│  │  Heap                          │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### 4.2 Thread

Uma **thread** é uma unidade de execução dentro de um processo.

**Características:**
- Compartilha memória do processo
- Leve (não copia memória)
- Comunicação direta via memória compartilhada
- Crash de uma thread pode derrubar processo inteiro

```
┌──────────────────────────────────────┐
│         Processo                     │
│  ┌────────────────────────────────┐  │
│  │  Código (compartilhado)        │  │
│  ├────────────────────────────────┤  │
│  │  Heap (compartilhado)          │  │
│  ├────────────────────────────────┤  │
│  │  Variáveis Globais (comp.)     │  │
│  ├────────────────────────────────┤  │
│  │  Thread 1: Stack própria       │  │
│  ├────────────────────────────────┤  │
│  │  Thread 2: Stack própria       │  │
│  ├────────────────────────────────┤  │
│  │  Thread 3: Stack própria       │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### 4.3 Processos vs Threads - Comparação

| Aspecto | Processo | Thread |
|---------|----------|--------|
| **Memória** | Isolada | Compartilhada |
| **Criação** | Lento (~ms) | Rápido (~μs) |
| **Overhead** | Alto | Baixo |
| **Comunicação** | IPC (lento) | Memória (rápido) |
| **Segurança** | Isolado | Race conditions |
| **Uso no Python** | Multiprocessing | Threading |

### 💡 Quando usar cada um?

```python
import threading
import multiprocessing
import time

# TAREFA CPU-BOUND (cálculos pesados)
def tarefa_cpu(n):
    result = 0
    for i in range(n):
        result += i ** 2
    return result

# TAREFA I/O-BOUND (espera por rede/disco)
def tarefa_io():
    time.sleep(1)  # Simula chamada de API
    return "Dados recebidos"

# ❌ THREADS não ajudam com CPU-bound (devido ao GIL)
start = time.time()
threads = [threading.Thread(target=tarefa_cpu, args=(10_000_000,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
print(f"4 threads CPU-bound: {time.time() - start:.2f}s")  # ~4s

# ✅ PROCESSOS ajudam com CPU-bound
start = time.time()
with multiprocessing.Pool(4) as pool:
    pool.map(tarefa_cpu, [10_000_000] * 4)
print(f"4 processos CPU-bound: {time.time() - start:.2f}s")  # ~1s

# ✅ THREADS ajudam com I/O-bound
start = time.time()
threads = [threading.Thread(target=tarefa_io) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
print(f"10 threads I/O-bound: {time.time() - start:.2f}s")  # ~1s (não 10s!)
```

---

## 5. System Calls e Kernel

### 5.1 User Space vs Kernel Space

```
┌─────────────────────────────────────────┐
│         User Space                      │
│  ┌─────────────────────────────────┐   │
│  │  Aplicação Python                │   │
│  │  (FastAPI, seu código)           │   │
│  └─────────────┬───────────────────┘   │
│                │                         │
│                │ System Call             │
│                ↓                         │
├─────────────────────────────────────────┤
│         Kernel Space                    │
│  ┌─────────────────────────────────┐   │
│  │  Sistema Operacional Linux       │   │
│  │  - Gerencia memória              │   │
│  │  - Gerencia processos            │   │
│  │  - Gerencia I/O                  │   │
│  │  - Gerencia rede                 │   │
│  └─────────────┬───────────────────┘   │
│                │                         │
│                ↓                         │
├─────────────────────────────────────────┤
│         Hardware                        │
│  CPU | RAM | Disco | Rede               │
└─────────────────────────────────────────┘
```

### 5.2 O que são System Calls?

**System calls** são funções que solicitam serviços do kernel.

Exemplos:
- `open()`, `read()`, `write()`, `close()` - Arquivos
- `socket()`, `connect()`, `send()`, `recv()` - Rede
- `fork()`, `exec()`, `wait()` - Processos
- `malloc()`, `free()` - Memória

```python
# Python esconde system calls, mas elas estão lá!
import os

# Isso chama a system call open()
fd = os.open("arquivo.txt", os.O_RDWR | os.O_CREAT)

# Isso chama a system call write()
os.write(fd, b"Hello, World!")

# Isso chama a system call close()
os.close(fd)

# Forma pythônica (mas ainda usa system calls internamente)
with open("arquivo.txt", "w") as f:
    f.write("Hello, World!")
```

### 5.3 Por que System Calls são lentas?

1. **Context Switch**: CPU muda de user mode para kernel mode
2. **Validação**: Kernel valida permissões e parâmetros
3. **Operação real**: Kernel executa operação
4. **Context Switch de volta**: CPU retorna para user mode

```python
import time

# Muitas system calls
start = time.time()
for i in range(10000):
    with open("test.txt", "a") as f:  # open() e close() = 2 syscalls
        f.write("x")  # write() = 1 syscall
# Total: 30.000 system calls
print(f"10k writes individuais: {time.time() - start:.2f}s")

# Poucas system calls
start = time.time()
with open("test.txt", "a") as f:
    for i in range(10000):
        f.write("x")  # Sistema de buffering reduz syscalls
# Total: ~10 system calls (devido a buffering)
print(f"10k writes em batch: {time.time() - start:.2f}s")

# Limpeza
os.remove("test.txt")
```

**Resultado:** Batch é 100x mais rápido!

---

## 6. Como Python Executa Código

### 6.1 Arquitetura do Python

```
┌─────────────────────────────────────────┐
│  Código Python (.py)                    │
│  def hello():                           │
│      print("Hello")                     │
└─────────────┬───────────────────────────┘
              │
              ↓ Compilação
┌─────────────────────────────────────────┐
│  Bytecode (.pyc)                        │
│  LOAD_GLOBAL (print)                    │
│  LOAD_CONST ("Hello")                   │
│  CALL_FUNCTION                          │
└─────────────┬───────────────────────────┘
              │
              ↓ Interpretação
┌─────────────────────────────────────────┐
│  Python Virtual Machine (PVM)           │
│  - Interpreta bytecode                  │
│  - Gerencia memória (heap)              │
│  - Garbage Collection                   │
│  - Global Interpreter Lock (GIL)        │
└─────────────┬───────────────────────────┘
              │
              ↓ System calls
┌─────────────────────────────────────────┐
│  Sistema Operacional                    │
└─────────────────────────────────────────┘
```

### 6.2 Global Interpreter Lock (GIL)

**O que é?** Um mutex que protege acesso aos objetos Python.

**Problema:** Apenas uma thread pode executar bytecode Python por vez.

```
┌─────────────────────────────────────────┐
│         CPU com 4 cores                 │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐   │
│  │Core1│  │Core2│  │Core3│  │Core4│   │
│  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘   │
└─────┼──────┼──────┼──────┼─────────┘
      │      │      │      │
      │      │      │      │
      ↓      ↓      ↓      ↓
┌─────────────────────────────────────────┐
│  Python Process                         │
│  ┌───────────────────────────────────┐  │
│  │  GIL (apenas 1 thread por vez)    │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │ Thread 1 (executando)       │  │  │ → Usa apenas 1 core
│  │  ├─────────────────────────────┤  │  │
│  │  │ Thread 2 (esperando GIL)    │  │  │
│  │  ├─────────────────────────────┤  │  │
│  │  │ Thread 3 (esperando GIL)    │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 6.3 Soluções para o GIL

```python
# ❌ PROBLEMA: GIL limita threads
import threading
import time

def tarefa_cpu():
    total = 0
    for i in range(10_000_000):
        total += i
    return total

start = time.time()
threads = [threading.Thread(target=tarefa_cpu) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
print(f"Threads: {time.time() - start:.2f}s")  # ~4s (não usa múltiplos cores!)

# ✅ SOLUÇÃO 1: Multiprocessing (processos = GILs separados)
import multiprocessing

start = time.time()
with multiprocessing.Pool(4) as pool:
    pool.map(tarefa_cpu, range(4))
print(f"Multiprocessing: {time.time() - start:.2f}s")  # ~1s (usa 4 cores!)

# ✅ SOLUÇÃO 2: Async para I/O-bound (não precisa de múltiplos cores)
import asyncio

async def tarefa_io():
    await asyncio.sleep(1)  # Simula chamada de API
    return "done"

start = time.time()
async def main():
    tasks = [tarefa_io() for _ in range(10)]
    await asyncio.gather(*tasks)
asyncio.run(main())
print(f"Async: {time.time() - start:.2f}s")  # ~1s (não 10s!)

# ✅ SOLUÇÃO 3: Bibliotecas em C (numpy, pandas liberam o GIL)
import numpy as np

start = time.time()
arrays = [np.arange(10_000_000) for _ in range(4)]
results = [arr.sum() for arr in arrays]
print(f"NumPy: {time.time() - start:.2f}s")  # Rápido pois C libera GIL
```

### 6.4 Garbage Collection

Python usa **reference counting** + **cycle detector**.

```python
import sys

# Reference Counting
a = []  # refcount = 1
b = a   # refcount = 2
c = a   # refcount = 3
print(sys.getrefcount(a))  # 4 (inclui getrefcount)

del b   # refcount = 2
del c   # refcount = 1
del a   # refcount = 0 → objeto é deletado imediatamente!

# Cycle Detector (para referências circulares)
import gc

class Node:
    def __init__(self):
        self.ref = None

a = Node()
b = Node()
a.ref = b
b.ref = a  # Ciclo!

del a, b  # Refcount não zera devido ao ciclo
# Garbage collector detecta e limpa ciclos periodicamente

# Forçar coleta
gc.collect()
print(f"Objetos coletados: {gc.collect()}")
```

---

## 🎓 Resumo - O que você aprendeu

### Conceitos-chave:

1. **Hardware**: CPU, cache, RAM, storage - hierarquia de velocidade
2. **Memória**: Stack (rápida, limitada) vs Heap (flexível, mais lenta)
3. **Concorrência**:
   - Threads: leves, memória compartilhada, limitadas por GIL em Python
   - Processos: pesados, isolados, contornam o GIL
4. **Sistema Operacional**: System calls são a ponte entre código e hardware
5. **Python**: Interpretado, com GIL, garbage collected

### Decisões que você pode tomar agora:

✅ **Usar async/await** para I/O-bound (APIs, banco de dados)
✅ **Usar multiprocessing** para CPU-bound (processamento de imagens, ML)
✅ **Evitar alocações desnecessárias** (reuse objetos, use generators)
✅ **Minimizar system calls** (use buffering, batch operations)
✅ **Entender trade-offs** entre performance e produtividade

---

## 📝 Próximos Passos

1. Veja os **exemplos práticos** em [`../exemplos/`](../exemplos/)
2. Faça os **exercícios** em [`../exercicios/`](../exercicios/)
3. Avance para o **[Módulo 02 - Protocolos](../../02-protocolos/teoria/README.md)**

---

## 📚 Referências

- [Python Internals](https://realpython.com/python-gil/)
- [Computer Systems: A Programmer's Perspective](http://csapp.cs.cmu.edu/)
- [Understanding the Linux Kernel](https://www.oreilly.com/library/view/understanding-the-linux/0596005652/)
