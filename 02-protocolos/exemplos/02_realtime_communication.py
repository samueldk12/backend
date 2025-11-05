"""
Exemplo 02: Comunicação em Tempo Real

Demonstra 3 formas de comunicação em tempo real:
1. WebSocket (bidirecional, full-duplex)
2. Server-Sent Events (SSE) (unidirecional, servidor → cliente)
3. Long Polling (request-response com espera)

Caso de uso: Sistema de notificações em tempo real
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
import asyncio
import json
import time
from datetime import datetime
from collections import deque

# ============================================================================
# MODELS
# ============================================================================

class Notification(BaseModel):
    id: int
    user_id: int
    message: str
    type: str  # "info", "warning", "success"
    timestamp: str

# ============================================================================
# STORAGE (In-memory para demonstração)
# ============================================================================

# Notificações por usuário
notifications_queue: Dict[int, deque] = {}

# Conexões WebSocket ativas
active_websockets: Dict[int, List[WebSocket]] = {}

# Para long polling: armazenar última verificação
last_poll_time: Dict[int, float] = {}

# Contador de notificações
notification_id = 0

def add_notification(user_id: int, message: str, type: str = "info"):
    """Adiciona notificação para um usuário."""
    global notification_id
    notification_id += 1

    notification = Notification(
        id=notification_id,
        user_id=user_id,
        message=message,
        type=type,
        timestamp=datetime.now().isoformat()
    )

    # Adicionar à fila do usuário
    if user_id not in notifications_queue:
        notifications_queue[user_id] = deque(maxlen=100)
    notifications_queue[user_id].append(notification)

    return notification

# ============================================================================
# 1. WEBSOCKET (Bidirecional, Conexão Persistente)
# ============================================================================

app_websocket = FastAPI(title="WebSocket Example")

class WebSocketConnectionManager:
    """Gerencia conexões WebSocket."""

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Aceita nova conexão."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"✅ WebSocket: User {user_id} connected")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove conexão."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"❌ WebSocket: User {user_id} disconnected")

    async def send_personal_message(self, message: str, user_id: int):
        """Envia mensagem para um usuário específico."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(message)

    async def broadcast(self, message: str):
        """Envia mensagem para todos os usuários."""
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                await connection.send_text(message)

manager = WebSocketConnectionManager()

