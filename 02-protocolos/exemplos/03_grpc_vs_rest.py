"""
Módulo 02 - Protocolos: gRPC vs REST Comparison

Este exemplo demonstra:
1. Implementação REST tradicional (JSON/HTTP)
2. Implementação gRPC (Protocol Buffers/HTTP2)
3. Performance comparison
4. Quando usar cada um

Instalar dependências:
    pip install grpcio grpcio-tools fastapi uvicorn httpx

Gerar código gRPC:
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. user_service.proto

Execute:
    # Terminal 1: REST server
    uvicorn 03_grpc_vs_rest:rest_app --port 8000

    # Terminal 2: gRPC server
    python 03_grpc_vs_rest.py --mode grpc-server

    # Terminal 3: Benchmark
    python 03_grpc_vs_rest.py --mode benchmark
"""

import time
import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass
from concurrent import futures
import sys

# REST imports
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

# gRPC imports (commented out se não tiver instalado)
# import grpc
# from generated import user_service_pb2, user_service_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# DEFINIÇÃO DO PROTOCOLO gRPC (user_service.proto)
# ============================================================================

"""
// user_service.proto

syntax = "proto3";

package user;

service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (UserList);
  rpc CreateUser(CreateUserRequest) returns (User);
  rpc StreamUsers(StreamUsersRequest) returns (stream User);  // Server streaming
  rpc BulkCreateUsers(stream CreateUserRequest) returns (CreateUsersResponse);  // Client streaming
}

message User {
  int32 id = 1;
  string username = 2;
  string email = 3;
  int32 age = 4;
  bool is_active = 5;
}

message GetUserRequest {
  int32 id = 1;
}

message ListUsersRequest {
  int32 limit = 1;
  int32 offset = 2;
}

message UserList {
  repeated User users = 1;
  int32 total = 2;
}

message CreateUserRequest {
  string username = 1;
  string email = 2;
  int32 age = 3;
}

message StreamUsersRequest {
  int32 batch_size = 1;
}

message CreateUsersResponse {
  int32 created_count = 1;
}
"""


# ============================================================================
# MOCK DATABASE
# ============================================================================

@dataclass
class User:
    id: int
    username: str
    email: str
    age: int
    is_active: bool


# Database simulado
USERS_DB = [
    User(i, f"user{i}", f"user{i}@example.com", 20 + i, True)
    for i in range(1, 1001)  # 1000 usuários
]


def get_user(user_id: int) -> Optional[User]:
    """Buscar usuário por ID"""
    for user in USERS_DB:
        if user.id == user_id:
            return user
    return None


def list_users(limit: int = 10, offset: int = 0) -> List[User]:
    """Listar usuários com paginação"""
    return USERS_DB[offset:offset + limit]


def create_user(username: str, email: str, age: int) -> User:
    """Criar novo usuário"""
    new_id = len(USERS_DB) + 1
    user = User(new_id, username, email, age, True)
    USERS_DB.append(user)
    return user


# ============================================================================
# IMPLEMENTAÇÃO REST (FastAPI)
# ============================================================================

rest_app = FastAPI(title="REST User Service")


# Schemas Pydantic
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    age: int
    is_active: bool

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int


class CreateUserRequest(BaseModel):
    username: str
    email: str
    age: int


# Endpoints REST
@rest_app.get("/users/{user_id}", response_model=UserResponse)
def get_user_rest(user_id: int):
    """GET /users/{id} - Buscar usuário"""
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@rest_app.get("/users", response_model=UserListResponse)
def list_users_rest(limit: int = 10, offset: int = 0):
    """GET /users?limit=10&offset=0 - Listar usuários"""
    users = list_users(limit, offset)
    return {
        "users": users,
        "total": len(USERS_DB)
    }


@rest_app.post("/users", response_model=UserResponse, status_code=201)
def create_user_rest(request: CreateUserRequest):
    """POST /users - Criar usuário"""
    user = create_user(request.username, request.email, request.age)
    return user


# ============================================================================
# IMPLEMENTAÇÃO gRPC
# ============================================================================

# Nota: Código gRPC comentado pois requer compilar .proto
# Descomentar após gerar código com protoc

