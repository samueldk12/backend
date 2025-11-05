"""
Exemplo 2: Árvores e Grafos em Backend

Demonstra aplicações práticas de trees e graphs em sistemas reais
"""

from collections import defaultdict, deque
from typing import List, Optional, Set, Dict
import json


# =====================================
# ÁRVORE: Categorias Hierárquicas
# =====================================

class Category:
    """Categoria com hierarquia (N-ary tree)"""

    def __init__(self, id: int, name: str, parent_id: Optional[int] = None):
        self.id = id
        self.name = name
        self.parent_id = parent_id
        self.children: List['Category'] = []

    def __repr__(self):
        return f"Category({self.id}, '{self.name}')"


def build_category_tree(categories: List[Category]) -> List[Category]:
    """
    Construir árvore de categorias

    Input: Lista flat de categorias
    Output: Árvore hierárquica (apenas roots)

    Complexidade: O(n) com hash table
    """
    # Hash table para lookup rápido
    category_map = {cat.id: cat for cat in categories}

    root_categories = []

    for category in categories:
        if category.parent_id is None:
            # Root category
            root_categories.append(category)
        else:
            # Adicionar como filho do pai
            parent = category_map.get(category.parent_id)
            if parent:
                parent.children.append(category)

    return root_categories


def print_category_tree(category: Category, depth: int = 0):
    """
    Imprimir árvore (DFS pré-order)

    Output:
    Eletrônicos
      ├── Computadores
      │   ├── Notebooks
      │   └── Desktops
      └── Celulares
    """
    indent = "  " * depth
    prefix = "├── " if depth > 0 else ""
    print(f"{indent}{prefix}{category.name}")

    for child in category.children:
        print_category_tree(child, depth + 1)


def get_all_descendants(category: Category) -> List[Category]:
    """
    Buscar todos descendentes (DFS)

    Útil para: "Buscar todos produtos em Eletrônicos (incluindo subcategorias)"

    Complexidade: O(n) onde n = descendentes
    """
    descendants = []

    def dfs(cat: Category):
        descendants.append(cat)
        for child in cat.children:
            dfs(child)

    dfs(category)
    return descendants


def get_path_to_root(category: Category, category_map: Dict) -> List[str]:
    """
    Buscar caminho até raiz (breadcrumb)

    Exemplo: Notebooks → Computadores → Eletrônicos → Home

    Complexidade: O(h) onde h = altura da árvore
    """
    path = []
    current = category

    while current:
        path.append(current.name)
        if current.parent_id:
            current = category_map.get(current.parent_id)
        else:
            break

    path.reverse()
    return path


# =====================================
# ÁRVORE: Comments Tree (Nested Comments)
# =====================================

class Comment:
    """Comentário com replies (Reddit-style)"""

    def __init__(self, id: int, content: str, author: str, parent_id: Optional[int] = None):
        self.id = id
        self.content = content
        self.author = author
        self.parent_id = parent_id
        self.replies: List['Comment'] = []

    def to_dict(self):
        """Serializar para JSON"""
        return {
            "id": self.id,
            "content": self.content,
            "author": self.author,
            "replies": [reply.to_dict() for reply in self.replies]
        }


def build_comment_tree(comments: List[Comment]) -> List[Comment]:
    """
    Construir árvore de comentários

    Mesmo algoritmo de categorias!
    """
    comment_map = {c.id: c for c in comments}
    root_comments = []

    for comment in comments:
        if comment.parent_id is None:
            root_comments.append(comment)
        else:
            parent = comment_map.get(comment.parent_id)
            if parent:
                parent.replies.append(comment)

    return root_comments


def count_total_replies(comment: Comment) -> int:
    """
    Contar total de replies (recursivo - DFS)

    Exemplo: Comment com 2 replies, cada uma com 1 reply = 4 total
    """
    count = len(comment.replies)

    for reply in comment.replies:
        count += count_total_replies(reply)

    return count


# =====================================
# GRAFO: Social Network
# =====================================

