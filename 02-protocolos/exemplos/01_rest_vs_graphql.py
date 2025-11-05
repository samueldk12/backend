"""
Exemplo 01: REST vs GraphQL

Demonstra as diferenças entre REST e GraphQL com exemplos práticos.
Mostra problemas de over-fetching, under-fetching e como GraphQL resolve.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# ============================================================================
# MODELS
# ============================================================================

class User(BaseModel):
    id: int
    name: str
    email: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class Post(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    likes: int = 0
    views: int = 0

class Comment(BaseModel):
    id: int
    post_id: int
    user_id: int
    text: str

# ============================================================================
# MOCK DATABASE
# ============================================================================

USERS_DB = [
    User(id=1, name="João Silva", email="joao@example.com", bio="Developer", avatar_url="https://example.com/avatar1.jpg"),
    User(id=2, name="Maria Santos", email="maria@example.com", bio="Designer", avatar_url="https://example.com/avatar2.jpg"),
    User(id=3, name="Pedro Costa", email="pedro@example.com", bio="Product Manager", avatar_url="https://example.com/avatar3.jpg"),
]

POSTS_DB = [
    Post(id=1, user_id=1, title="Aprendendo FastAPI", content="FastAPI é incrível...", likes=150, views=1200),
    Post(id=2, user_id=1, title="Python Async", content="Async/await no Python...", likes=200, views=1500),
    Post(id=3, user_id=2, title="Design Systems", content="Como criar design systems...", likes=100, views=800),
]

COMMENTS_DB = [
    Comment(id=1, post_id=1, user_id=2, text="Ótimo post!"),
    Comment(id=2, post_id=1, user_id=3, text="Muito útil, obrigado!"),
    Comment(id=3, post_id=2, user_id=2, text="Excelente explicação."),
]

# ============================================================================
# REST API
# ============================================================================

rest_app = FastAPI(title="REST API Example")

@rest_app.get("/api/users")
def get_users() -> List[User]:
    """
    REST: Retorna TODOS os campos de TODOS os usuários.

    Problema: Over-fetching
    - Cliente pode precisar apenas de id e name
    - Mas recebe bio, avatar_url, email também
    - Desperdício de banda
    """
    return USERS_DB

@rest_app.get("/api/users/{user_id}")
def get_user(user_id: int) -> User:
    """REST: Buscar um usuário."""
    user = next((u for u in USERS_DB if u.id == user_id), None)
    if not user:
        raise HTTPException(404, "User not found")
    return user

@rest_app.get("/api/users/{user_id}/posts")
def get_user_posts(user_id: int) -> List[Post]:
    """
    REST: Buscar posts de um usuário.

    Problema: Under-fetching
    - Para mostrar posts com dados do autor, precisa:
      1. GET /api/users/{user_id}/posts
      2. Para cada post, GET /api/users/{user_id}
    - N+1 queries!
    """
    return [p for p in POSTS_DB if p.user_id == user_id]

@rest_app.get("/api/posts/{post_id}")
def get_post(post_id: int) -> Post:
    """REST: Buscar um post."""
    post = next((p for p in POSTS_DB if p.id == post_id), None)
    if not post:
        raise HTTPException(404, "Post not found")
    return post

@rest_app.get("/api/posts/{post_id}/comments")
def get_post_comments(post_id: int) -> List[Comment]:
    """REST: Buscar comentários de um post."""
    return [c for c in COMMENTS_DB if c.post_id == post_id]

# ============================================================================
# DEMONSTRAÇÃO DOS PROBLEMAS DO REST
# ============================================================================

def demonstrar_problemas_rest():
    """Mostra os problemas do REST."""
    print("\n" + "=" * 60)
    print("PROBLEMAS DO REST")
    print("=" * 60)

    print("\n1️⃣ OVER-FETCHING:")
    print("   Cenário: Listar usuários mostrando apenas nome")
    print("   REST: GET /api/users")
    print("   Retorna: id, name, email, bio, avatar_url")
    print("   Necessário: apenas name")
    print("   ❌ Desperdício de 80% dos dados!")

    print("\n2️⃣ UNDER-FETCHING (N+1 Problem):")
    print("   Cenário: Mostrar posts com autor e comentários")
    print("   REST precisa de múltiplas requests:")
    print("   1. GET /api/posts/1")
    print("   2. GET /api/users/1       (autor do post)")
    print("   3. GET /api/posts/1/comments")
    print("   4. GET /api/users/2       (autor do comentário 1)")
    print("   5. GET /api/users/3       (autor do comentário 2)")
    print("   ❌ 5 requests para uma página!")

    print("\n3️⃣ VERSIONAMENTO:")
    print("   Adicionar novo campo? Criar /api/v2/users")
    print("   ❌ Manter múltiplas versões da API")

# ============================================================================
# GraphQL (Simulado com FastAPI)
# ============================================================================

from typing import Dict, Any

graphql_app = FastAPI(title="GraphQL-style API")

class GraphQLQuery(BaseModel):
    query: str
    variables: Optional[Dict[str, Any]] = None

def parse_simple_query(query: str) -> Dict[str, Any]:
    """
    Parser simplificado de GraphQL (apenas para demonstração).
    Em produção, use Strawberry, Ariadne ou Graphene.
    """
    # Este é um parser MUITO simplificado apenas para demonstração
    result = {}

    if "users" in query:
        # Extrair campos solicitados
        if "id" in query:
            result["users"] = [{"id": u.id} for u in USERS_DB]
        elif "name" in query:
            if "email" in query:
                result["users"] = [{"id": u.id, "name": u.name, "email": u.email} for u in USERS_DB]
            else:
                result["users"] = [{"id": u.id, "name": u.name} for u in USERS_DB]
        else:
            result["users"] = [u.dict() for u in USERS_DB]

    return result

@graphql_app.post("/graphql")
def graphql_endpoint(query: GraphQLQuery):
    """
    GraphQL endpoint (simplificado).

    Vantagens:
    1. Cliente escolhe exatamente os campos que quer
    2. Uma única request pode buscar dados relacionados
    3. Sem over-fetching ou under-fetching
    """
    return parse_simple_query(query.query)

# ============================================================================
# COMPARAÇÃO PRÁTICA
# ============================================================================

def comparacao_pratica():
    """Comparação lado a lado."""
    print("\n" + "=" * 60)
    print("COMPARAÇÃO: REST vs GraphQL")
    print("=" * 60)

    print("\n📝 CENÁRIO 1: Listar apenas nomes de usuários")
    print("-" * 60)

    print("\n🔴 REST:")
    print("""
    GET /api/users

    Retorna:
    [
      {
        "id": 1,
        "name": "João Silva",
        "email": "joao@example.com",        ← Não precisa
        "bio": "Developer",                 ← Não precisa
        "avatar_url": "https://..."         ← Não precisa
      },
      ...
    ]

    Tamanho: ~500 bytes
    """)

    print("\n🟢 GraphQL:")
    print("""
    POST /graphql
    {
      query {
        users {
          name
        }
      }
    }

    Retorna:
    {
      "data": {
        "users": [
          { "name": "João Silva" },
          { "name": "Maria Santos" },
          { "name": "Pedro Costa" }
        ]
      }
    }

    Tamanho: ~100 bytes (80% menor!)
    """)

    print("\n" + "=" * 60)
    print("\n📝 CENÁRIO 2: Post com autor e comentários")
    print("-" * 60)

    print("\n🔴 REST (5 requests):")
    print("""
    1. GET /api/posts/1
       → { id, title, content, user_id: 1, ... }

    2. GET /api/users/1
       → { id, name, email, ... }

    3. GET /api/posts/1/comments
       → [{ id, text, user_id: 2 }, { id, text, user_id: 3 }]

    4. GET /api/users/2  (autor do comentário 1)
    5. GET /api/users/3  (autor do comentário 2)

    Total: 5 requests HTTP
    Latência: 5 × 50ms = 250ms
    """)

    print("\n🟢 GraphQL (1 request):")
    print("""
    POST /graphql
    {
      query {
        post(id: 1) {
          title
          content
          author {
            name
            avatar_url
          }
          comments {
            text
            author {
              name
            }
          }
        }
      }
    }

    Retorna tudo em uma resposta:
    {
      "data": {
        "post": {
          "title": "Aprendendo FastAPI",
          "content": "FastAPI é incrível...",
          "author": {
            "name": "João Silva",
            "avatar_url": "https://..."
          },
          "comments": [
            {
              "text": "Ótimo post!",
              "author": { "name": "Maria Santos" }
            },
            {
              "text": "Muito útil!",
              "author": { "name": "Pedro Costa" }
            }
          ]
        }
      }
    }

    Total: 1 request HTTP
    Latência: 50ms (5x mais rápido!)
    """)

# ============================================================================
# QUANDO USAR CADA UM
# ============================================================================

def quando_usar():
    """Guia de decisão."""
    print("\n" + "=" * 60)
    print("QUANDO USAR CADA UM?")
    print("=" * 60)

    print("""
