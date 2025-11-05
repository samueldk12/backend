"""
Exemplo: Trie para Autocomplete

Execute: python 01_trie_autocomplete.py

Demonstra implementação de Trie para autocomplete eficiente.
"""

from typing import List, Optional
import time


# ============================================
# TRIE IMPLEMENTATION
# ============================================

class TrieNode:
    """Nó da Trie"""
    def __init__(self):
        self.children = {}  # char -> TrieNode
        self.is_end_of_word = False
        self.word = None  # Palavra completa (se is_end_of_word)
        self.frequency = 0  # Para ranking de resultados


class Trie:
    """
    Trie (Prefix Tree) para autocomplete

    Complexidade:
    - Insert: O(M) onde M = tamanho da palavra
    - Search: O(M)
    - Prefix search: O(P + N) onde P = prefixo, N = resultados
    """

    def __init__(self):
        self.root = TrieNode()
        self.word_count = 0

    def insert(self, word: str, frequency: int = 1):
        """
        Insere palavra na Trie

        Args:
            word: palavra a inserir
            frequency: frequência/ranking (maior = mais popular)
        """
        node = self.root

        # Percorre caractere por caractere
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]

        # Marca fim da palavra
        node.is_end_of_word = True
        node.word = word
        node.frequency = frequency
        self.word_count += 1

    def search(self, word: str) -> bool:
        """Verifica se palavra existe exatamente"""
        node = self._find_node(word)
        return node is not None and node.is_end_of_word

    def starts_with(self, prefix: str) -> bool:
        """Verifica se alguma palavra começa com prefixo"""
        return self._find_node(prefix) is not None

    def autocomplete(self, prefix: str, max_results: int = 10) -> List[str]:
        """
        Retorna palavras que começam com prefixo

        Args:
            prefix: prefixo a buscar
            max_results: máximo de resultados

        Returns:
            Lista de palavras ordenadas por frequência
        """
        # Encontra nó do prefixo
        node = self._find_node(prefix)

        if node is None:
            return []

        # Coleta todas palavras a partir deste nó
        results = []
        self._collect_words(node, results)

        # Ordena por frequência (descendente)
        results.sort(key=lambda x: x[1], reverse=True)

        # Retorna apenas as palavras (sem frequência)
        return [word for word, _ in results[:max_results]]

    def _find_node(self, prefix: str) -> Optional[TrieNode]:
        """Encontra nó correspondente ao prefixo"""
        node = self.root

        for char in prefix.lower():
            if char not in node.children:
                return None
            node = node.children[char]

        return node

    def _collect_words(self, node: TrieNode, results: List):
        """Coleta recursivamente todas palavras a partir de um nó"""
        if node.is_end_of_word:
            results.append((node.word, node.frequency))

        for child in node.children.values():
            self._collect_words(child, results)

    def delete(self, word: str) -> bool:
        """Remove palavra da Trie"""
        def _delete(node: TrieNode, word: str, depth: int) -> bool:
            if depth == len(word):
                if not node.is_end_of_word:
                    return False

                node.is_end_of_word = False
                self.word_count -= 1

                # Se nó não tem filhos, pode deletar
                return len(node.children) == 0

            char = word[depth]
            if char not in node.children:
                return False

            should_delete = _delete(node.children[char], word, depth + 1)

            if should_delete:
                del node.children[char]
                # Deleta nó se não tem filhos e não é fim de palavra
                return len(node.children) == 0 and not node.is_end_of_word

            return False

        return _delete(self.root, word.lower(), 0)

    def get_stats(self):
        """Retorna estatísticas da Trie"""
        def count_nodes(node: TrieNode) -> int:
            count = 1
            for child in node.children.values():
                count += count_nodes(child)
            return count

        return {
            "words": self.word_count,
            "nodes": count_nodes(self.root)
        }


# ============================================
# COMPARISON: TRIE vs LINEAR SEARCH
# ============================================

def linear_search_autocomplete(words: List[str], prefix: str, max_results: int = 10) -> List[str]:
    """
    Busca linear (naive approach)

    Complexidade: O(N * M) onde N = palavras, M = tamanho médio
    """
    prefix_lower = prefix.lower()
    results = [w for w in words if w.lower().startswith(prefix_lower)]
    return results[:max_results]


def compare_performance():
    """Compara performance Trie vs Linear Search"""
    print("\n" + "="*60)
    print("⏱️  PERFORMANCE COMPARISON")
    print("="*60)

    # Dataset: 100,000 palavras
    words = [f"word{i}" for i in range(100_000)]
    words.extend([f"test{i}" for i in range(10_000)])
    words.extend([f"example{i}" for i in range(5_000)])

    print(f"\nDataset: {len(words):,} words")

    # Build Trie
    print("\n1️⃣  Building Trie...")
    start = time.time()
    trie = Trie()
    for word in words:
        trie.insert(word)
    build_time = time.time() - start
    print(f"   Time: {build_time:.3f}s")
    print(f"   Stats: {trie.get_stats()}")

    # Test Trie search
    print("\n2️⃣  Trie search ('test')...")
    start = time.time()
    trie_results = trie.autocomplete("test", 10)
    trie_time = time.time() - start
    print(f"   Time: {trie_time*1000:.2f}ms")
    print(f"   Results: {len(trie_results)}")

    # Test Linear search
    print("\n3️⃣  Linear search ('test')...")
    start = time.time()
    linear_results = linear_search_autocomplete(words, "test", 10)
    linear_time = time.time() - start
    print(f"   Time: {linear_time*1000:.2f}ms")
    print(f"   Results: {len(linear_results)}")

    # Comparison
    print("\n" + "="*60)
    print("📊 RESULTS:")
    print("="*60)
    print(f"Trie:   {trie_time*1000:.2f}ms")
    print(f"Linear: {linear_time*1000:.2f}ms")
    print(f"\n🚀 Trie is {linear_time/trie_time:.0f}x FASTER!")


