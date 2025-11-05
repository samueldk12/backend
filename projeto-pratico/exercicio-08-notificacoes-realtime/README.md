# Exercício 08 - Notificações em Tempo Real

> Sistema completo de notificações push usando WebSocket, com fallback para polling e integração com push notifications mobile.

---

## 📋 Objetivo

Implementar sistema de notificações escalável, explorando:
- WebSocket para notificações em tempo real
- Tipos de notificações (like, comment, follow, mention)
- Polling como fallback para browsers antigos
- Marcação de lidas/não lidas
- Agrupamento de notificações (aggregation)
- Push notifications para mobile (FCM/APNs)
- Escalabilidade com Redis Pub/Sub

---

## 🎯 O Que Vamos Aprender

1. **WebSocket**: Conexões bidirecionais persistentes
2. **Connection management**: Rastrear usuários conectados
3. **Broadcasting**: Enviar para múltiplos usuários
4. **Redis Pub/Sub**: Escalar para múltiplos servidores
5. **Notification aggregation**: "João e mais 10 pessoas curtiram seu post"
6. **Read receipts**: Marcar como lida
7. **Fallback strategies**: Polling, SSE

---

## 📊 Modelagem de Notificações

### Modelo de Dados

```python
# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from datetime import datetime
import enum

class NotificationType(str, enum.Enum):
    LIKE = "like"
    COMMENT = "comment"
    REPLY = "reply"
    FOLLOW = "follow"
    MENTION = "mention"


class Notification(Base):
    """
    Notificação para usuário

    Exemplos:
    - "João curtiu seu post"
    - "Maria comentou: 'Ótimo post!'"
    - "Pedro começou a te seguir"
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    # Receptor da notificação
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Tipo de notificação
    type = Column(Enum(NotificationType), nullable=False)

    # Quem gerou a notificação
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Objeto relacionado (post, comment, etc)
    target_type = Column(String(50))  # "post", "comment", "user"
    target_id = Column(Integer)

    # Conteúdo
    message = Column(String(255))

    # Estado
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    actor = relationship("User", foreign_keys=[actor_id])


# Índices importantes
Index('ix_notifications_user_read', Notification.user_id, Notification.is_read)
Index('ix_notifications_user_created', Notification.user_id, Notification.created_at)
```

---

## 🔧 Implementação WebSocket

### 1. Connection Manager (FastAPI)

```python
# services/websocket_manager.py
from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gerencia conexões WebSocket de usuários

    Mantém mapa: user_id -> Set[WebSocket]
    Usuário pode ter múltiplas conexões (múltiplas abas, dispositivos)
    """

    def __init__(self):
        # user_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Conectar usuário"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Desconectar usuário"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Se não tem mais conexões, remover do dict
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: int):
        """
        Enviar mensagem para um usuário específico

        Envia para TODAS as conexões do usuário (múltiplas abas)
        """
        if user_id not in self.active_connections:
            logger.warning(f"User {user_id} not connected")
            return

        disconnected = set()

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.add(websocket)

        # Remover conexões que falharam
        for ws in disconnected:
            self.active_connections[user_id].discard(ws)

    async def broadcast(self, message: dict, user_ids: list):
        """Broadcast para múltiplos usuários"""
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

    def is_connected(self, user_id: int) -> bool:
        """Verificar se usuário está conectado"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_connected_users(self) -> list:
        """Retornar lista de usuários conectados"""
        return list(self.active_connections.keys())


# Singleton
manager = ConnectionManager()
```

---

### 2. WebSocket Endpoint

```python
# routes/notifications.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,  # JWT token como query param
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint para notificações

    Cliente conecta: ws://localhost:8000/ws/notifications?token=<jwt>
    Servidor envia notificações em tempo real
    """

    # Autenticar via JWT token
    try:
        user = verify_jwt_token(token)
        if not user:
            await websocket.close(code=1008)  # Policy violation
            return
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        await websocket.close(code=1008)
        return

    # Conectar
    await manager.connect(websocket, user.id)

    try:
        # Enviar notificações não lidas ao conectar
        unread_notifications = get_unread_notifications(db, user.id)
        if unread_notifications:
            await websocket.send_json({
                "type": "initial_load",
                "notifications": [serialize_notification(n) for n in unread_notifications],
                "unread_count": len(unread_notifications)
            })

        # Loop: receber mensagens do cliente
        while True:
            data = await websocket.receive_text()

            # Cliente pode enviar comandos
            command = json.loads(data)

            if command["action"] == "mark_read":
                # Marcar notificação como lida
                notification_id = command["notification_id"]
                mark_notification_as_read(db, notification_id, user.id)

                await websocket.send_json({
                    "type": "marked_read",
                    "notification_id": notification_id
                })

            elif command["action"] == "mark_all_read":
                # Marcar todas como lidas
                count = mark_all_notifications_as_read(db, user.id)

                await websocket.send_json({
                    "type": "marked_all_read",
                    "count": count
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
        logger.info(f"User {user.id} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user.id)
```