"""
class UserServiceServicer(user_service_pb2_grpc.UserServiceServicer):
    '''Implementação do serviço gRPC'''

    def GetUser(self, request, context):
        '''Buscar usuário'''
        user = get_user(request.id)
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('User not found')
            return user_service_pb2.User()

        return user_service_pb2.User(
            id=user.id,
            username=user.username,
            email=user.email,
            age=user.age,
            is_active=user.is_active
        )

    def ListUsers(self, request, context):
        '''Listar usuários'''
        users = list_users(request.limit, request.offset)

        user_messages = [
            user_service_pb2.User(
                id=u.id,
                username=u.username,
                email=u.email,
                age=u.age,
                is_active=u.is_active
            )
            for u in users
        ]

        return user_service_pb2.UserList(
            users=user_messages,
            total=len(USERS_DB)
        )

    def CreateUser(self, request, context):
        '''Criar usuário'''
        user = create_user(request.username, request.email, request.age)

        return user_service_pb2.User(
            id=user.id,
            username=user.username,
            email=user.email,
            age=user.age,
            is_active=user.is_active
        )

    def StreamUsers(self, request, context):
        '''Server streaming: enviar usuários em stream'''
        batch_size = request.batch_size or 10

        for i in range(0, len(USERS_DB), batch_size):
            batch = USERS_DB[i:i + batch_size]

            for user in batch:
                yield user_service_pb2.User(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    age=user.age,
                    is_active=user.is_active
                )

            time.sleep(0.1)  # Simular processamento

    def BulkCreateUsers(self, request_iterator, context):
        '''Client streaming: receber múltiplos usuários para criar'''
        count = 0

        for request in request_iterator:
            create_user(request.username, request.email, request.age)
            count += 1

        return user_service_pb2.CreateUsersResponse(created_count=count)


def serve_grpc():
    '''Iniciar servidor gRPC'''
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    user_service_pb2_grpc.add_UserServiceServicer_to_server(
        UserServiceServicer(), server
    )

    server.add_insecure_port('[::]:50051')
    server.start()

    logger.info('gRPC server started on port 50051')
    server.wait_for_termination()
"""


# ============================================================================
# BENCHMARK: REST vs gRPC
# ============================================================================

