# 💬 Projeto 9: WhatsApp (System Design)

> Real-time messaging - aparece em 90% das entrevistas de messaging systems

---

## 📋 Problema

**Design de sistema de mensagens em tempo real para 2B usuários.**

**Estimativas:**
```
Usuários: 2B total, 500M online simultâneos
Mensagens: 100B mensagens/dia = 1.1M mensagens/segundo
Picos: 2-3x média = 3M mensagens/segundo

Storage:
- Mensagens: 100B/dia * 365 * 5 anos * 200 bytes = 3.6 PB
- Mídia: 30% têm foto/vídeo → +10 PB
- Total: ~14 PB em 5 anos

WebSocket connections: 500M simultâneas (MASSIVO!)
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     MESSAGE FLOW                             │
│                                                              │
│  Cliente A                  Servidor                Cliente B │
│     │                          │                        │     │
│     │──1. send_message()──────>│                        │     │
│     │                          │──2. store──>Cassandra  │     │
│     │                          │──3. push──>│           │     │
│     │                          │            └──────────>│     │
│     │<─────4. ack──────────────│                        │     │
│                                                               │
└──────────────────────────────────────────────────────────────┘

COMPONENTS:
- WebSocket Gateway (Netty/Go): Manter conexões
- Message Service: Routing e persistência
- Cassandra: Armazenamento de mensagens
- Redis: Online users, message queue
- Kafka: Event streaming
- S3: Armazenamento de mídia
```

---

## 🗄️ Schema

```sql
-- Cassandra para mensagens (time-series)

CREATE TABLE messages (
    conversation_id UUID,
    message_id UUID,
    sender_id BIGINT,
    content TEXT,
    media_url TEXT,
    created_at TIMESTAMP,
    status VARCHAR(20), -- 'sent', 'delivered', 'read'
    PRIMARY KEY (conversation_id, created_at, message_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- Conversas (inbox)
CREATE TABLE conversations (
    user_id BIGINT,
    conversation_id UUID,
    other_user_id BIGINT,
    last_message TEXT,
    last_message_at TIMESTAMP,
    unread_count INT,
    PRIMARY KEY (user_id, last_message_at, conversation_id)
) WITH CLUSTERING ORDER BY (last_message_at DESC);

-- Online presence
-- Redis: user:{user_id}:online = "ws_server_3"
```

---

## 🔌 WebSocket Connection Management

```python
from fastapi import WebSocket
import redis
import json

class ConnectionManager:
    """
    Gerenciar 500M conexões WebSocket

    Desafio: Single server suporta ~65k conexões (file descriptor limit)
    Solução: Múltiplos servidores + Redis Pub/Sub
    """

    def __init__(self, server_id: str):
        self.server_id = server_id  # "ws_server_1"
        self.connections = {}  # user_id -> WebSocket
        self.redis = redis.Redis()

        # Subscribe para mensagens destinadas a este servidor
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(f"server:{server_id}")

    async def connect(self, websocket: WebSocket, user_id: int):
        """Conectar usuário"""
        await websocket.accept()

        # Salvar conexão local
        self.connections[user_id] = websocket

        # Registrar user online (qual servidor)
        self.redis.setex(
            f"user:{user_id}:online",
            3600,  # 1 hora
            self.server_id
        )

        print(f"✓ User {user_id} connected to {self.server_id}")

    async def send_message(self, user_id: int, message: dict):
        """
        Enviar mensagem para user

        Se user está conectado neste servidor: enviar direto
        Se user está em outro servidor: enviar via Redis Pub/Sub
        """
        # Verificar qual servidor tem user conectado
        server = self.redis.get(f"user:{user_id}:online")

        if not server:
            # User offline, salvar em queue
            self.redis.lpush(
                f"user:{user_id}:pending_messages",
                json.dumps(message)
            )
            return

        server = server.decode()

        if server == self.server_id:
            # User conectado neste servidor
            if user_id in self.connections:
                await self.connections[user_id].send_json(message)
        else:
            # User conectado em outro servidor, usar Redis Pub/Sub
            self.redis.publish(
                f"server:{server}",
                json.dumps({'user_id': user_id, 'message': message})
            )


# Instanciar por servidor
import os
SERVER_ID = os.getenv("SERVER_ID", "ws_server_1")
connection_manager = ConnectionManager(SERVER_ID)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint"""
    await connection_manager.connect(websocket, user_id)

    try:
        while True:
            # Receber mensagens do cliente
            data = await websocket.receive_json()

            # Processar send message
            await handle_send_message(user_id, data)
    except:
        # Desconectar
        del connection_manager.connections[user_id]
        connection_manager.redis.delete(f"user:{user_id}:online")
```

---

## 📨 Message Sending

