"""
Exemplo 1: Comparação entre Sync e Async para requisições HTTP

Execute: python 01_sync_vs_async.py
"""

import time
import requests
import asyncio
import aiohttp


# ============================================
# SYNC - Bloqueante
# ============================================

def fetch_sync(url):
    """Requisição síncrona bloqueante"""
    response = requests.get(url)
    return len(response.content)


def test_sync(urls):
    """Testa múltiplas requisições síncronas"""
    print("🔄 Testando SYNC (bloqueante)...")
    inicio = time.time()

    resultados = []
    for url in urls:
        tamanho = fetch_sync(url)
        resultados.append(tamanho)
        print(f"  ✓ {url}: {tamanho} bytes")

    duracao = time.time() - inicio
    print(f"⏱️  Tempo total SYNC: {duracao:.2f}s\n")
    return duracao


# ============================================
# ASYNC - Não-bloqueante
# ============================================

async def fetch_async(session, url):
    """Requisição assíncrona não-bloqueante"""
    async with session.get(url) as response:
        content = await response.read()
        return len(content)


async def test_async(urls):
    """Testa múltiplas requisições assíncronas"""
    print("⚡ Testando ASYNC (não-bloqueante)...")
    inicio = time.time()

    async with aiohttp.ClientSession() as session:
        # Cria todas as tarefas
        tasks = [fetch_async(session, url) for url in urls]

        # Executa todas em paralelo
        resultados = await asyncio.gather(*tasks)

        for url, tamanho in zip(urls, resultados):
            print(f"  ✓ {url}: {tamanho} bytes")

    duracao = time.time() - inicio
    print(f"⏱️  Tempo total ASYNC: {duracao:.2f}s\n")
    return duracao


# ============================================
# THREADING - Intermediário
# ============================================

from concurrent.futures import ThreadPoolExecutor


def test_threading(urls):
    """Testa múltiplas requisições com threading"""
    print("🧵 Testando THREADING...")
    inicio = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        resultados = list(executor.map(fetch_sync, urls))

        for url, tamanho in zip(urls, resultados):
            print(f"  ✓ {url}: {tamanho} bytes")

    duracao = time.time() - inicio
    print(f"⏱️  Tempo total THREADING: {duracao:.2f}s\n")
    return duracao


# ============================================
# MAIN
# ============================================

def main():
    """Compara as três abordagens"""
    print("=" * 60)
    print("🚀 Comparação: SYNC vs THREADING vs ASYNC")
    print("=" * 60)
    print()

    # URLs para testar (cada uma demora ~1 segundo)
    urls = [
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/1',
    ]

    print(f"📊 Testando com {len(urls)} requisições (1s cada)\n")

    # Teste 1: SYNC
    tempo_sync = test_sync(urls)

    # Teste 2: THREADING
    tempo_threading = test_threading(urls)

    # Teste 3: ASYNC
    tempo_async = asyncio.run(test_async(urls))

    # Comparação
    print("=" * 60)
    print("📈 RESULTADOS:")
    print("=" * 60)
    print(f"SYNC:      {tempo_sync:.2f}s  (baseline)")
    print(f"THREADING: {tempo_threading:.2f}s  ({tempo_sync/tempo_threading:.1f}x mais rápido)")
    print(f"ASYNC:     {tempo_async:.2f}s  ({tempo_sync/tempo_async:.1f}x mais rápido)")
    print()

    print("💡 CONCLUSÕES:")
    print("- SYNC é sequencial: tempo total = soma de todos")
    print("- THREADING e ASYNC são concorrentes: tempo ≈ request mais lento")
    print("- ASYNC é mais eficiente com milhares de conexões")
    print("- THREADING é mais simples para casos pequenos (<100 requests)")


if __name__ == '__main__':
    main()