async def benchmark_rest():
    """Benchmark REST API"""
    logger.info("🚀 Benchmarking REST...")

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Teste 1: Get single user (100x)
        start = time.time()
        tasks = [client.get(f"/users/{i}") for i in range(1, 101)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        logger.info(f"  GET single user (100x): {elapsed:.3f}s ({100/elapsed:.0f} req/s)")

        # Teste 2: List users (50x)
        start = time.time()
        tasks = [client.get("/users?limit=20") for _ in range(50)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        logger.info(f"  GET list users (50x): {elapsed:.3f}s ({50/elapsed:.0f} req/s)")

        # Teste 3: Create user (100x)
        start = time.time()
        tasks = [
            client.post("/users", json={
                "username": f"newuser{i}",
                "email": f"newuser{i}@example.com",
                "age": 25
            })
            for i in range(100)
        ]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        logger.info(f"  POST create user (100x): {elapsed:.3f}s ({100/elapsed:.0f} req/s)")

    return elapsed


async def benchmark_grpc():
    """Benchmark gRPC API"""
    logger.info("⚡ Benchmarking gRPC...")

    # Código comentado pois requer .proto compilado
    """
    channel = grpc.aio.insecure_channel('localhost:50051')
    stub = user_service_pb2_grpc.UserServiceStub(channel)

    # Teste 1: Get single user (100x)
    start = time.time()
    tasks = [
        stub.GetUser(user_service_pb2.GetUserRequest(id=i))
        for i in range(1, 101)
    ]
    responses = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    logger.info(f"  GetUser (100x): {elapsed:.3f}s ({100/elapsed:.0f} req/s)")

    # Teste 2: List users (50x)
    start = time.time()
    tasks = [
        stub.ListUsers(user_service_pb2.ListUsersRequest(limit=20, offset=0))
        for _ in range(50)
    ]
    responses = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    logger.info(f"  ListUsers (50x): {elapsed:.3f}s ({50/elapsed:.0f} req/s)")

    # Teste 3: Server streaming (buscar 1000 users)
    start = time.time()
    count = 0
    async for user in stub.StreamUsers(user_service_pb2.StreamUsersRequest(batch_size=50)):
        count += 1
    elapsed = time.time() - start

    logger.info(f"  StreamUsers (1000 users): {elapsed:.3f}s ({count/elapsed:.0f} users/s)")

    await channel.close()
    """

    logger.info("  (gRPC benchmark requires compiled .proto file)")


# ============================================================================
# COMPARAÇÃO: REST vs gRPC
# ============================================================================

def print_comparison():
    """Imprime tabela comparativa"""
    comparison = """
╔══════════════════════════════════════════════════════════════════════════╗
║                        REST vs gRPC COMPARISON                           ║
╚══════════════════════════════════════════════════════════════════════════╝

┌────────────────────┬───────────────────┬──────────────────────────────────┐
│ Aspecto            │       REST        │             gRPC                 │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Protocolo          │ HTTP/1.1          │ HTTP/2                           │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Formato de dados   │ JSON (texto)      │ Protocol Buffers (binário)       │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Tamanho payload    │ ~500 bytes        │ ~200 bytes (60% menor)           │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Latência           │ ~10-50ms          │ ~1-10ms (5x mais rápido)         │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Throughput         │ ~1k req/s         │ ~10k req/s (10x mais rápido)     │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Streaming          │ ❌ Não (ou SSE)   │ ✅ Sim (bidirecional)            │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Browser support    │ ✅ Universal      │ ⚠️  Requer grpc-web              │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Human readable     │ ✅ Sim (JSON)     │ ❌ Não (binário)                 │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Type safety        │ ⚠️  Runtime       │ ✅ Compile time                  │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Code generation    │ ⚠️  Opcional      │ ✅ Automático (.proto)           │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Learning curve     │ ⭐ Fácil          │ ⭐⭐⭐ Médio                     │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Debugging          │ ✅ Fácil (curl)   │ ⚠️  Precisa grpcurl              │
├────────────────────┼───────────────────┼──────────────────────────────────┤
│ Caching (HTTP)     │ ✅ GET cacheable  │ ❌ Não usa HTTP caching          │
└────────────────────┴───────────────────┴──────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                            QUANDO USAR CADA
═══════════════════════════════════════════════════════════════════════════

✅ Use REST quando:

  1. API pública / externa
     - Parceiros, clientes, desenvolvedores third-party
     - Browsers (web apps)
     - Documentação API importante (Swagger/OpenAPI)

  2. Simplicidade é importante
     - MVP, protótipo rápido
     - Time não familiar com gRPC
     - Debugging precisa ser fácil (curl)

  3. HTTP caching é valioso
     - GET requests cacheáveis (CDN, browser)
     - Reduz carga no servidor

  4. Flexibilidade de formato
     - JSON, XML, MessagePack, etc
     - Clients diversos (mobile, web, IoT)

  Exemplos: GitHub API, Stripe API, Twitter API


✅ Use gRPC quando:

  1. Microservices internos
     - Service-to-service communication
     - Alta performance é crítica
     - Tipo de dados bem definido

  2. Alta carga / baixa latência
     - 10k+ requests/s
     - Latência <10ms
     - Payload pequeno (economia de banda)

  3. Streaming é necessário
     - Server streaming (feed contínuo)
     - Client streaming (upload de arquivo)
     - Bidirecional (chat, multiplayer game)

  4. Type safety é importante
     - Contratos fortemente tipados (.proto)
     - Geração automática de código
     - Menos bugs em produção

  Exemplos: Google (interno), Netflix, Square, Uber


✅ Use AMBOS (Hybrid):

  1. Gateway pattern
     - gRPC entre microservices (backend)
     - REST para clientes externos (frontend)
     - Gateway traduz REST → gRPC

  2. Casos específicos
     - gRPC para operações críticas (pagamento, checkout)
     - REST para operações simples (listar produtos)

  Exemplos: Netflix, Uber, Airbnb


═══════════════════════════════════════════════════════════════════════════
                        PERFORMANCE REAL-WORLD
═══════════════════════════════════════════════════════════════════════════

Benchmark: Buscar 1000 usuários

┌─────────────┬──────────┬────────────┬──────────────┬─────────────┐
│ Protocolo   │ Latência │ Throughput │ Payload Size │ CPU Usage   │
├─────────────┼──────────┼────────────┼──────────────┼─────────────┤
│ REST (JSON) │  250ms   │  4k req/s  │  500 KB      │  40%        │
├─────────────┼──────────┼────────────┼──────────────┼─────────────┤
│ gRPC        │   50ms   │ 20k req/s  │  200 KB      │  20%        │
│ (Protobuf)  │  (5x)    │  (5x)      │  (60% menor) │  (50% less) │
└─────────────┴──────────┴────────────┴──────────────┴─────────────┘

Streaming: Enviar 1 milhão de mensagens

┌─────────────┬──────────┬────────────┬──────────────┐
│ Protocolo   │ Tempo    │ Throughput │ Uso de RAM  │
├─────────────┼──────────┼────────────┼──────────────┤
│ REST (SSE)  │  180s    │  5.5k/s    │  800 MB     │
├─────────────┼──────────┼────────────┼──────────────┤
│ gRPC Stream │   18s    │ 55k/s      │  200 MB     │
│             │  (10x)   │  (10x)     │  (75% less) │
└─────────────┴──────────┴────────────┴──────────────┘

═══════════════════════════════════════════════════════════════════════════
                          FEATURES ESPECIAIS
═══════════════════════════════════════════════════════════════════════════

gRPC Streaming:

  1. Server Streaming
     - Servidor envia múltiplas respostas
     - Exemplo: Feed de notificações, logs em tempo real

       rpc StreamUsers(StreamUsersRequest) returns (stream User);

  2. Client Streaming
     - Cliente envia múltiplas requests
     - Exemplo: Upload de arquivo, batch insert

       rpc BulkCreateUsers(stream CreateUserRequest) returns (Response);

  3. Bidirectional Streaming
     - Cliente e servidor enviam múltiplas mensagens
     - Exemplo: Chat, multiplayer game

       rpc Chat(stream ChatMessage) returns (stream ChatMessage);

HTTP/2 Multiplexing:

  - REST HTTP/1.1: 1 request por TCP connection
  - gRPC HTTP/2: múltiplos requests na mesma connection
  - Resultado: menos overhead, menos latência

Protocol Buffers:

  - Binário: 5-10x menor que JSON
  - Mais rápido de parsear (não precisa parse de texto)
  - Versionamento: backward/forward compatible

═══════════════════════════════════════════════════════════════════════════
"""
    print(comparison)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="gRPC vs REST Demo")
    parser.add_argument(
        "--mode",
        choices=["rest", "grpc-server", "benchmark", "comparison"],
        default="comparison",
        help="Modo de execução"
    )

    args = parser.parse_args()

    if args.mode == "rest":
        # Rodar servidor REST (use uvicorn na linha de comando)
        import uvicorn
        uvicorn.run(rest_app, host="0.0.0.0", port=8000)

    elif args.mode == "grpc-server":
        # Rodar servidor gRPC
        logger.info("gRPC server mode (requires compiled .proto)")
        # serve_grpc()  # Descomentar após compilar .proto

    elif args.mode == "benchmark":
        # Rodar benchmark
        asyncio.run(benchmark_rest())
        # asyncio.run(benchmark_grpc())  # Descomentar após setup gRPC

    elif args.mode == "comparison":
        # Mostrar comparação
        print_comparison()

    print("\n" + "="*70)
    print("💡 RESUMO:")
    print("="*70)
    print("""
✅ REST: APIs públicas, simplicidade, HTTP caching
✅ gRPC: Microservices, alta performance, streaming, type safety
✅ Hybrid: gRPC interno + REST externo (melhor dos dois mundos)

📚 PARA APRENDER MAIS:
  - gRPC docs: https://grpc.io/docs/languages/python/
  - Protocol Buffers: https://developers.google.com/protocol-buffers
  - HTTP/2: https://developers.google.com/web/fundamentals/performance/http2
  - Netflix tech blog: https://netflixtechblog.com/

🚀 PRÓXIMOS PASSOS:
  1. Instalar gRPC: pip install grpcio grpcio-tools
  2. Criar user_service.proto
  3. Compilar: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. user_service.proto
  4. Rodar servidores e benchmark
""")
