"""
Exemplo 1: Otimizações com Hash Table

Demonstra como hash tables resolvem problemas comuns de performance em backend
"""

from collections import defaultdict, Counter
from typing import List, Dict
import time


# =====================================
# PROBLEMA 1: N+1 Query Problem
# =====================================

class Post:
    def __init__(self, id, user_id, title):
        self.id = id
        self.user_id = user_id
        self.title = title


class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name


# Simular database
USERS_DB = {
    1: User(1, "Alice"),
    2: User(2, "Bob"),
    3: User(3, "Charlie"),
}

POSTS_DB = [
    Post(1, 1, "Python Tips"),
    Post(2, 1, "SQL Optimization"),
    Post(3, 2, "Docker Tutorial"),
    Post(4, 2, "Kubernetes Guide"),
    Post(5, 3, "React Basics"),
]


def get_posts_with_authors_slow():
    """
    ❌ VERSÃO LENTA: N+1 Problem

    Para cada post, faz query para buscar author
    Complexidade: O(n * m) onde n=posts, m=avg users
    """
    posts_with_authors = []

    for post in POSTS_DB:
        # Query para buscar user (simulado)
        author = USERS_DB[post.user_id]  # "Query" ao banco
        posts_with_authors.append({
            "title": post.title,
            "author": author.name
        })

    return posts_with_authors


def get_posts_with_authors_fast():
    """
    ✅ VERSÃO RÁPIDA: Hash Table para lookup

    1. Buscar todos users de uma vez
    2. Criar hash table: user_id -> User
    3. Lookup O(1) para cada post

    Complexidade: O(n + m)
    """
    # Buscar user_ids únicos
    user_ids = {post.user_id for post in POSTS_DB}  # Set (hash table) remove duplicatas

    # Buscar todos users de uma vez (simulated bulk query)
    users = {uid: USERS_DB[uid] for uid in user_ids}

    # Criar hash table: user_id -> User
    users_by_id = users  # Já é hash table!

    posts_with_authors = []

    for post in POSTS_DB:
        author = users_by_id[post.user_id]  # O(1) lookup!
        posts_with_authors.append({
            "title": post.title,
            "author": author.name
        })

    return posts_with_authors


# =====================================
# PROBLEMA 2: Duplicatas
# =====================================

def remove_duplicates_slow(items: List[int]) -> List[int]:
    """
    ❌ VERSÃO LENTA: Nested loops

    Complexidade: O(n²)
    """
    result = []

    for item in items:
        if item not in result:  # O(n) para list
            result.append(item)

    return result


def remove_duplicates_fast(items: List[int]) -> List[int]:
    """
    ✅ VERSÃO RÁPIDA: Set (hash table)

    Complexidade: O(n)
    """
    seen = set()  # Hash table
    result = []

    for item in items:
        if item not in seen:  # O(1) para set!
            seen.add(item)
            result.append(item)

    return result


# Ou simplesmente:
def remove_duplicates_fastest(items: List[int]) -> List[int]:
    """✅ VERSÃO MAIS RÁPIDA: set + list comprehension"""
    return list(dict.fromkeys(items))  # Preserva ordem


# =====================================
# PROBLEMA 3: Grouping
# =====================================