┌─────────────────────────────────────────────────────────────┐
│                        REST                                 │
├─────────────────────────────────────────────────────────────┤
│ ✅ Quando usar:                                             │
│   • API pública simples                                     │
│   • CRUD tradicional                                        │
│   • Caching importante (HTTP cache funciona bem)           │
│   • Time pequeno ou projeto simples                        │
│   • Endpoints bem definidos                                │
│                                                             │
│ ❌ Evitar quando:                                           │
│   • Muitas entidades relacionadas                          │
│   • Clientes diferentes precisam de dados diferentes       │
│   • Over-fetching causando problemas de performance        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      GraphQL                                │
├─────────────────────────────────────────────────────────────┤
│ ✅ Quando usar:                                             │
│   • Frontend complexo com muitos componentes               │
│   • Múltiplos clientes (web, mobile, etc)                 │
│   • Dados altamente relacionados (grafo)                   │
│   • Over-fetching é problema                               │
│   • Mudanças frequentes no frontend                        │
│                                                             │
│ ❌ Evitar quando:                                           │
│   • API pública simples                                    │
│   • Operações simples de CRUD                              │
│   • Caching HTTP é importante                              │
│   • Time não tem experiência com GraphQL                   │
│   • Upload de arquivos (GraphQL não é ideal)              │
└─────────────────────────────────────────────────────────────┘