@app_websocket.websocket("/ws/notifications/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint para notificações em tempo real.

    Características:
    - Conexão persistente e bidirecional
    - Servidor e cliente podem enviar mensagens a qualquer momento
    - Latência muito baixa (~1-5ms)
    - Ideal para: chat, gaming, collaborative editing
    """
    await manager.connect(websocket, user_id)

    try:
        # Enviar notificações antigas
        if user_id in notifications_queue:
            for notif in notifications_queue[user_id]:
                await websocket.send_json(notif.dict())

        # Loop: receber mensagens do cliente
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Cliente pode enviar ações
            if message.get("action") == "mark_read":
                notif_id = message.get("notification_id")
                await websocket.send_json({
                    "status": "success",
                    "message": f"Notification {notif_id} marked as read"
                })

            elif message.get("action") == "ping":
                # Heartbeat para manter conexão viva
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app_websocket.post("/trigger-notification/{user_id}")
async def trigger_notification(user_id: int, message: str):
    """
    Trigger de notificação (para teste).
    Envia notificação via WebSocket imediatamente.
    """
    notification = add_notification(user_id, message)

    # Enviar via WebSocket
    await manager.send_personal_message(
        json.dumps(notification.dict()),
        user_id
    )

    return {"status": "sent", "notification": notification}

# ============================================================================
# 2. SERVER-SENT EVENTS (SSE) (Unidirecional, Servidor → Cliente)
# ============================================================================

app_sse = FastAPI(title="SSE Example")

async def notification_stream(user_id: int):
    """
    Generator que produz eventos de notificações.

    SSE usa formato específico:
    data: {json}\\n\\n
    """
    # Enviar notificações antigas
    if user_id in notifications_queue:
        for notif in notifications_queue[user_id]:
            yield f"data: {json.dumps(notif.dict())}\n\n"

    # Stream de novas notificações
    while True:
        # Verificar novas notificações a cada 1s
        await asyncio.sleep(1)

        if user_id in notifications_queue and notifications_queue[user_id]:
            # Pegar última notificação
            notif = notifications_queue[user_id][-1]
            yield f"data: {json.dumps(notif.dict())}\n\n"

        # Heartbeat (manter conexão viva)
        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"

@app_sse.get("/sse/notifications/{user_id}")
async def sse_endpoint(user_id: int):
    """
    SSE endpoint para notificações.

    Características:
    - Conexão persistente, mas unidirecional (servidor → cliente)
    - Cliente não pode enviar dados pelo stream (usa HTTP normal para isso)
    - Reconexão automática se cair
    - Event IDs para retomar de onde parou
    - Ideal para: feeds de atualizações, dashboards, live scores

    Uso no frontend (JavaScript):
    ```javascript
    const eventSource = new EventSource('/sse/notifications/123');
    eventSource.onmessage = (event) => {
        const notification = JSON.parse(event.data);
        console.log('Nova notificação:', notification);
    };
    ```
    """
    return StreamingResponse(
        notification_stream(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

@app_sse.post("/trigger-notification-sse/{user_id}")
async def trigger_notification_sse(user_id: int, message: str):
    """Trigger de notificação para SSE."""
    notification = add_notification(user_id, message)
    return {"status": "queued", "notification": notification}

# ============================================================================
# 3. LONG POLLING (Request-Response com Espera)
# ============================================================================

app_polling = FastAPI(title="Long Polling Example")

@app_polling.get("/poll/notifications/{user_id}")
async def long_poll_endpoint(user_id: int, timeout: int = 30):
    """
    Long Polling endpoint.

    Características:
    - Cliente faz request HTTP normal
    - Servidor "segura" a request até ter dados (ou timeout)
    - Cliente recebe resposta e imediatamente faz nova request
    - Funciona em qualquer ambiente (apenas HTTP)
    - Ideal para: ambientes com restrições, fallback

    Fluxo:
    1. Cliente → Servidor: GET /poll/notifications/123
    2. Servidor espera até ter notificação (max 30s)
    3. Servidor → Cliente: Resposta com notificações
    4. Cliente imediatamente faz nova request (volta ao passo 1)
    """
    start_time = time.time()
    last_check = last_poll_time.get(user_id, 0)

    # Esperar por novas notificações (max timeout segundos)
    while time.time() - start_time < timeout:
        # Verificar se há notificações novas
        if user_id in notifications_queue:
            queue = notifications_queue[user_id]
            # Filtrar notificações novas (timestamp > last_check)
            new_notifications = [
                n for n in queue
                if datetime.fromisoformat(n.timestamp).timestamp() > last_check
            ]

            if new_notifications:
                last_poll_time[user_id] = time.time()
                return {
                    "notifications": new_notifications,
                    "has_more": False
                }

        # Aguardar 1s antes de verificar novamente
        await asyncio.sleep(1)

    # Timeout: retornar vazio
    return {
        "notifications": [],
        "has_more": False
    }

@app_polling.post("/trigger-notification-poll/{user_id}")
async def trigger_notification_poll(user_id: int, message: str):
    """Trigger de notificação para long polling."""
    notification = add_notification(user_id, message)
    return {"status": "queued", "notification": notification}

# ============================================================================
# COMPARAÇÃO
# ============================================================================

def comparacao():
    """Comparação detalhada das abordagens."""
    print("\n" + "=" * 70)
    print("COMPARAÇÃO: WebSocket vs SSE vs Long Polling")
    print("=" * 70)

    print("""
┌──────────────────────────────────────────────────────────────────────┐
│                          WEBSOCKET                                   │
├──────────────────────────────────────────────────────────────────────┤
│ Conexão: Persistente, bidirecional (full-duplex)                    │
│ Protocolo: ws:// ou wss:// (upgrade de HTTP)                        │
│ Latência: Muito baixa (1-5ms)                                       │
│ Overhead: Baixo após handshake inicial                              │
│                                                                      │
│ ✅ Vantagens:                                                        │
│   • Bidirecional (servidor ↔ cliente)                               │
│   • Latência mínima                                                 │
│   • Eficiente (mensagens binárias)                                  │
│   • Ideal para interação em tempo real                             │
│                                                                      │
│ ❌ Desvantagens:                                                     │
│   • Mais complexo de implementar                                    │
│   • Requer suporte especial em proxies/load balancers              │
│   • Problemas com alguns firewalls corporativos                     │
│   • Stateful (complica escalabilidade)                             │
│                                                                      │
│ 🎯 Casos de uso:                                                    │
│   • Chat em tempo real                                              │
│   • Gaming online (multiplayer)                                     │
│   • Collaborative editing (Google Docs style)                       │
│   • Trading platforms                                               │
│   • IoT dashboards                                                  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    SERVER-SENT EVENTS (SSE)                          │
├──────────────────────────────────────────────────────────────────────┤
│ Conexão: Persistente, unidirecional (servidor → cliente)            │
│ Protocolo: HTTP (text/event-stream)                                 │
│ Latência: Baixa (5-10ms)                                            │
│ Overhead: Médio                                                      │
│                                                                      │
│ ✅ Vantagens:                                                        │
│   • Simples (HTTP puro)                                             │
│   • Reconexão automática                                            │
│   • Event IDs (pode retomar de onde parou)                          │
│   • Funciona em qualquer ambiente HTTP                             │
│   • Suporte nativo em browsers                                      │
│                                                                      │
│ ❌ Desvantagens:                                                     │
│   • Apenas servidor → cliente (unidirecional)                       │
│   • Cliente precisa usar HTTP normal para enviar dados             │
│   • Limitações de conexões simultâneas em browsers                  │
│   • Apenas texto (não suporta binário)                             │
│                                                                      │
│ 🎯 Casos de uso:                                                    │
│   • Feeds de notificações                                           │
│   • Live dashboards / metrics                                       │
│   • Live scores / sports updates                                    │
│   • Stock tickers                                                   │
│   • Log streaming                                                   │
│   • Progresso de tarefas longas                                     │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                         LONG POLLING                                 │
├──────────────────────────────────────────────────────────────────────┤
│ Conexão: Request-response com espera                                │
│ Protocolo: HTTP normal (GET/POST)                                   │
│ Latência: Média (50-100ms + tempo de espera)                        │
│ Overhead: Alto (muitas requisições)                                 │
│                                                                      │
│ ✅ Vantagens:                                                        │
│   • Funciona em QUALQUER ambiente                                   │
│   • Simples de implementar                                          │
│   • Não requer suporte especial de infraestrutura                   │
│   • Stateless (fácil de escalar)                                    │
│   • Compatível com todos os browsers                                │
│                                                                      │
│ ❌ Desvantagens:                                                     │
│   • Overhead alto (nova request a cada resposta)                    │
│   • Latência maior                                                  │
│   • Consome mais recursos (servidor e rede)                         │
│   • Menos eficiente                                                 │
│                                                                      │
│ 🎯 Casos de uso:                                                    │
│   • Fallback quando WebSocket/SSE não disponíveis                   │
│   • Ambientes com restrições (firewalls corporativos)              │
│   • Polling de status de jobs                                       │
│   • Notificações não-críticas                                       │
└──────────────────────────────────────────────────────────────────────┘
    """)

def comparacao_performance():
    """Comparação de performance."""
    print("\n" + "=" * 70)
    print("PERFORMANCE E RECURSOS")
    print("=" * 70)

    print("""
┌──────────────────┬──────────────┬──────────────┬──────────────┐
│ Métrica          │ WebSocket    │ SSE          │ Long Polling │
├──────────────────┼──────────────┼──────────────┼──────────────┤
│ Latência         │ 1-5ms        │ 5-10ms       │ 50-200ms     │
│ Overhead/msg     │ 2-6 bytes    │ ~10 bytes    │ 500-1000 b   │
│ Conexões simult. │ Milhares     │ ~100/browser │ Ilimitado    │
│ CPU (servidor)   │ Baixo        │ Médio        │ Alto         │
│ Banda (1000 msg) │ ~2KB         │ ~10KB        │ ~500KB       │
│ Complexidade     │ Alta         │ Média        │ Baixa        │
└──────────────────┴──────────────┴──────────────┴──────────────┘

📊 EXEMPLO PRÁTICO: 1000 notificações/hora

WebSocket:
  • 1 conexão persistente
  • ~2KB de dados
  • CPU: ~5% de 1 core

SSE:
  • 1 conexão persistente
  • ~10KB de dados
  • CPU: ~10% de 1 core

Long Polling:
  • 1000 requisições HTTP
  • ~500KB de dados
  • CPU: ~30% de 1 core

🎯 VENCEDOR: WebSocket (5x mais eficiente)
    """)

def estrategia_progressive_enhancement():
    """Estratégia de fallback."""
    print("\n" + "=" * 70)
    print("ESTRATÉGIA: PROGRESSIVE ENHANCEMENT")
    print("=" * 70)

    print("""
Implementar fallback automático para máxima compatibilidade:

┌─────────────────────────────────────────────────────────────┐
│                    TENTATIVA 1: WebSocket                    │
│                           ↓                                  │
│                   (não disponível?)                          │
│                           ↓                                  │
│                    TENTATIVA 2: SSE                          │
│                           ↓                                  │
│                   (não disponível?)                          │
│                           ↓                                  │
│                  FALLBACK: Long Polling                      │
└─────────────────────────────────────────────────────────────┘

Código de exemplo (JavaScript):

```javascript
class RealtimeConnection {
  constructor(userId) {
    this.userId = userId;
    this.connect();
  }

  async connect() {
    // Tentar WebSocket
    try {
      this.ws = new WebSocket(`ws://localhost:8000/ws/notifications/${this.userId}`);
      this.ws.onmessage = (event) => this.handleMessage(JSON.parse(event.data));
      this.ws.onerror = () => this.fallbackToSSE();
      console.log('✅ Conectado via WebSocket');
      return;
    } catch (e) {
      console.log('❌ WebSocket falhou, tentando SSE...');
    }

    // Fallback: SSE
    try {
      this.eventSource = new EventSource(`/sse/notifications/${this.userId}`);
      this.eventSource.onmessage = (event) => this.handleMessage(JSON.parse(event.data));
      this.eventSource.onerror = () => this.fallbackToPolling();
      console.log('✅ Conectado via SSE');
      return;
    } catch (e) {
      console.log('❌ SSE falhou, usando Long Polling...');
    }

    // Fallback final: Long Polling
    this.startPolling();
  }

  async startPolling() {
    while (true) {
      try {
        const response = await fetch(`/poll/notifications/${this.userId}`);
        const data = await response.json();
        data.notifications.forEach(n => this.handleMessage(n));
        console.log('✅ Polling ativo');
      } catch (e) {
        await new Promise(r => setTimeout(r, 5000));
      }
    }
  }

  handleMessage(notification) {
    console.log('Nova notificação:', notification);
    // Atualizar UI
  }
}

