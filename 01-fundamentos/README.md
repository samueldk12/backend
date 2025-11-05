# 01 - Fundamentos de Backend

## Índice

1. [CPU e Processamento](#cpu-e-processamento)
2. [Memória](#memória)
3. [Threads vs Processos](#threads-vs-processos)
4. [GIL (Global Interpreter Lock)](#gil-global-interpreter-lock)
5. [Async/Await](#asyncawait)
6. [Quando Usar Cada Abordagem](#quando-usar-cada-abordagem)
7. [Exemplos Práticos](#exemplos-práticos)

---

## CPU e Processamento

### O que é CPU-Bound vs I/O-Bound?

**CPU-Bound**: Operação limitada pela velocidade do processador
```python
# Exemplo: Cálculos matemáticos pesados
def calcular_fibonacci(n):
    if n <= 1:
        return n
    return calcular_fibonacci(n-1) + calcular_fibonacci(n-2)

# Esta operação usa 100% da CPU
result = calcular_fibonacci(35)  # Demora vários segundos
```

**I/O-Bound**: Operação limitada por entrada/saída (disco, rede)
```python
# Exemplo: Requisições HTTP
import requests

# Esta operação espera pela rede (I/O)
response = requests.get('https://api.exemplo.com/dados')

# A CPU fica OCIOSA esperando a resposta
# Apenas 2-5% de uso de CPU durante a espera
```

### Como Identificar?

```python
import time
import psutil  # pip install psutil

def medir_operacao():
    cpu_antes = psutil.cpu_percent(interval=0.1)

    inicio = time.time()
    # Sua operação aqui
    requests.get('https://httpbin.org/delay/2')
    fim = time.time()

    cpu_depois = psutil.cpu_percent(interval=0.1)

    print(f"Tempo: {fim - inicio:.2f}s")
    print(f"CPU média: {(cpu_antes + cpu_depois) / 2:.1f}%")

    # Se CPU < 20% e tempo > 1s = I/O-Bound
    # Se CPU > 80% = CPU-Bound
```

---

## Memória

### Stack vs Heap

**Stack Memory** (Pilha)
- Rápida e automática
- Tamanho limitado (~1-8 MB)
- Variáveis locais, parâmetros de função
- Limpa automaticamente ao sair do escopo

```python
def funcao():
    x = 10  # Alocado na STACK
    y = 20  # Alocado na STACK
    return x + y  # x e y são desalocados automaticamente
```

**Heap Memory** (Monte)
- Mais lenta, gerenciada manualmente (ou por GC)
- Tamanho grande (GBs disponíveis)
- Objetos, listas, dicionários
- Precisa de Garbage Collection

```python
def criar_lista():
    lista = [1, 2, 3, 4, 5]  # Alocada no HEAP
    return lista
    # Lista NÃO é desalocada - fica no HEAP
    # Garbage Collector vai limpar depois

grande_lista = [0] * 10_000_000  # 10M elementos no HEAP
```

### Memory Leaks em Backend

```python
# ❌ RUIM - Memory Leak
cache_global = {}

def processar_request(user_id, dados):
    # Cache cresce infinitamente!
    cache_global[user_id] = dados
    return processar(dados)

# ✅ BOM - Cache com limite
from functools import lru_cache

@lru_cache(maxsize=1000)  # Apenas 1000 itens em cache
def processar_dados(dados_hash):
    return processar(dados)
```

---

## Threads vs Processos

### Thread (Linha de Execução)

**Características:**
- Compartilha memória com outras threads
- Leve (~8 KB de overhead)
- Comunicação rápida (memória compartilhada)
- ⚠️ Risco de race conditions

```python
import threading
import time

contador = 0  # Memória COMPARTILHADA

def incrementar():
    global contador
    for _ in range(1_000_000):
        contador += 1  # ⚠️ Race condition!

# Criar 2 threads
t1 = threading.Thread(target=incrementar)
t2 = threading.Thread(target=incrementar)

t1.start()
t2.start()
t1.join()
t2.join()

print(f"Contador: {contador}")
# Esperado: 2_000_000
# Real: ~1_200_000 (PERDEU dados!)
```

**Solução: Lock**
```python
import threading

contador = 0
lock = threading.Lock()  # Mutex

def incrementar_seguro():
    global contador
    for _ in range(1_000_000):
        with lock:  # Apenas 1 thread por vez
            contador += 1

# Agora funciona corretamente!
# Mas é mais lento devido ao lock
```

### Process (Processo)

**Características:**
- Memória isolada (cada processo tem seu espaço)
- Pesado (~10-50 MB de overhead)
- Comunicação lenta (IPC - Inter Process Communication)
- ✅ Sem race conditions (memória isolada)

```python
from multiprocessing import Process, Queue
import os

def worker(queue, numero):
    # Cada processo tem PID diferente
    print(f"Processo {os.getpid()} processando {numero}")
    resultado = numero * numero
    queue.put(resultado)

if __name__ == '__main__':
    queue = Queue()  # IPC - comunicação entre processos

    processos = []
    for i in range(4):
        p = Process(target=worker, args=(queue, i))
        p.start()
        processos.append(p)

    # Esperar todos
    for p in processos:
        p.join()

    # Coletar resultados
    resultados = []
    while not queue.empty():
        resultados.append(queue.get())

    print(f"Resultados: {resultados}")
```

### Quando usar cada um?

| Operação | Thread | Process |
|----------|--------|---------|
| I/O-Bound (HTTP, DB) | ✅ Sim | ❌ Overhead |
| CPU-Bound (cálculos) | ❌ GIL limita | ✅ Sim |
| Memória compartilhada | ✅ Sim | ❌ Não |
| Isolamento/Segurança | ❌ Não | ✅ Sim |

---

## GIL (Global Interpreter Lock)

### O que é?

**GIL** é um mutex que permite apenas **1 thread executar bytecode Python por vez**.

```python
import threading
import time

# CPU-Bound com threads
def calcular():
    total = 0
    for i in range(10_000_000):
        total += i
    return total

# Single Thread
inicio = time.time()
calcular()
calcular()
print(f"1 thread: {time.time() - inicio:.2f}s")  # ~2.0s

# Multi Thread (deveria ser 2x mais rápido, certo?)
inicio = time.time()
t1 = threading.Thread(target=calcular)
t2 = threading.Thread(target=calcular)
t1.start()
t2.start()
t1.join()
t2.join()
print(f"2 threads: {time.time() - inicio:.2f}s")  # ~2.0s também!

# ❌ NÃO ficou mais rápido por causa do GIL!
```

### Por que o GIL existe?

1. **Simplicidade**: Evita race conditions em C extensions
2. **Performance Single-Thread**: CPython é otimizado para 1 thread
3. **C Extensions**: Bibliotecas C não precisam ser thread-safe

### Quando o GIL NÃO importa?

```python
# ✅ I/O Operations - GIL é LIBERADO durante I/O!
import threading
import requests

def fetch_url(url):
    # Durante requests.get(), GIL é LIBERADO
    response = requests.get(url)
    return len(response.content)

# Isso É mais rápido com threads!
urls = ['https://google.com'] * 10

threads = []
for url in urls:
    t = threading.Thread(target=fetch_url, args=(url,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
```

### Como Contornar o GIL?

**1. Multiprocessing** (CPU-Bound)
```python
from multiprocessing import Pool

def calcular(n):
    return sum(range(n))

# Cada processo tem seu próprio GIL!
with Pool(4) as pool:
    resultados = pool.map(calcular, [10_000_000] * 4)
```

**2. Async/Await** (I/O-Bound)
```python
import asyncio
import aiohttp

async def fetch_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

# Uma única thread, mas concorrente!
async def main():
    urls = ['https://google.com'] * 100
    tasks = [fetch_url(url) for url in urls]
    resultados = await asyncio.gather(*tasks)

asyncio.run(main())
```

---

## Async/Await

### Como funciona?

**Sync (Bloqueante)**
```python
import time

def fazer_cafe():
    print("☕ Fervendo água...")
    time.sleep(3)  # Bloqueia TUDO por 3s
    print("☕ Café pronto!")

def fazer_torrada():
    print("🍞 Torrando pão...")
    time.sleep(2)  # Bloqueia TUDO por 2s
    print("🍞 Torrada pronta!")

# Total: 3s + 2s = 5s
fazer_cafe()
fazer_torrada()
```

**Async (Não-bloqueante)**
```python
import asyncio

async def fazer_cafe():
    print("☕ Fervendo água...")
    await asyncio.sleep(3)  # Libera CPU para outras tarefas
    print("☕ Café pronto!")

async def fazer_torrada():
    print("🍞 Torrando pão...")
    await asyncio.sleep(2)  # Libera CPU para outras tarefas
    print("🍞 Torrada pronta!")

# Total: max(3s, 2s) = 3s (paralelo!)
async def main():
    await asyncio.gather(
        fazer_cafe(),
        fazer_torrada()
    )

asyncio.run(main())
```

### Event Loop

```python
import asyncio

# Event Loop = Orquestrador de tarefas assíncronas

async def tarefa(nome, duracao):
    print(f"{nome}: Iniciando")
    await asyncio.sleep(duracao)
    print(f"{nome}: Concluída")
    return nome

async def main():
    # Event Loop gerencia estas 3 tarefas
    resultados = await asyncio.gather(
        tarefa("A", 2),
        tarefa("B", 1),
        tarefa("C", 3)
    )
    print(f"Resultados: {resultados}")

# Output:
# A: Iniciando
# B: Iniciando
# C: Iniciando
# B: Concluída (1s)
# A: Concluída (2s)
# C: Concluída (3s)
# Resultados: ['A', 'B', 'C']
```

### Async HTTP Requests

```python
import asyncio
import aiohttp
import time

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# Teste
urls = ['https://httpbin.org/delay/1'] * 10

# Sync: 10 requests * 1s = 10s
inicio = time.time()
# [requests.get(url) for url in urls]  # 10s

# Async: 10 requests em paralelo = 1s
inicio = time.time()
asyncio.run(fetch_all(urls))
print(f"Tempo: {time.time() - inicio:.2f}s")  # ~1s
```

---

## Quando Usar Cada Abordagem

### Decision Tree

```
┌─────────────────────────────────┐
│ Sua operação é CPU ou I/O?      │
└────────────┬────────────────────┘
             │
     ┌───────┴────────┐
     │                │
  CPU-Bound      I/O-Bound
     │                │
     ▼                ▼
┌─────────┐    ┌──────────────┐
│Multi-   │    │ Quantas      │
│process  │    │ conexões?    │
└─────────┘    └──────┬───────┘
                      │
              ┌───────┴────────┐
              │                │
           < 1000          > 1000
              │                │
              ▼                ▼
        ┌──────────┐      ┌─────────┐
        │Threading │      │ Async/  │
        │          │      │ Await   │
        └──────────┘      └─────────┘
```

### Exemplos Práticos

**1. Web Scraping (I/O-Bound, < 100 URLs)**
```python
# Use Threading
from concurrent.futures import ThreadPoolExecutor
import requests

def scrape(url):
    return requests.get(url).text

urls = ['https://site.com/page' + str(i) for i in range(50)]

with ThreadPoolExecutor(max_workers=10) as executor:
    resultados = list(executor.map(scrape, urls))
```

**2. API com Muitas Requisições (I/O-Bound, > 1000)**
```python
# Use Async/Await
from fastapi import FastAPI
import asyncio

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Async DB query
    user = await db.fetch_one(f"SELECT * FROM users WHERE id = {user_id}")

    # Async HTTP call
    async with aiohttp.ClientSession() as session:
        posts = await fetch_user_posts(session, user_id)

    return {"user": user, "posts": posts}
```

**3. Processamento de Imagens (CPU-Bound)**
```python
# Use Multiprocessing
from multiprocessing import Pool
from PIL import Image

def processar_imagem(path):
    img = Image.open(path)
    img = img.resize((800, 600))
    img = img.filter(ImageFilter.SHARPEN)
    img.save(f"processed_{path}")
    return path

imagens = ['foto1.jpg', 'foto2.jpg', ...] * 100

with Pool(8) as pool:  # 8 processos
    pool.map(processar_imagem, imagens)
```

**4. Machine Learning Training (CPU-Bound + GPU)**
```python
# Use Multiprocessing + GPU
import torch
from torch.utils.data import DataLoader

# DataLoader usa multiprocessing internamente
dataloader = DataLoader(
    dataset,
    batch_size=32,
    num_workers=4,  # 4 processos para carregar dados
    pin_memory=True  # Otimiza transferência CPU -> GPU
)

for batch in dataloader:
    # GPU processa batch
    output = model(batch.to('cuda'))
```

---

## Exemplos Práticos

### Exemplo 1: Sync vs Async API Calls

Ver arquivo: `exemplos/01_sync_vs_async.py`

### Exemplo 2: Thread Pool vs Process Pool

Ver arquivo: `exemplos/02_thread_vs_process.py`

### Exemplo 3: GIL Impact Measurement

Ver arquivo: `exemplos/03_gil_impact.py`

---

## Recursos Adicionais

- [Python Concurrency Docs](https://docs.python.org/3/library/concurrency.html)
- [Real Python - Async IO](https://realpython.com/async-io-python/)
- [Understanding the Python GIL](https://realpython.com/python-gil/)

---

## Exercícios

1. Crie um script que baixa 100 URLs e compare o tempo entre sync, threading e async
2. Implemente um rate limiter usando threading.Lock
3. Meça o impacto do GIL em operações CPU-bound vs I/O-bound
4. Crie um worker pool com multiprocessing para processar arquivos CSV

---

## Próximo Módulo

➡️ [02 - Protocolos](../02-protocolos/README.md)