```python
@app.post("/messages/send")
async def send_message(
    sender_id: int,
    receiver_id: int,
    content: str,
    media_url: str = None
):
    """
    Enviar mensagem

    Flow:
    1. Validar sender/receiver
    2. Salvar no Cassandra
    3. Enviar via WebSocket (se online)
    4. Notificar se offline (push notification)
    """
    # 1. Validar
    if len(content) > 10000:
        raise HTTPException(400, "Message too long")

    # 2. Criar message
    message_id = uuid.uuid4()
    conversation_id = get_or_create_conversation(sender_id, receiver_id)

    # 3. Salvar no Cassandra
    cassandra.execute("""
        INSERT INTO messages (
            conversation_id, message_id, sender_id,
            content, media_url, created_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, 'sent')
    """, (conversation_id, message_id, sender_id, content, media_url, datetime.utcnow()))

    # 4. Atualizar conversation (inbox)
    cassandra.execute("""
        UPDATE conversations
        SET last_message = ?, last_message_at = ?, unread_count = unread_count + 1
        WHERE user_id = ? AND conversation_id = ?
    """, (content, datetime.utcnow(), receiver_id, conversation_id))

    # 5. Enviar via WebSocket
    message_data = {
        'message_id': str(message_id),
        'conversation_id': str(conversation_id),
        'sender_id': sender_id,
        'content': content,
        'media_url': media_url,
        'timestamp': time.time()
    }

    await connection_manager.send_message(receiver_id, message_data)

    # 6. Delivery acknowledgment (assíncrono)
    kafka_producer.send('message_delivery', {
        'message_id': str(message_id),
        'receiver_id': receiver_id,
        'sent_at': time.time()
    })

    return {
        'message_id': str(message_id),
        'status': 'sent'
    }
```

---

## ✅ Read Receipts & Status

```python
@app.post("/messages/{message_id}/status")
async def update_message_status(
    message_id: str,
    user_id: int,
    status: str  # 'delivered' or 'read'
):
    """
    Atualizar status de mensagem

    delivered: Mensagem chegou no device
    read: Usuário abriu chat e leu
    """
    # Atualizar status
    cassandra.execute("""
        UPDATE messages
        SET status = ?
        WHERE message_id = ?
    """, (status, uuid.UUID(message_id)))

    # Notificar sender sobre status (via WebSocket)
    message = get_message(message_id)

    await connection_manager.send_message(
        message.sender_id,
        {
            'type': 'status_update',
            'message_id': message_id,
            'status': status
        }
    )

    return {'status': 'ok'}
```

---

## 📷 Media Upload (WhatsApp Pattern)

```python
from fastapi import UploadFile
import boto3

s3 = boto3.client('s3')

@app.post("/media/upload")
async def upload_media(file: UploadFile, user_id: int):
    """
    Upload de mídia (foto/vídeo)

    Flow (otimizado):
    1. Upload direto para S3 (client-side upload com presigned URL)
    2. Server apenas gera URL e valida
    3. Comprimir imagens (thumbnail para preview)
    """
    # Validar tamanho
    MAX_SIZE = 100 * 1024 * 1024  # 100 MB

    # Gerar key único
    file_ext = file.filename.split('.')[-1]
    file_key = f"media/{user_id}/{uuid.uuid4()}.{file_ext}"

    # Upload para S3
    s3.upload_fileobj(
        file.file,
        'whatsapp-media',
        file_key,
        ExtraArgs={'ContentType': file.content_type}
    )

    # Gerar thumbnail (assíncrono para imagens)
    if file.content_type.startswith('image/'):
        kafka_producer.send('thumbnail_generation', {
            'file_key': file_key,
            'user_id': user_id
        })

    # URL pública (via CloudFront CDN)
    media_url = f"https://cdn.whatsapp.com/{file_key}"

    return {
        'media_url': media_url,
        'thumbnail_url': f"{media_url}?size=thumbnail"
    }
```

---

## 👥 Group Chats

```python
"""
Group chats = desafio de fanout

Grupo com 256 pessoas:
  - 1 mensagem → 256 entregas (fanout)
  - 100 mensagens/s → 25,600 entregas/s (!)

Solução: Fanout assíncrono
"""

CREATE TABLE group_messages (
    group_id UUID,
    message_id UUID,
    sender_id BIGINT,
    content TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (group_id, created_at, message_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

CREATE TABLE group_members (
    group_id UUID,
    user_id BIGINT,
    joined_at TIMESTAMP,
    PRIMARY KEY (group_id, user_id)
);


@app.post("/groups/{group_id}/messages")
async def send_group_message(
    group_id: str,
    sender_id: int,
    content: str
):
    """Enviar mensagem para grupo"""
    # 1. Salvar mensagem
    message_id = uuid.uuid4()

    cassandra.execute("""
        INSERT INTO group_messages (
            group_id, message_id, sender_id, content, created_at
        ) VALUES (?, ?, ?, ?, ?)
    """, (uuid.UUID(group_id), message_id, sender_id, content, datetime.utcnow()))

    # 2. Fanout assíncrono (Kafka)
    kafka_producer.send('group_message_fanout', {
        'group_id': group_id,
        'message_id': str(message_id),
        'sender_id': sender_id,
        'content': content
    })

    return {'message_id': str(message_id)}


# Worker de fanout
def group_fanout_worker():
    """Entregar mensagem para todos membros do grupo"""
    consumer = KafkaConsumer('group_message_fanout')

    for message in consumer:
        data = message.value

        group_id = data['group_id']
        message_data = {
            'message_id': data['message_id'],
            'content': data['content'],
            'sender_id': data['sender_id']
        }

        # Buscar membros do grupo
        members = cassandra.execute("""
            SELECT user_id FROM group_members WHERE group_id = ?
        """, (uuid.UUID(group_id),))

        # Enviar para cada membro (em paralelo)
        tasks = [
            connection_manager.send_message(member.user_id, message_data)
            for member in members
            if member.user_id != data['sender_id']  # Não enviar para sender
        ]

        await asyncio.gather(*tasks)
```

