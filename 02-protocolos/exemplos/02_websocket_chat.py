"""
Exemplo: Chat em Tempo Real com WebSocket

Execute: uvicorn 02_websocket_chat:app --reload
Acesse: http://localhost:8000 (abre o cliente HTML)

Teste com múltiplas abas para simular vários usuários!
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List, Dict
from datetime import datetime
import json
import uvicorn

app = FastAPI(title="WebSocket Chat")


# ============================================
# CONNECTION MANAGER
# ============================================

class ConnectionManager:
    """
    Gerencia conexões WebSocket ativas
    """
    def __init__(self):
        # Lista de conexões ativas
        self.active_connections: List[WebSocket] = []
        # Mapa user_id -> WebSocket
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Aceita nova conexão"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket

        print(f"✅ User {user_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove conexão"""
        self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]

        print(f"❌ User {user_id} disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Envia mensagem para um usuário específico"""
        await websocket.send_text(message)

    async def broadcast(self, message: str, exclude: WebSocket = None):
        """
        Broadcast para todos os usuários conectados
        Opcionalmente exclui o sender
        """
        for connection in self.active_connections:
            if connection != exclude:
                await connection.send_text(message)

    async def send_to_user(self, user_id: str, message: str):
        """Envia mensagem para user específico por ID"""
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_text(message)


manager = ConnectionManager()


# ============================================
# WEBSOCKET ENDPOINT
# ============================================

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint para chat

    Args:
        user_id: ID único do usuário
    """
    await manager.connect(websocket, user_id)

    # Notifica outros usuários
    await manager.broadcast(
        json.dumps({
            "type": "user_joined",
            "user_id": user_id,
            "message": f"{user_id} entrou no chat",
            "timestamp": datetime.now().isoformat(),
            "online_users": len(manager.active_connections)
        }),
        exclude=websocket
    )

    try:
        while True:
            # Recebe mensagem do cliente
            data = await websocket.receive_text()

            # Parse message
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")

                if message_type == "message":
                    # Mensagem normal - broadcast para todos
                    response = {
                        "type": "message",
                        "user_id": user_id,
                        "message": message_data.get("message", ""),
                        "timestamp": datetime.now().isoformat()
                    }

                    # Broadcast incluindo o sender
                    await manager.broadcast(json.dumps(response))

                elif message_type == "private":
                    # Mensagem privada para usuário específico
                    target_user = message_data.get("to")
                    response = {
                        "type": "private",
                        "from": user_id,
                        "message": message_data.get("message", ""),
                        "timestamp": datetime.now().isoformat()
                    }

                    # Envia para destinatário
                    await manager.send_to_user(target_user, json.dumps(response))

                    # Confirma para sender
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "private_sent",
                            "to": target_user,
                            "message": message_data.get("message", ""),
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )

                elif message_type == "typing":
                    # Usuário está digitando
                    await manager.broadcast(
                        json.dumps({
                            "type": "typing",
                            "user_id": user_id,
                            "timestamp": datetime.now().isoformat()
                        }),
                        exclude=websocket
                    )

            except json.JSONDecodeError:
                # Mensagem de texto simples (backward compatibility)
                response = {
                    "type": "message",
                    "user_id": user_id,
                    "message": data,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast(json.dumps(response))

    except WebSocketDisconnect:
        # Cliente desconectou
        manager.disconnect(websocket, user_id)

        # Notifica outros usuários
        await manager.broadcast(
            json.dumps({
                "type": "user_left",
                "user_id": user_id,
                "message": f"{user_id} saiu do chat",
                "timestamp": datetime.now().isoformat(),
                "online_users": len(manager.active_connections)
            })
        )


# ============================================
# HTTP ENDPOINT (CLIENTE HTML)
# ============================================

@app.get("/")
def get_client():
    """Retorna cliente HTML para o chat"""
    return HTMLResponse(HTML_CLIENT)


@app.get("/health")
def health():
    """Health check"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "users": list(manager.user_connections.keys())
    }


# ============================================
# HTML CLIENT
# ============================================