class SocialGraph:
    """
    Grafo de seguidores (directed graph)

    Estrutura: Adjacency list (hash table de sets)
    """

    def __init__(self):
        self.followers: Dict[int, Set[int]] = defaultdict(set)  # user_id -> {follower_ids}
        self.following: Dict[int, Set[int]] = defaultdict(set)  # user_id -> {following_ids}

    def follow(self, follower_id: int, followee_id: int):
        """
        User A seguir User B

        Complexidade: O(1)
        """
        self.following[follower_id].add(followee_id)
        self.followers[followee_id].add(follower_id)

    def unfollow(self, follower_id: int, followee_id: int):
        """Complexidade: O(1)"""
        self.following[follower_id].discard(followee_id)
        self.followers[followee_id].discard(follower_id)

    def get_followers(self, user_id: int) -> Set[int]:
        """Retornar quem segue o user - O(1)"""
        return self.followers[user_id]

    def get_following(self, user_id: int) -> Set[int]:
        """Retornar quem o user segue - O(1)"""
        return self.following[user_id]

    def get_mutual_friends(self, user_a: int, user_b: int) -> Set[int]:
        """
        Amigos em comum (interseção de sets)

        Complexidade: O(min(|A|, |B|))
        """
        following_a = self.following[user_a]
        following_b = self.following[user_b]

        return following_a & following_b  # Set intersection

    def get_friend_suggestions(self, user_id: int, limit: int = 10) -> List[tuple]:
        """
        Sugestões de amizade (2-hop neighbors)

        Algoritmo:
        1. Pegar amigos dos meus amigos (2-hop BFS)
        2. Remover: eu mesmo, quem já sigo
        3. Ordenar por # de amigos em comum

        Complexidade: O(friends * friends_of_friends)
        """
        from collections import Counter

        following = self.following[user_id]
        friend_suggestions = Counter()

        # Friends of friends (2-hop)
        for friend_id in following:
            friends_of_friend = self.following[friend_id]

            for candidate in friends_of_friend:
                # Pular: eu mesmo, quem já sigo
                if candidate == user_id or candidate in following:
                    continue

                friend_suggestions[candidate] += 1  # Contar amigos em comum

        # Retornar top N por amigos em comum
        return friend_suggestions.most_common(limit)


def shortest_path_bfs(graph: SocialGraph, start: int, end: int) -> List[int]:
    """
    Caminho mais curto entre dois users (degrees of separation)

    BFS garante caminho mais curto em grafo não-ponderado

    Exemplo: Alice → Bob → Charlie → David (3 degrees)

    Complexidade: O(V + E) onde V=users, E=connections
    """
    if start == end:
        return [start]

    visited = {start}
    queue = deque([(start, [start])])  # (node, path)

    while queue:
        current, path = queue.popleft()

        # Explorar vizinhos (quem o user segue)
        for neighbor in graph.following[current]:
            if neighbor in visited:
                continue

            new_path = path + [neighbor]

            if neighbor == end:
                return new_path  # Encontrou!

            visited.add(neighbor)
            queue.append((neighbor, new_path))

    return []  # Não há caminho


# =====================================
# EXEMPLOS PRÁTICOS
# =====================================

def example_category_tree():
    """Exemplo: E-commerce categories"""
    print("\n" + "="*60)
    print("EXEMPLO: Árvore de Categorias (E-commerce)")
    print("="*60)

    # Criar categorias
    categories = [
        Category(1, "Eletrônicos"),
        Category(2, "Computadores", parent_id=1),
        Category(3, "Notebooks", parent_id=2),
        Category(4, "Desktops", parent_id=2),
        Category(5, "Celulares", parent_id=1),
        Category(6, "iPhone", parent_id=5),
        Category(7, "Android", parent_id=5),
        Category(8, "Moda"),
        Category(9, "Roupas", parent_id=8),
        Category(10, "Calçados", parent_id=8),
    ]

    # Construir árvore
    roots = build_category_tree(categories)

    print("\nÁrvore de Categorias:")
    for root in roots:
        print_category_tree(root)

    # Buscar todos descendentes de "Eletrônicos"
    eletronicos = categories[0]  # Eletrônicos
    descendants = get_all_descendants(eletronicos)

    print(f"\n✅ Todas subcategorias de '{eletronicos.name}':")
    for cat in descendants:
        print(f"  - {cat.name}")

    # Breadcrumb (caminho até raiz)
    category_map = {cat.id: cat for cat in categories}
    iphone = categories[5]  # iPhone
    path = get_path_to_root(iphone, category_map)

    print(f"\n✅ Breadcrumb para '{iphone.name}':")
    print(" > ".join(path))


