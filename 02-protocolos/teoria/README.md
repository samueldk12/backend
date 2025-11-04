# Módulo 02 - Protocolos e Comunicação

## 🎯 Objetivo

Entender como dados trafegam pela rede e como escolher o protocolo certo para cada situação.

---

## 📚 Conteúdo

1. [Modelo OSI e TCP/IP](#1-modelo-osi-e-tcpip)
2. [TCP vs UDP](#2-tcp-vs-udp)
3. [HTTP: 1.1 vs 2 vs 3](#3-http-11-vs-2-vs-3)
4. [REST vs gRPC vs GraphQL](#4-rest-vs-grpc-vs-graphql)
5. [WebSockets vs SSE vs Long Polling](#5-websockets-vs-sse-vs-long-polling)
6. [Serialização de Dados](#6-serialização-de-dados)
7. [Encoding e Compression](#7-encoding-e-compression)

---

## 1. Modelo OSI e TCP/IP

### 1.1 As 7 Camadas do OSI

```
┌──────────────────────────────────────────────┐
│ 7. APLICAÇÃO  │ HTTP, FTP, SMTP, DNS        │ ← Onde seu código vive
├──────────────────────────────────────────────┤
│ 6. APRESENTAÇÃO│ SSL/TLS, Encoding          │
├──────────────────────────────────────────────┤
│ 5. SESSÃO     │ Session management          │
├──────────────────────────────────────────────┤
│ 4. TRANSPORTE │ TCP, UDP                    │ ← Conexão fim-a-fim
├──────────────────────────────────────────────┤
│ 3. REDE       │ IP, ICMP, Routing           │ ← Endereçamento
├──────────────────────────────────────────────┤
│ 2. ENLACE     │ Ethernet, WiFi, MAC         │
├──────────────────────────────────────────────┤
│ 1. FÍSICA     │ Cabos, sinais elétricos     │
└──────────────────────────────────────────────┘
```

### 1.2 Modelo TCP/IP (Prático)

```
┌────────────────────────────────────┐
│  Aplicação (HTTP, DNS, SSH)        │ ← FastAPI, requests
├────────────────────────────────────┤
│  Transporte (TCP, UDP)             │ ← socket
├────────────────────────────────────┤
│  Internet (IP)                     │
├────────────────────────────────────┤
│  Acesso à Rede (Ethernet, WiFi)    │
└────────────────────────────────────┘
```

---

## 2. TCP vs UDP

### 2.1 TCP (Transmission Control Protocol)

**Características:**
- ✅ Confiável (garante entrega)
- ✅ Ordenado (pacotes chegam na ordem)
- ✅ Controle de fluxo
- ✅ Detecção de erros
- ❌ Mais lento (overhead de garantias)
- ❌ Handshake (latência inicial)

**Three-Way Handshake:**
```
Cliente                    Servidor
   │                          │
   │──────── SYN ────────────>│  1. Cliente: "Vamos conversar?"
   │                          │
   │<─────── SYN-ACK ─────────│  2. Servidor: "OK, vamos!"
   │                          │
   │──────── ACK ────────────>│  3. Cliente: "Confirmado!"
   │                          │
   │      Conexão aberta      │
   │<══════════════════════════>│
```

**Quando usar:**
- HTTP/HTTPS
- Transferência de arquivos (FTP)
- Email (SMTP, POP3, IMAP)
- SSH, Telnet
- Database connections

### 2.2 UDP (User Datagram Protocol)

**Características:**
- ✅ Rápido (sem overhead)
- ✅ Baixa latência
- ❌ Não confiável (pode perder pacotes)
- ❌ Sem ordem garantida
- ❌ Sem controle de fluxo

**Quando usar:**
- Video streaming (perda de alguns frames é aceitável)
- VoIP (voz sobre IP)
- Gaming online (latência > perda de pacotes)
- DNS queries
- Live broadcasts

### 2.3 Comparação

| Aspecto | TCP | UDP |
|---------|-----|-----|
| **Confiabilidade** | Garantida | Não garantida |
| **Velocidade** | Mais lento | Mais rápido |
| **Overhead** | Alto | Baixo |
| **Latência** | Maior | Menor |
| **Uso de casos** | Dados críticos | Real-time |

---

## 3. HTTP: 1.1 vs 2 vs 3

### 3.1 HTTP/1.1 (1997)

```
Cliente → Servidor: GET /index.html
Cliente ← Servidor: 200 OK + HTML

Cliente → Servidor: GET /style.css    ← Nova conexão!
Cliente ← Servidor: 200 OK + CSS

Cliente → Servidor: GET /script.js   ← Outra conexão!
Cliente ← Servidor: 200 OK + JS
```

**Limitações:**
- Head-of-line blocking
- Uma requisição por vez por conexão
- Headers em texto (overhead)
- Sem priorização

### 3.2 HTTP/2 (2015)

```
Cliente → Servidor: Múltiplas requisições paralelas
              ↓
    ┌─────────┼─────────┐
    │         │         │
  GET /html GET /css GET /js
    │         │         │
    └─────────┼─────────┘
              ↓
Cliente ← Servidor: Respostas multiplexadas
```

**Melhorias:**
- ✅ Multiplexing (múltiplas requisições na mesma conexão)
- ✅ Server push (servidor envia recursos antecipadamente)
- ✅ Header compression (HPACK)
- ✅ Stream prioritization
- ❌ Ainda sofre de TCP head-of-line blocking

### 3.3 HTTP/3 (2022)

**Base:** QUIC (sobre UDP em vez de TCP)

**Melhorias:**
- ✅ Sem head-of-line blocking (UDP)
- ✅ Conexão mais rápida (0-RTT)
- ✅ Melhor em redes instáveis
- ✅ Migração de conexão (mudança de IP/rede sem reconectar)

### 3.4 Quando usar cada um?

| Versão | Quando usar |
|--------|-------------|
| **HTTP/1.1** | Legado, servidores antigos |
| **HTTP/2** | APIs modernas, web apps (padrão atual) |
| **HTTP/3** | Low latency, mobile, streaming |

---

## 4. REST vs gRPC vs GraphQL

### 4.1 REST (Representational State Transfer)

```python
# Exemplo REST
GET    /users          # Listar usuários
GET    /users/123      # Buscar usuário
POST   /users          # Criar usuário
PUT    /users/123      # Atualizar usuário
DELETE /users/123      # Deletar usuário
```

**Características:**
- ✅ Simples e amplamente adotado
- ✅ Stateless
- ✅ Cacheable
- ✅ Padrão HTTP (GET, POST, PUT, DELETE)
- ❌ Over-fetching (pega mais dados que precisa)
- ❌ Under-fetching (precisa de múltiplas chamadas)
- ❌ Versionamento pode ser complicado

### 4.2 gRPC (Google RPC)

```protobuf
// Definição Protocol Buffers
service UserService {
  rpc GetUser (UserRequest) returns (UserResponse);
  rpc ListUsers (Empty) returns (stream UserResponse);
}

message UserRequest {
  int32 id = 1;
}
```

**Características:**
- ✅ Muito rápido (Protocol Buffers binário)
- ✅ HTTP/2 (multiplexing, streaming)
- ✅ Streaming bidirecional
- ✅ Typed (schema definido)
- ❌ Menos legível que JSON
- ❌ Suporte limitado em browsers
- ❌ Curva de aprendizado

**Quando usar:**
- Microservices internos
- Alta performance necessária
- Streaming de dados
- Comunicação server-to-server

### 4.3 GraphQL

```graphql
# Query (cliente escolhe campos)
query {
  user(id: 123) {
    name
    email
    posts {
      title
      createdAt
    }
  }
}

# Response
{
  "data": {
    "user": {
      "name": "João",
      "email": "joao@example.com",
      "posts": [...]
    }
  }
}
```

**Características:**
- ✅ Cliente controla dados retornados
- ✅ Sem over-fetching
- ✅ Uma única endpoint
- ✅ Schema strongly-typed
- ❌ Complexidade adicional
- ❌ Caching mais difícil
- ❌ Pode ser menos performático (N+1 queries)

### 4.4 Comparação

| Aspecto | REST | gRPC | GraphQL |
|---------|------|------|---------|
| **Performance** | Média | Alta | Média |
| **Simplicidade** | Alta | Média | Baixa |
| **Flexibilidade** | Baixa | Baixa | Alta |
| **Caching** | Fácil | Difícil | Médio |
| **Browser support** | Sim | Limitado | Sim |
| **Streaming** | Não | Sim | Sim (subscriptions) |

**Decisão:**
```
API pública simples → REST
Microservices performance → gRPC
Frontend complexo → GraphQL
```

---

## 5. WebSockets vs SSE vs Long Polling

### 5.1 WebSocket

```python
# Conexão bidirecional persistente
Cliente ⇄ Servidor

# Cliente e servidor podem enviar dados a qualquer momento
```

**Características:**
- ✅ Full-duplex (bidirectional)
- ✅ Baixa latência
- ✅ Menos overhead
- ❌ Mais complexo
- ❌ Requer suporte especial (proxies, load balancers)

**Quando usar:**
- Chat em tempo real
- Gaming online
- Collaborative editing
- Trading platforms

### 5.2 Server-Sent Events (SSE)

```python
# Conexão unidirecional: Servidor → Cliente
Servidor → Cliente (stream de eventos)
Cliente → Servidor (HTTP normal)
```

**Características:**
- ✅ Simples (HTTP puro)
- ✅ Reconexão automática
- ✅ Event IDs (pode retomar de onde parou)
- ❌ Unidirecional (servidor → cliente apenas)
- ❌ Limitações em alguns browsers

**Quando usar:**
- Notificações
- Feed de atualizações
- Streaming de logs
- Live scores

### 5.3 Long Polling

```python
# Cliente faz requisição e servidor "segura" até ter dados
Cliente → Servidor: GET /updates
          (servidor espera...)
          (evento ocorre)
Cliente ← Servidor: Resposta com dados
Cliente → Servidor: Nova requisição imediata
```

**Características:**
- ✅ Funciona em qualquer ambiente (HTTP puro)
- ✅ Simples de implementar
- ❌ Overhead (muitas requisições)
- ❌ Latência maior
- ❌ Consome mais recursos

### 5.4 Comparação

| Aspecto | WebSocket | SSE | Long Polling |
|---------|-----------|-----|--------------|
| **Direção** | Bidirecional | Servidor→Cliente | Request-response |
| **Latência** | Muito baixa | Baixa | Média |
| **Overhead** | Baixo | Médio | Alto |
| **Simplicidade** | Baixa | Alta | Média |
| **Suporte** | Bom | Bom | Universal |

---

## 6. Serialização de Dados

### 6.1 JSON

```json
{
  "id": 123,
  "name": "João",
  "active": true,
  "score": 95.5
}
```

**Prós:**
- ✅ Legível
- ✅ Amplamente suportado
- ✅ Fácil de debugar

**Contras:**
- ❌ Texto (maior que binário)
- ❌ Sem schema (erros em runtime)
- ❌ Parsing lento

### 6.2 Protocol Buffers (protobuf)

```protobuf
message User {
  int32 id = 1;
  string name = 2;
  bool active = 3;
  float score = 4;
}
```

**Prós:**
- ✅ Binário (menor tamanho)
- ✅ Muito rápido
- ✅ Schema obrigatório (type-safe)
- ✅ Backward compatible

**Contras:**
- ❌ Não legível
- ❌ Requer compilação
- ❌ Curva de aprendizado

### 6.3 MessagePack

```python
# Binário, mas compatível com JSON
import msgpack

data = {"id": 123, "name": "João"}
packed = msgpack.packb(data)  # Binário
unpacked = msgpack.unpackb(packed)  # Dict Python
```

**Prós:**
- ✅ Compatível com JSON
- ✅ Menor que JSON
- ✅ Mais rápido que JSON

**Contras:**
- ❌ Menos adotado
- ❌ Não legível

### 6.4 Comparação de Tamanho

```
Dados: {"id": 123, "name": "João Silva", "score": 95.5}

JSON:         58 bytes
MessagePack:  35 bytes (40% menor)
Protobuf:     19 bytes (67% menor)
JSON + gzip:  48 bytes
```

---

## 7. Encoding e Compression

### 7.1 Encodings

**UTF-8:**
- Padrão universal
- Variável (1-4 bytes por caractere)
- ASCII-compatible

**Base64:**
- Converte binário em texto
- Aumenta tamanho em ~33%
- Usado para: emails, URLs, JSON

**URL Encoding:**
- Escapa caracteres especiais
- `hello world` → `hello%20world`

### 7.2 Compression

**gzip:**
- Padrão web
- Compressão ~70-80%
- Bom para texto (HTML, JSON, CSS)

**brotli:**
- Melhor que gzip (~20% a mais)
- Suportado por browsers modernos
- Mais lento para comprimir

**Comparação:**
```
HTML original:     100 KB
gzip:               20 KB (80% redução)
brotli:             16 KB (84% redução)
```

---

## 🎓 Resumo - Decisões

### Para APIs:

```
API pública simples          → REST + JSON + HTTP/2
Microservices high-perf      → gRPC + Protobuf
Frontend complexo            → GraphQL + JSON
Real-time bidirecional       → WebSocket
Real-time uni (server→cli)   → SSE
```

### Para dados:

```
Legibilidade                 → JSON
Performance                  → Protobuf
Compatibilidade + perf       → MessagePack
```

### Para transport:

```
Dados críticos               → TCP
Real-time (gaming, voice)    → UDP
Web tradicional              → HTTP/2
Low latency mobile           → HTTP/3
```

---

## 📝 Próximos Passos

1. Veja exemplos em [`../exemplos/`](../exemplos/)
2. Faça exercícios em [`../exercicios/`](../exercicios/)
3. Avance para **[Módulo 03 - Banco de Dados](../../03-banco-dados/teoria/README.md)**