📊 PERFORMANCE:

Cenário                    | REST      | GraphQL   | Vencedor
──────────────────────────|─────────--|───────────|─────────
Lista simples             | 50ms      | 52ms      | Empate
Lista com relacionamentos | 250ms (5x)| 50ms (1x) | GraphQL
Dados específicos         | 200KB     | 20KB      | GraphQL
Caching                   | Fácil     | Complexo  | REST
Upload de arquivos        | Simples   | Complexo  | REST

💡 RECOMENDAÇÃO:

1. Começar com REST → Simples e eficaz para maioria dos casos
2. Migrar para GraphQL → Quando complexidade justificar
3. Híbrido → REST para CRUD, GraphQL para queries complexas

Empresas que usam GraphQL:
• Facebook (criou o GraphQL)
• GitHub
• Shopify
• Twitter
• Netflix
    """)

# ============================================================================
# IMPLEMENTAÇÃO REAL COM STRAWBERRY (GraphQL)
# ============================================================================

def exemplo_strawberry():
    """Mostra como implementar GraphQL real."""
    print("\n" + "=" * 60)
    print("IMPLEMENTAÇÃO REAL: Strawberry GraphQL")
    print("=" * 60)

    print("""
Para usar GraphQL de verdade em Python, use Strawberry:

```python
# pip install strawberry-graphql[fastapi]

import strawberry
from typing import List

@strawberry.type
class User:
    id: int
    name: str
    email: str

@strawberry.type
class Post:
    id: int
    title: str
    content: str

    @strawberry.field
    def author(self) -> User:
        # Resolver para buscar autor
        return get_user_by_id(self.user_id)

    @strawberry.field
    def comments(self) -> List['Comment']:
        # Resolver para buscar comentários
        return get_comments_by_post_id(self.id)

@strawberry.type
class Query:
    @strawberry.field
    def users(self) -> List[User]:
        return get_all_users()

    @strawberry.field
    def post(self, id: int) -> Post:
        return get_post_by_id(id)

# Criar schema
schema = strawberry.Schema(query=Query)

# Integrar com FastAPI
from strawberry.fastapi import GraphQLRouter

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
```

Query no frontend:
```graphql
query GetPost($postId: Int!) {
  post(id: $postId) {
    title
    content
    author {
      name
      avatar_url
    }
    comments {
      text
      author {
        name
      }
    }
  }
}
```

Vantagens do Strawberry:
✅ Type hints nativos do Python
✅ Integração perfeita com FastAPI
✅ DataLoaders (resolve N+1 automaticamente)
✅ Subscriptions (WebSocket)
✅ Ferramentas de desenvolvimento (GraphiQL)
    """)

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("REST vs GraphQL - Comparação Prática")
    print("=" * 60)

    demonstrar_problemas_rest()
    comparacao_pratica()
    quando_usar()
    exemplo_strawberry()

    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    print("""
✅ REST:
   • Simples e eficaz para CRUD
   • Caching fácil
   • Amplamente conhecido
   • Melhor para APIs públicas simples

✅ GraphQL:
   • Cliente controla dados
   • Uma request para dados complexos
   • Evolução da API sem versioning
   • Melhor para frontends complexos

🎯 ESCOLHA:
   • MVP/Startup → REST
   • App complexo → GraphQL
   • API pública → REST
   • Dashboard com muitos dados → GraphQL

Para rodar exemplos:
1. pip install fastapi uvicorn strawberry-graphql
2. python 01_rest_vs_graphql.py
3. Acesse http://localhost:8000/docs (REST)
4. Acesse http://localhost:8001/docs (GraphQL-style)
    """)

    print("\n💡 Para testar as APIs:")
    print("   uvicorn 01_rest_vs_graphql:rest_app --port 8000")
    print("   uvicorn 01_rest_vs_graphql:graphql_app --port 8001")


if __name__ == "__main__":
    main()