HTML_CLIENT = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 800px;
            height: 600px;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px 15px 0 0;
        }

        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { opacity: 0.9; font-size: 14px; }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f7f9fc;
        }

        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 10px;
            max-width: 70%;
            word-wrap: break-word;
        }

        .message.mine {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
        }

        .message.other {
            background: white;
            border: 1px solid #e0e0e0;
        }

        .message.system {
            background: #fffbea;
            border: 1px solid #ffe58f;
            color: #8c8c8c;
            margin-left: auto;
            margin-right: auto;
            text-align: center;
            max-width: 90%;
        }

        .message-header {
            font-size: 12px;
            opacity: 0.7;
            margin-bottom: 5px;
        }

        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
            border-radius: 0 0 15px 15px;
        }

        .input-row {
            display: flex;
            gap: 10px;
        }

        input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }

        input:focus { border-color: #667eea; }

        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }

        button:hover { transform: translateY(-2px); }
        button:active { transform: translateY(0); }

        #status {
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 600;
        }

        .connected { background: #52c41a; color: white; }
        .disconnected { background: #ff4d4f; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 WebSocket Chat</h1>
            <p id="info">Conectando...</p>
            <span id="status" class="disconnected">Offline</span>
        </div>

        <div class="messages" id="messages"></div>

        <div class="input-area">
            <div class="input-row">
                <input type="text" id="userInput" placeholder="Seu nome de usuário" />
                <button onclick="connect()">Conectar</button>
            </div>
            <div class="input-row" style="margin-top: 10px;">
                <input type="text" id="messageInput" placeholder="Digite sua mensagem..." disabled />
                <button onclick="sendMessage()" id="sendBtn" disabled>Enviar</button>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let userId = null;

        function connect() {
            userId = document.getElementById("userInput").value.trim();
            if (!userId) {
                alert("Por favor, digite seu nome de usuário");
                return;
            }

            // Connect to WebSocket
            ws = new WebSocket(`ws://localhost:8000/ws/${userId}`);

            ws.onopen = () => {
                document.getElementById("status").textContent = "Online";
                document.getElementById("status").className = "connected";
                document.getElementById("info").textContent = `Conectado como ${userId}`;
                document.getElementById("messageInput").disabled = false;
                document.getElementById("sendBtn").disabled = false;
                document.getElementById("userInput").disabled = true;
                addSystemMessage("Conectado ao chat!");
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === "message") {
                    addMessage(data.user_id, data.message, data.user_id === userId);
                } else if (data.type === "user_joined" || data.type === "user_left") {
                    addSystemMessage(data.message + ` (${data.online_users} online)`);
                } else if (data.type === "private") {
                    addMessage(`${data.from} (privado)`, data.message, false);
                }
            };

            ws.onclose = () => {
                document.getElementById("status").textContent = "Offline";
                document.getElementById("status").className = "disconnected";
                document.getElementById("info").textContent = "Desconectado";
                document.getElementById("messageInput").disabled = true;
                document.getElementById("sendBtn").disabled = true;
                addSystemMessage("Desconectado do chat");
            };
        }

        function sendMessage() {
            const input = document.getElementById("messageInput");
            const message = input.value.trim();

            if (message && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: "message",
                    message: message
                }));
                input.value = "";
            }
        }

        function addMessage(user, text, isMine) {
            const messagesDiv = document.getElementById("messages");
            const messageDiv = document.createElement("div");
            messageDiv.className = `message ${isMine ? 'mine' : 'other'}`;

            const header = document.createElement("div");
            header.className = "message-header";
            header.textContent = user;

            const content = document.createElement("div");
            content.textContent = text;

            messageDiv.appendChild(header);
            messageDiv.appendChild(content);
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function addSystemMessage(text) {
            const messagesDiv = document.getElementById("messages");
            const messageDiv = document.createElement("div");
            messageDiv.className = "message system";
            messageDiv.textContent = text;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // Enter to send
        document.getElementById("messageInput").addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendMessage();
        });

        document.getElementById("userInput").addEventListener("keypress", (e) => {
            if (e.key === "Enter") connect();
        });
    </script>
</body>
</html>
"""


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("💬 WebSocket Chat Example")
    print("=" * 60)
    print()
    print("🌐 Abra seu navegador em: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print()
    print("💡 Dica: Abra múltiplas abas para simular vários usuários!")
    print()
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