---

## 🔐 End-to-End Encryption (Signal Protocol)

```python
"""
WhatsApp usa Signal Protocol para E2EE

Conceito:
- Cada user tem par de chaves (pública/privada)
- Mensagens criptografadas com chave do receiver
- Servidor NUNCA vê conteúdo (apenas metadata)

Flow:
1. Sender busca public key do receiver
2. Sender criptografa mensagem com public key
3. Server armazena mensagem CRIPTOGRAFADA
4. Receiver descriptografa com private key
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

def generate_keypair():
    """Gerar par de chaves (ao criar conta)"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    return private_key, public_key


def encrypt_message(content: str, receiver_public_key) -> bytes:
    """Criptografar mensagem (client-side)"""
    encrypted = receiver_public_key.encrypt(
        content.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return encrypted


def decrypt_message(encrypted_content: bytes, private_key) -> str:
    """Descriptografar mensagem (client-side)"""
    decrypted = private_key.decrypt(
        encrypted_content,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return decrypted.decode()


# Servidor nunca vê plaintext!
```

---

## 🎯 Otimizações Críticas

### 1. Message Batching

```python
"""
Ao invés de enviar 1 mensagem por WebSocket frame:
Batch múltiplas mensagens em 1 frame

Exemplo:
100 mensagens/s → 100 frames (overhead!)
Batch a cada 100ms → 10 frames (10x menos overhead)
"""

class MessageBatcher:
    def __init__(self, flush_interval: float = 0.1):
        self.buffer = []
        self.flush_interval = flush_interval

    async def add_message(self, user_id: int, message: dict):
        """Adicionar ao buffer"""
        self.buffer.append((user_id, message))

        # Flush se buffer cheio
        if len(self.buffer) >= 100:
            await self.flush()

    async def flush(self):
        """Enviar batch"""
        if not self.buffer:
            return

        # Agrupar por user_id
        by_user = {}
        for user_id, message in self.buffer:
            if user_id not in by_user:
                by_user[user_id] = []
            by_user[user_id].append(message)

        # Enviar batch para cada user
        for user_id, messages in by_user.items():
            await connection_manager.send_message(
                user_id,
                {'type': 'batch', 'messages': messages}
            )

        self.buffer.clear()
```

### 2. Sharding Strategy

```python
"""
Shard por conversation_id (Cassandra partition key)

conversation_id = hash(min(user1_id, user2_id), max(user1_id, user2_id))

Garante:
- Todas mensagens de 1 conversa no mesmo shard
- Queries rápidas (sem cross-shard)
- Load balancing (hash distribui uniformemente)
"""

def get_conversation_id(user1_id: int, user2_id: int) -> uuid.UUID:
    """Gerar conversation_id determinístico"""
    min_id = min(user1_id, user2_id)
    max_id = max(user1_id, user2_id)

    # UUID v5 (determinístico)
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    name = f"{min_id}:{max_id}"

    return uuid.uuid5(namespace, name)
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Como escalar para 500M conexões WebSocket?"

**Você:** "Problema: 1 servidor suporta ~65k conexões (file descriptor limit).

Solução:
1. **Múltiplos servidores**: 500M / 65k = ~8,000 servidores WebSocket
2. **Redis Pub/Sub**: Coordenar servidores (routing de mensagens)
3. **Load balancer com sticky sessions**: Garantir user sempre conecta ao mesmo servidor (enquanto possível)
4. **Consistent hashing**: Distribuir users entre servidores de forma balanceada"

---

**Interviewer:** "Como garantir ordem de mensagens?"

**Você:** "Desafios:
- Clock skew entre servidores
- Network reordering

Soluções:
1. **Lamport timestamps**: Cada mensagem tem (timestamp, server_id, sequence)
2. **Sequence numbers por conversa**: Auto-increment no cliente
3. **Cassandra clustering order**: `ORDER BY created_at DESC` garante ordem na query

WhatsApp usa sequence numbers + Cassandra ordering."

---

## ✅ Checklist

- [ ] WebSocket connection management (multi-server)
- [ ] Message sending e receiving
- [ ] Delivery e read receipts
- [ ] Media upload (S3 + CDN)
- [ ] Group chats (fanout)
- [ ] End-to-end encryption
- [ ] Sharding (Cassandra)
- [ ] Optimizações (batching, caching)

---

**Messaging system design fundamental! 💬**
