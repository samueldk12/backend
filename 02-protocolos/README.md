# 02 - Protocolos de Comunicação

## Índice

1. [REST API](#rest-api)
2. [GraphQL](#graphql)
3. [gRPC](#grpc)
4. [WebSocket](#websocket)
5. [Quando Usar Cada Um](#quando-usar-cada-um)

---

## REST API

### Princípios REST

**REST (Representational State Transfer)** - Arquitetura stateless baseada em HTTP.

**Constraints:**
1. **Client-Server**: Separação de responsabilidades
2. **Stateless**: Cada request tem toda info necessária
3. **Cacheable**: Responses devem indicar se são cacheáveis
4. **Uniform Interface**: URIs padronizadas
5. **Layered System**: Cliente não sabe se fala direto com servidor

### HTTP Methods

```python
# GET - Buscar recursos (idempotente)
GET /api/users/123

# POST - Criar recurso (não-idempotente)
POST /api/users
{
    "name": "João",
    "email": "joao@example.com"
}

# PUT - Substituir recurso completo (idempotente)
PUT /api/users/123
{
    "name": "João Silva",
    "email": "joao@example.com",
    "age": 30
}

# PATCH - Atualizar parcialmente (idempotente)
PATCH /api/users/123
{
    "age": 31
}

# DELETE - Remover recurso (idempotente)
DELETE /api/users/123
```

### Status Codes

```
2xx - Sucesso
├── 200 OK (GET, PUT, PATCH)
├── 201 Created (POST)
└── 204 No Content (DELETE)

4xx - Erro do Cliente
├── 400 Bad Request (dados inválidos)
├── 401 Unauthorized (não autenticado)
├── 403 Forbidden (não autorizado)
├── 404 Not Found (recurso não existe)
└── 429 Too Many Requests (rate limit)

5xx - Erro do Servidor
├── 500 Internal Server Error
├── 502 Bad Gateway
└── 503 Service Unavailable
```

### REST com FastAPI

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    name: str
    email: str

users_db = {}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]

@app.post("/users", status_code=201)
def create_user(user: User):
    user_id = len(users_db) + 1
    users_db[user_id] = user.dict()
    return {"id": user_id, **user.dict()}

@app.put("/users/{user_id}")
def update_user(user_id: int, user: User):
    if user_id not in users_db:
        raise HTTPException(status_code=404)
    users_db[user_id] = user.dict()
    return users_db[user_id]

@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    if user_id not in users_db:
        raise HTTPException(status_code=404)
    del users_db[user_id]
```

---

## GraphQL

### O que é GraphQL?

Query language que permite cliente pedir EXATAMENTE o que precisa.

**Problemas que resolve:**
- **Over-fetching**: REST retorna dados desnecessários
- **Under-fetching**: Precisa de múltiplas requests (N+1)
- **Versionamento**: Sem `/v1`, `/v2` - schema evolui

### Exemplo GraphQL

```python
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class User:
    id: int
    name: str
    email: str
    posts: list['Post']

@strawberry.type
class Post:
    id: int
    title: str
    content: str

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: int) -> User:
        # Cliente pede apenas o que precisa:
        # query {
        #   user(id: 1) {
        #     name
        #     posts { title }
        #   }
        # }
        return get_user_from_db(id)

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")
```

**Query do cliente:**
```graphql
query {
  user(id: 1) {
    name          # Apenas name, não email
    posts {
      title       # Apenas title, não content
    }
  }
}
```

**Response:**
```json
{
  "data": {
    "user": {
      "name": "João",
      "posts": [
        {"title": "Post 1"},
        {"title": "Post 2"}
      ]
    }
  }
}
```

---

## gRPC

### O que é gRPC?

Framework RPC (Remote Procedure Call) da Google usando Protocol Buffers.

**Vantagens:**
- **Binário**: 7x menor que JSON
- **HTTP/2**: Multiplexing, streaming
- **Type-Safe**: Schema em `.proto`
- **Streaming**: Bidirecional

### Protocol Buffer

```protobuf
// user.proto
syntax = "proto3";

service UserService {
  rpc GetUser (UserRequest) returns (UserResponse);
  rpc ListUsers (Empty) returns (stream UserResponse);
}

message UserRequest {
  int32 id = 1;
}

message UserResponse {
  int32 id = 1;
  string name = 2;
  string email = 3;
}

message Empty {}
```

### Server gRPC (Python)

```python
import grpc
from concurrent import futures
import user_pb2
import user_pb2_grpc

class UserService(user_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        # request.id = ID do usuário
        user = get_user_from_db(request.id)
        return user_pb2.UserResponse(
            id=user.id,
            name=user.name,
            email=user.email
        )

    def ListUsers(self, request, context):
        # Streaming: envia usuários um por um
        for user in get_all_users():
            yield user_pb2.UserResponse(
                id=user.id,
                name=user.name,
                email=user.email
            )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()
```

### Client gRPC

```python
import grpc
import user_pb2
import user_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = user_pb2_grpc.UserServiceStub(channel)

# Unary call
user = stub.GetUser(user_pb2.UserRequest(id=1))
print(f"User: {user.name}")

# Streaming call
for user in stub.ListUsers(user_pb2.Empty()):
    print(f"User: {user.name}")
```

---

## WebSocket

### O que é WebSocket?

Protocolo full-duplex para comunicação bidirecional em tempo real.

**Diferença do HTTP:**
- HTTP: Cliente pergunta → Servidor responde (request/response)
- WebSocket: Conexão persistente, ambos enviam quando quiserem

### Server WebSocket (FastAPI)

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket)
    try:
        while True:
            # Recebe mensagem do cliente
            data = await websocket.receive_text()

            # Broadcast para todos
            await manager.broadcast(f"User {user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"User {user_id} left")
```

### Client WebSocket (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/123');

// Evento: Conexão aberta
ws.onopen = () => {
    console.log('Connected');
    ws.send('Hello Server!');
};

// Evento: Mensagem recebida
ws.onmessage = (event) => {
    console.log('Received:', event.data);
};

// Evento: Conexão fechada
ws.onclose = () => {
    console.log('Disconnected');
};

// Enviar mensagem
ws.send('Nova mensagem');
```

---

## Quando Usar Cada Um

### Decision Tree

```
Sua aplicação precisa de...

┌─ Comunicação em tempo real? (chat, notificações)
│  └─ SIM → WebSocket
│
├─ Múltiplos clientes com necessidades diferentes? (mobile, web, parceiros)
│  └─ SIM → GraphQL
│
├─ Alta performance entre microservices?
│  └─ SIM → gRPC
│
└─ API pública simples?
   └─ SIM → REST
```

### Comparação

| Critério | REST | GraphQL | gRPC | WebSocket |
|----------|------|---------|------|-----------|
| **Performance** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Simplicidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Browser Support** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Real-time** | ❌ | ❌ | ✅ | ✅ |
| **Streaming** | ❌ | ❌ | ✅ | ✅ |
| **Type Safety** | ❌ | ✅ | ✅ | ❌ |

### Casos de Uso

**REST:**
- ✅ APIs públicas (Twitter API, Stripe API)
- ✅ CRUD simples
- ✅ Caching com HTTP headers

**GraphQL:**
- ✅ Apps mobile (economizar dados)
- ✅ Dashboards (cada widget pede o que precisa)
- ✅ Quando tem muitos tipos de clientes

**gRPC:**
- ✅ Comunicação entre microservices
- ✅ Streaming de dados (logs, métricas)
- ✅ Alta performance crítica

**WebSocket:**
- ✅ Chat em tempo real
- ✅ Notificações push
- ✅ Live updates (dashboard, trading)
- ✅ Multiplayer games

---

## Exemplo Real: Chat

### REST (Polling - ❌ ineficiente)
```python
# Cliente faz request a cada 1s
@app.get("/messages/new")
def get_new_messages(since: datetime):
    return db.query(Message).filter(Message.created_at > since).all()

# Problema: 99% das requests retornam vazio
# 1000 usuários = 1000 req/s no servidor (waste!)
```

### WebSocket (Real-time - ✅)
```python
@app.websocket("/chat")
async def chat(websocket: WebSocket):
    await manager.connect(websocket)
    while True:
        message = await websocket.receive_text()
        await manager.broadcast(message)

# Problema resolvido: servidor PUSH quando há mensagem
# 1000 usuários = 1000 conexões persistentes
```

---

## Próximo Módulo

➡️ [03 - Banco de Dados](../03-banco-dados/README.md)