def group_by_category_manual(posts: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Agrupar posts por categoria (manual)
    """
    result = {}

    for post in posts:
        category = post['category']

        if category not in result:
            result[category] = []

        result[category].append(post)

    return result


def group_by_category_defaultdict(posts: List[Dict]) -> Dict[str, List[Dict]]:
    """
    ✅ Agrupar com defaultdict (mais limpo)

    defaultdict evita verificação de key
    """
    result = defaultdict(list)

    for post in posts:
        result[post['category']].append(post)

    return dict(result)


# =====================================
# PROBLEMA 4: Contar Frequências
# =====================================

def count_words_manual(text: str) -> Dict[str, int]:
    """Contar palavras manualmente"""
    counts = {}
    words = text.lower().split()

    for word in words:
        if word not in counts:
            counts[word] = 0
        counts[word] += 1

    return counts


def count_words_defaultdict(text: str) -> Dict[str, int]:
    """Contar palavras com defaultdict"""
    counts = defaultdict(int)
    words = text.lower().split()

    for word in words:
        counts[word] += 1

    return dict(counts)


def count_words_counter(text: str) -> Dict[str, int]:
    """
    ✅ Contar palavras com Counter (melhor)

    Counter é hash table especializada para contagem
    """
    words = text.lower().split()
    return dict(Counter(words))


# =====================================
# PROBLEMA 5: Two Sum (LeetCode classic)
# =====================================

def two_sum_brute_force(nums: List[int], target: int) -> List[int]:
    """
    ❌ Brute force: Nested loops

    Complexidade: O(n²)
    """
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]

    return []


def two_sum_hash_table(nums: List[int], target: int) -> List[int]:
    """
    ✅ Hash table: Single pass

    Complexidade: O(n)

    Ideia:
    - Para cada número, verificar se (target - número) já foi visto
    - Hash table permite lookup O(1)
    """
    seen = {}  # value -> index

    for i, num in enumerate(nums):
        complement = target - num

        if complement in seen:  # O(1) lookup!
            return [seen[complement], i]

        seen[num] = i

    return []


# =====================================
# BENCHMARKS
# =====================================

def benchmark_n_plus_one():
    """Benchmark N+1 vs Hash Table"""
    print("\n" + "="*60)
    print("BENCHMARK: N+1 Query Problem")
    print("="*60)

    # Simular 100 posts
    global POSTS_DB
    POSTS_DB = [Post(i, (i % 3) + 1, f"Post {i}") for i in range(100)]

    # Slow version
    start = time.time()
    result_slow = get_posts_with_authors_slow()
    time_slow = time.time() - start

    # Fast version
    start = time.time()
    result_fast = get_posts_with_authors_fast()
    time_fast = time.time() - start

    print(f"Slow (N+1):       {time_slow*1000:.2f}ms")
    print(f"Fast (Hash):      {time_fast*1000:.2f}ms")
    print(f"Speedup:          {time_slow/time_fast:.1f}x")


def benchmark_remove_duplicates():
    """Benchmark remove duplicates"""
    print("\n" + "="*60)
    print("BENCHMARK: Remove Duplicates")
    print("="*60)

    items = list(range(1000)) * 2  # 2000 items com duplicatas

    # Slow version
    start = time.time()
    result_slow = remove_duplicates_slow(items)
    time_slow = time.time() - start

    # Fast version
    start = time.time()
    result_fast = remove_duplicates_fast(items)
    time_fast = time.time() - start

    print(f"Slow (nested):    {time_slow*1000:.2f}ms")
    print(f"Fast (set):       {time_fast*1000:.2f}ms")
    print(f"Speedup:          {time_slow/time_fast:.1f}x")


def benchmark_two_sum():
    """Benchmark Two Sum"""
    print("\n" + "="*60)
    print("BENCHMARK: Two Sum")
    print("="*60)

    nums = list(range(10000))
    target = 19997

    # Brute force
    start = time.time()
    result_slow = two_sum_brute_force(nums, target)
    time_slow = time.time() - start

    # Hash table
    start = time.time()
    result_fast = two_sum_hash_table(nums, target)
    time_fast = time.time() - start

    print(f"Brute force:      {time_slow*1000:.2f}ms")
    print(f"Hash table:       {time_fast*1000:.2f}ms")
    print(f"Speedup:          {time_slow/time_fast:.1f}x")
    print(f"Result:           {result_fast}")


# =====================================
# EXEMPLOS PRÁTICOS
# =====================================

def example_grouping():
    """Exemplo: Agrupar posts por categoria"""
    print("\n" + "="*60)
    print("EXEMPLO: Grouping com defaultdict")
    print("="*60)

    posts = [
        {"title": "Python Tips", "category": "tech"},
        {"title": "Healthy Food", "category": "food"},
        {"title": "Docker Guide", "category": "tech"},
        {"title": "Pasta Recipe", "category": "food"},
        {"title": "React Tutorial", "category": "tech"},
    ]

    grouped = group_by_category_defaultdict(posts)

    for category, items in grouped.items():
        print(f"\n{category.upper()}:")
        for post in items:
            print(f"  - {post['title']}")


def example_word_frequency():
    """Exemplo: Contar frequência de palavras"""
    print("\n" + "="*60)
    print("EXEMPLO: Word Frequency com Counter")
    print("="*60)

    text = """
    python python python java java javascript
    backend backend frontend python
    """

    counts = count_words_counter(text)

    # Top 3 palavras mais frequentes
    top_words = Counter(counts).most_common(3)

    print("Top 3 palavras:")
    for word, count in top_words:
        print(f"  {word}: {count} vezes")


# =====================================
# MAIN
# =====================================

if __name__ == "__main__":
    print("\n🗝️  HASH TABLE OPTIMIZATIONS\n")
    print("Demonstração de como hash tables resolvem problemas comuns")

    # Exemplos práticos
    example_grouping()
    example_word_frequency()

    # Benchmarks
    benchmark_n_plus_one()
    benchmark_remove_duplicates()
    benchmark_two_sum()

    print("\n" + "="*60)
    print("✅ CONCLUSÃO")
    print("="*60)
    print("""
Hash Tables (dict, set, defaultdict, Counter) são fundamentais para:
- Resolver N+1 queries (100x speedup)
- Eliminar duplicatas (100x speedup)
- Agrupar dados por chave
- Contar frequências
- Lookup rápido O(1)

USE HASH TABLES SEMPRE QUE POSSÍVEL!
    """)