---

### 3. Criar e Enviar Notificações

```python
# services/notification_service.py
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Serviço para criar e enviar notificações"""

    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user_id: int,
        actor_id: int,
        notification_type: NotificationType,
        target_type: str,
        target_id: int,
        message: Optional[str] = None
    ) -> Notification:
        """
        Criar notificação no banco

        Regras:
        - Não criar se user_id == actor_id (não notificar a si mesmo)
        - Agrupar notificações similares recentes (aggregation)
        """

        # Não notificar a si mesmo
        if user_id == actor_id:
            return None

        # Verificar se já existe notificação similar recente (últimos 5 min)
        existing = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.target_type == target_type,
            Notification.target_id == target_id,
            Notification.created_at > datetime.utcnow() - timedelta(minutes=5)
        ).first()

        if existing:
            # Atualizar notificação existente ao invés de criar nova
            existing.created_at = datetime.utcnow()  # Bump timestamp
            self.db.commit()
            return existing

        # Criar notificação
        notification = Notification(
            user_id=user_id,
            actor_id=actor_id,
            type=notification_type,
            target_type=target_type,
            target_id=target_id,
            message=message or self._generate_message(notification_type, actor_id, target_type)
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        return notification

    def _generate_message(self, notification_type: NotificationType, actor_id: int, target_type: str) -> str:
        """Gerar mensagem da notificação"""
        actor = self.db.query(User).filter(User.id == actor_id).first()

        messages = {
            NotificationType.LIKE: f"{actor.username} curtiu seu {target_type}",
            NotificationType.COMMENT: f"{actor.username} comentou no seu {target_type}",
            NotificationType.REPLY: f"{actor.username} respondeu seu comentário",
            NotificationType.FOLLOW: f"{actor.username} começou a te seguir",
            NotificationType.MENTION: f"{actor.username} mencionou você"
        }

        return messages.get(notification_type, "Nova notificação")

    async def send_notification(self, notification: Notification):
        """
        Enviar notificação via WebSocket

        Se usuário não estiver conectado, notificação fica no banco
        Será enviada quando conectar
        """
        if manager.is_connected(notification.user_id):
            await manager.send_personal_message(
                {
                    "type": "new_notification",
                    "notification": serialize_notification(notification)
                },
                notification.user_id
            )
            logger.info(f"Notification sent to user {notification.user_id} via WebSocket")
        else:
            logger.info(f"User {notification.user_id} not connected. Notification saved to DB.")


# Helper: Criar notificação quando alguém dá like
async def notify_post_liked(post_id: int, liker_id: int, db: Session):
    """Notificar autor quando post recebe like"""
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        return

    service = NotificationService(db)
    notification = service.create_notification(
        user_id=post.user_id,  # Autor do post
        actor_id=liker_id,  # Quem deu like
        notification_type=NotificationType.LIKE,
        target_type="post",
        target_id=post_id
    )

    if notification:
        await service.send_notification(notification)


# Helper: Criar notificação quando alguém comenta
async def notify_post_commented(post_id: int, commenter_id: int, db: Session):
    """Notificar autor quando post recebe comentário"""
    post = db.query(Post).filter(Post.id == post_id).first()

    service = NotificationService(db)
    notification = service.create_notification(
        user_id=post.user_id,
        actor_id=commenter_id,
        notification_type=NotificationType.COMMENT,
        target_type="post",
        target_id=post_id
    )

    if notification:
        await service.send_notification(notification)


# Helper: Criar notificação quando alguém segue
async def notify_followed(followed_id: int, follower_id: int, db: Session):
    """Notificar usuário quando alguém o segue"""
    service = NotificationService(db)
    notification = service.create_notification(
        user_id=followed_id,
        actor_id=follower_id,
        notification_type=NotificationType.FOLLOW,
        target_type="user",
        target_id=follower_id
    )

    if notification:
        await service.send_notification(notification)
```