// Uso
const connection = new RealtimeConnection(123);
```

✅ Benefícios:
  • Usa a melhor tecnologia disponível
  • Fallback automático
  • Funciona em qualquer ambiente
  • Progressive enhancement
    """)

# ============================================================================
# ÁRVORE DE DECISÃO
# ============================================================================

def arvore_decisao():
    """Árvore de decisão para escolher tecnologia."""
    print("\n" + "=" * 70)
    print("ÁRVORE DE DECISÃO")
    print("=" * 70)

    print("""
Seu caso de uso:

┌─ Precisa de comunicação bidirecional?
│  └─ SIM → WebSocket ✅
│     • Chat
│     • Gaming online
│     • Collaborative editing
│
└─ NÃO → Apenas servidor → cliente?
   │
   ├─ Alta frequência de updates (>1/s)?
   │  └─ SIM → WebSocket ou SSE ✅
   │     • Live dashboards
   │     • Real-time analytics
   │
   ├─ Baixa frequência (<1/min)?
   │  └─ SIM → Long Polling ✅
   │     • Notificações ocasionais
   │     • Status polling
   │
   ├─ Ambiente com restrições (firewall, proxy)?
   │  └─ SIM → Long Polling (fallback) ✅
   │
   └─ Reconexão automática importante?
      └─ SIM → SSE ✅
         • Feeds contínuos
         • Event streams

🎯 RECOMENDAÇÃO GERAL:

1. Aplicações modernas → WebSocket (com fallback SSE/Polling)
2. Feeds unidirecionais → SSE
3. Ambientes restritos → Long Polling
4. Chat/Gaming → WebSocket (apenas)
5. Dashboards → SSE ou WebSocket
    """)

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("COMUNICAÇÃO EM TEMPO REAL: WebSocket vs SSE vs Long Polling")
    print("=" * 70)

    comparacao()
    comparacao_performance()
    estrategia_progressive_enhancement()
    arvore_decisao()

    print("\n" + "=" * 70)
    print("RESUMO EXECUTIVO")
    print("=" * 70)
    print("""
🏆 VENCEDORES POR CATEGORIA:

Latência           → WebSocket (1-5ms)
Simplicidade       → SSE (HTTP puro)
Compatibilidade    → Long Polling (funciona sempre)
Eficiência         → WebSocket (menos overhead)
Bidirecional       → WebSocket (único)
Reconexão auto     → SSE (nativo)

💡 RECOMENDAÇÃO:

Para PRODUÇÃO: Implemente os 3 com progressive enhancement
Para PROTOTIPAGEM: Comece com SSE (mais simples)
Para APPS MODERNOS: WebSocket (com fallback)

📚 PARA RODAR OS EXEMPLOS:

# Terminal 1 - WebSocket
uvicorn 02_realtime_communication:app_websocket --port 8000

# Terminal 2 - SSE
uvicorn 02_realtime_communication:app_sse --port 8001

# Terminal 3 - Long Polling
uvicorn 02_realtime_communication:app_polling --port 8002

# Testar (em outro terminal):
# WebSocket:
curl -X POST "http://localhost:8000/trigger-notification/123?message=Hello"

# SSE:
curl "http://localhost:8001/sse/notifications/123"

# Long Polling:
curl "http://localhost:8002/poll/notifications/123"
    """)


if __name__ == "__main__":
    main()