# ============================================
# REAL-WORLD EXAMPLE: PRODUCT SEARCH
# ============================================

class ProductSearch:
    """Sistema de busca de produtos com autocomplete"""

    def __init__(self):
        self.trie = Trie()
        self.products = {}  # product_name -> details

    def add_product(self, name: str, price: float, category: str, sales_count: int = 0):
        """
        Adiciona produto

        Use sales_count como frequência para ranking
        """
        # Insere na Trie com frequência baseada em vendas
        self.trie.insert(name, frequency=sales_count)

        # Salva detalhes
        self.products[name.lower()] = {
            "name": name,
            "price": price,
            "category": category,
            "sales": sales_count
        }

    def search(self, query: str, max_results: int = 5):
        """
        Busca produtos por nome

        Retorna produtos ordenados por popularidade (vendas)
        """
        # Autocomplete
        product_names = self.trie.autocomplete(query, max_results)

        # Busca detalhes
        results = []
        for name in product_names:
            details = self.products.get(name.lower())
            if details:
                results.append(details)

        return results


def demo_product_search():
    """Demo: Sistema de busca de produtos"""
    print("\n" + "="*60)
    print("🛒 DEMO: PRODUCT SEARCH")
    print("="*60)

    # Criar sistema
    search = ProductSearch()

    # Adicionar produtos
    products = [
        ("iPhone 15 Pro", 999.99, "Electronics", 5000),
        ("iPhone 15", 799.99, "Electronics", 8000),
        ("iPhone 14", 699.99, "Electronics", 3000),
        ("iPad Pro", 1099.99, "Electronics", 2000),
        ("iPad Air", 599.99, "Electronics", 2500),
        ("MacBook Pro", 1999.99, "Electronics", 1500),
        ("MacBook Air", 1299.99, "Electronics", 2000),
    ]

    print("\nAdding products...")
    for name, price, category, sales in products:
        search.add_product(name, price, category, sales)
    print(f"✅ Added {len(products)} products")

    # Buscar
    queries = ["ip", "iph", "ipad", "mac"]

    for query in queries:
        print(f"\n🔍 Search: '{query}'")
        results = search.search(query, max_results=3)

        if results:
            for r in results:
                print(f"  • {r['name']} - ${r['price']} ({r['sales']:,} sales)")
        else:
            print("  No results")


# ============================================
# VISUALIZE TRIE
# ============================================

def visualize_trie():
    """Visualiza estrutura da Trie"""
    print("\n" + "="*60)
    print("🌳 VISUALIZING TRIE STRUCTURE")
    print("="*60)

    trie = Trie()
    words = ["cat", "car", "card", "care", "careful", "can", "dog", "dodge"]

    print(f"\nInserting words: {', '.join(words)}")
    for word in words:
        trie.insert(word)

    print("\nTrie structure:")
    print("""
                    ROOT
                   /    \\
                  c      d
                 /        \\
                a          o
               /|\\         |
              t r n        g
               /|          |
              d e          e
             /
            l

    Words:
    - cat, can
    - car, card, care, careful
    - dog, dodge
    """)

    print("\nAutocomple 'ca':")
    results = trie.autocomplete("ca")
    for r in results:
        print(f"  • {r}")


# ============================================
# MAIN
# ============================================

def main():
    print("="*60)
    print("🌳 TRIE DATA STRUCTURE DEMO")
    print("="*60)
    print()
    print("Use case: Autocomplete / Prefix Search")
    print()
    print("Benefits:")
    print("  ✅ Fast prefix search: O(M) where M = prefix length")
    print("  ✅ Memory efficient (shared prefixes)")
    print("  ✅ Used by: Google, Amazon, IDEs, etc")
    print()

    # Demo 1: Visualize
    visualize_trie()

    input("\nPress ENTER to continue...")

    # Demo 2: Product Search
    demo_product_search()

    input("\nPress ENTER to continue...")

    # Demo 3: Performance
    compare_performance()

    print("\n" + "="*60)
    print("✅ SUMMARY")
    print("="*60)
    print()
    print("Trie is perfect for:")
    print("  • Autocomplete")
    print("  • Spell checker")
    print("  • IP routing (longest prefix match)")
    print("  • Dictionary lookups")
    print()
    print("Complexity:")
    print("  • Insert: O(M)")
    print("  • Search: O(M)")
    print("  • Prefix search: O(P + N)")
    print()
    print("Where:")
    print("  M = word length")
    print("  P = prefix length")
    print("  N = number of results")


if __name__ == "__main__":
    main()