---

### 4. Integrar com Ações (Like, Comment, Follow)

```python
# routes/posts.py
@router.post("/{post_id}/like")
async def like_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dar like e notificar autor"""

    # Criar like
    service = LikeService(db)
    result = service.like_post(post_id, current_user.id)

    # Notificar autor (async, não bloqueia)
    await notify_post_liked(post_id, current_user.id, db)

    return result


@router.post("/{post_id}/comments")
async def create_comment(
    post_id: int,
    content: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Criar comentário e notificar autor"""

    # Criar comentário
    service = CommentService(db)
    comment = service.create_comment(post_id, current_user.id, content)

    # Notificar autor do post
    await notify_post_commented(post_id, current_user.id, db)

    return comment


@router.post("/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Seguir usuário e notificar"""

    # Criar follow
    follow = Follow(user_id=current_user.id, following_id=user_id)
    db.add(follow)
    db.commit()

    # Notificar usuário seguido
    await notify_followed(user_id, current_user.id, db)

    return {"following": True}
```

---

## 📊 Escalabilidade: Redis Pub/Sub

### Problema: Múltiplos Servidores

```
Server 1 (users: 1, 2, 3)     Server 2 (users: 4, 5, 6)
     │                              │
     └──────────────┬───────────────┘
                    │
               PostgreSQL

Se User 1 (Server 1) curte post de User 5 (Server 2):
❌ Server 1 não sabe que User 5 está no Server 2!
```

### Solução: Redis Pub/Sub

```python
# services/redis_pubsub.py
import redis.asyncio as aioredis
import json
import asyncio

redis_client = aioredis.from_url("redis://localhost:6379")


class RedisPubSubManager:
    """
    Usa Redis Pub/Sub para comunicar entre servidores

    Cada servidor:
    1. Subscribe ao canal "notifications"
    2. Quando cria notificação: publica no canal
    3. Quando recebe do canal: envia via WebSocket para usuários locais
    """

    def __init__(self):
        self.pubsub = None

    async def start(self):
        """Iniciar subscriber"""
        self.pubsub = redis_client.pubsub()
        await self.pubsub.subscribe("notifications")

        # Loop: processar mensagens
        asyncio.create_task(self._listen())

    async def _listen(self):
        """Escutar mensagens do Redis"""
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])

                user_id = data["user_id"]
                notification = data["notification"]

                # Se usuário está conectado NESTE servidor, enviar
                if manager.is_connected(user_id):
                    await manager.send_personal_message(
                        {
                            "type": "new_notification",
                            "notification": notification
                        },
                        user_id
                    )

    async def publish_notification(self, user_id: int, notification: dict):
        """Publicar notificação no canal Redis"""
        await redis_client.publish(
            "notifications",
            json.dumps({
                "user_id": user_id,
                "notification": notification
            })
        )


# Singleton
redis_pubsub = RedisPubSubManager()


# Atualizar NotificationService para usar Redis
class NotificationService:
    async def send_notification(self, notification: Notification):
        """Enviar notificação via Redis Pub/Sub"""

        # Publicar no Redis (todos os servidores receberão)
        await redis_pubsub.publish_notification(
            notification.user_id,
            serialize_notification(notification)
        )


# Inicializar no startup da aplicação
@app.on_event("startup")
async def startup():
    await redis_pubsub.start()
```

---

## 🔄 Fallback: Polling

```python
# routes/notifications.py
@router.get("/notifications")
def get_notifications(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Polling endpoint: buscar notificações

    Cliente que não suporta WebSocket pode fazer polling:
    setInterval(() => fetch('/notifications'), 5000)  // A cada 5s
    """

    notifications = db.query(Notification).options(
        joinedload(Notification.actor)
    ).filter(
        Notification.user_id == current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).offset(offset).limit(limit).all()

    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    return {
        "notifications": [serialize_notification(n) for n in notifications],
        "unread_count": unread_count
    }
```

---

## 📱 Push Notifications Mobile (FCM)