def example_comment_tree():
    """Exemplo: Nested comments (Reddit-style)"""
    print("\n" + "="*60)
    print("EXEMPLO: Árvore de Comentários (Reddit)")
    print("="*60)

    comments = [
        Comment(1, "Great post!", "Alice"),
        Comment(2, "Thanks Alice!", "Bob", parent_id=1),
        Comment(3, "I agree!", "Charlie", parent_id=1),
        Comment(4, "Me too!", "David", parent_id=3),
        Comment(5, "Interesting point", "Eve"),
        Comment(6, "Can you elaborate?", "Frank", parent_id=5),
    ]

    # Construir árvore
    root_comments = build_comment_tree(comments)

    print("\nComentários (estrutura de árvore):")
    print(json.dumps([c.to_dict() for c in root_comments], indent=2))

    # Contar total de replies
    first_comment = root_comments[0]
    total_replies = count_total_replies(first_comment)

    print(f"\n✅ Comentário 1 ('{first_comment.content}') tem {total_replies} replies totais")


def example_social_graph():
    """Exemplo: Social network graph"""
    print("\n" + "="*60)
    print("EXEMPLO: Grafo Social (Twitter-style)")
    print("="*60)

    # Construir grafo
    graph = SocialGraph()

    # Usuários (para display)
    users = {
        1: "Alice",
        2: "Bob",
        3: "Charlie",
        4: "David",
        5: "Eve",
        6: "Frank"
    }

    # Follows (directed edges)
    follows = [
        (1, 2),  # Alice → Bob
        (1, 3),  # Alice → Charlie
        (2, 3),  # Bob → Charlie
        (2, 4),  # Bob → David
        (3, 4),  # Charlie → David
        (3, 5),  # Charlie → Eve
        (4, 5),  # David → Eve
        (5, 6),  # Eve → Frank
    ]

    for follower, followee in follows:
        graph.follow(follower, followee)

    # Followers de Charlie
    charlie_followers = graph.get_followers(3)
    print(f"\n✅ Followers de Charlie:")
    for user_id in charlie_followers:
        print(f"  - {users[user_id]}")

    # Amigos em comum entre Alice e Bob
    mutual = graph.get_mutual_friends(1, 2)
    print(f"\n✅ Amigos em comum entre Alice e Bob:")
    for user_id in mutual:
        print(f"  - {users[user_id]}")

    # Sugestões de amizade para Alice
    suggestions = graph.get_friend_suggestions(1, limit=3)
    print(f"\n✅ Sugestões de amizade para Alice:")
    for user_id, common_friends in suggestions:
        print(f"  - {users[user_id]} ({common_friends} amigos em comum)")

    # Degrees of separation (Alice → Eve)
    path = shortest_path_bfs(graph, start=1, end=5)
    print(f"\n✅ Degrees of separation (Alice → Eve):")
    path_names = [users[uid] for uid in path]
    print(f"  {' → '.join(path_names)} ({len(path)-1} degrees)")


# =====================================
# MAIN
# =====================================

if __name__ == "__main__":
    print("\n🌲 TREES & GRAPHS IN BACKEND\n")
    print("Demonstração de aplicações práticas de árvores e grafos")

    # Exemplos
    example_category_tree()
    example_comment_tree()
    example_social_graph()

    print("\n" + "="*60)
    print("✅ CONCLUSÃO")
    print("="*60)
    print("""
ÁRVORES:
- Categorias hierárquicas (e-commerce)
- Nested comments (Reddit, YouTube)
- Org charts, file systems
- DFS/BFS para traversal

GRAFOS:
- Social networks (followers, friends)
- Recomendações (2-hop neighbors)
- Shortest path (degrees of separation)
- Adjacency list com hash tables

APLICAÇÕES REAIS:
- Amazon: Árvore de categorias
- Reddit: Árvore de comments
- Twitter: Grafo de followers
- LinkedIn: Friend suggestions (2-hop)
    """)