```python
# services/push_notification_service.py
from firebase_admin import messaging
import firebase_admin
from firebase_admin import credentials

# Inicializar Firebase
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)


class PushNotificationService:
    """
    Enviar push notifications para dispositivos móveis

    Requer FCM token do dispositivo (salvo ao fazer login no app)
    """

    def send_push(self, fcm_token: str, title: str, body: str, data: dict = None):
        """Enviar push notification via Firebase Cloud Messaging"""

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=fcm_token
        )

        try:
            response = messaging.send(message)
            logger.info(f"Push sent: {response}")
            return response
        except Exception as e:
            logger.error(f"Push failed: {e}")
            return None


# Integrar com NotificationService
class NotificationService:
    async def send_notification(self, notification: Notification):
        """Enviar via WebSocket + Push notification"""

        # 1. WebSocket (se conectado)
        await redis_pubsub.publish_notification(
            notification.user_id,
            serialize_notification(notification)
        )

        # 2. Push notification (se tem FCM token)
        user = self.db.query(User).filter(User.id == notification.user_id).first()

        if user.fcm_token:
            push_service = PushNotificationService()
            push_service.send_push(
                fcm_token=user.fcm_token,
                title="Nova notificação",
                body=notification.message,
                data={
                    "notification_id": str(notification.id),
                    "type": notification.type
                }
            )
```

---

## 🎨 Cliente JavaScript (Exemplo)

```javascript
// client.js
class NotificationClient {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${this.token}`);

    this.ws.onopen = () => {
      console.log('Connected to notifications');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'new_notification') {
        this.handleNotification(data.notification);
      } else if (data.type === 'initial_load') {
        this.handleInitialLoad(data.notifications, data.unread_count);
      }
    };

    this.ws.onclose = () => {
      console.log('Disconnected from notifications');
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

      console.log(`Reconnecting in ${delay}ms...`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnect attempts reached. Falling back to polling.');
      this.startPolling();
    }
  }

  handleNotification(notification) {
    // Mostrar toast notification
    this.showToast(notification.message);

    // Atualizar badge count
    this.updateBadgeCount();

    // Tocar som
    this.playNotificationSound();
  }

  markAsRead(notificationId) {
    this.ws.send(JSON.stringify({
      action: 'mark_read',
      notification_id: notificationId
    }));
  }

  markAllAsRead() {
    this.ws.send(JSON.stringify({
      action: 'mark_all_read'
    }));
  }

  startPolling() {
    // Fallback: polling a cada 10 segundos
    setInterval(async () => {
      const response = await fetch('/notifications?limit=10');
      const data = await response.json();

      // Processar notificações
      data.notifications.forEach(n => this.handleNotification(n));
    }, 10000);
  }
}

// Uso
const token = localStorage.getItem('jwt_token');
const notificationClient = new NotificationClient(token);
notificationClient.connect();
```

---

## 📊 Comparação de Estratégias

| Estratégia | Latência | Escalabilidade | Bateria (Mobile) | Implementação |
|------------|----------|----------------|------------------|---------------|
| **WebSocket** | ~10ms | Alta (Redis Pub/Sub) | ⚠️ Média | Complexa |
| **SSE** | ~50ms | Média | ⚠️ Média | Média |
| **Long Polling** | ~100ms | Baixa | ❌ Alta | Simples |
| **Regular Polling** | ~5s | Baixa | ❌ Muito Alta | Muito Simples |
| **Push Notifications** | ~1s | Alta | ✅ Baixa | Complexa (requer FCM/APNs) |

---

## 🎯 Conceitos Aprendidos

1. ✅ **WebSocket**: Conexões bidirecionais persistentes
2. ✅ **Connection pooling**: Múltiplas conexões por usuário
3. ✅ **Redis Pub/Sub**: Comunicação entre servidores
4. ✅ **Graceful degradation**: Fallback para polling
5. ✅ **Notification aggregation**: Agrupar notificações similares
6. ✅ **Push notifications**: FCM para mobile
7. ✅ **Reconnection logic**: Exponential backoff
8. ✅ **Read receipts**: Marcar como lida

---

## 📚 Próximos Passos

- **Exercício 09**: Search com Elasticsearch
- **Exercício 10**: Testing completo (unit, integration, e2e)
- **Exercício 11**: CI/CD e deploy

---

**Suas notificações estão em tempo real! 🔔⚡**
