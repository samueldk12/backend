"""
Módulo 06 - Filas e Streaming: Comparação de Message Queues

Este exemplo mostra implementações reais de:
1. Celery com Redis (task queue mais popular)
2. RabbitMQ com pika (message broker robusto)
3. Comparação de padrões (publish/subscribe, fanout, direct)
4. Idempotência e retry strategies
5. Dead Letter Queue (DLQ)

Execute:
    # Terminal 1: Inicie o Redis
    docker run -d -p 6379:6379 redis:alpine

    # Terminal 2: Inicie o worker Celery
    celery -A 01_message_queues_comparison:celery_app worker --loglevel=info

    # Terminal 3: Execute o script
    python 01_message_queues_comparison.py
"""

import time
import json
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# EXEMPLO 1: Celery com Redis (Mais Usado em Python)
# ============================================================================

from celery import Celery, Task
from celery.exceptions import Retry

# Configuração do Celery
celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',  # Onde ficam as filas
    backend='redis://localhost:6379/1'  # Onde ficam os resultados
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo',
    enable_utc=True,

    # Configurações importantes
    task_acks_late=True,  # Confirma task só após completar (não ao receber)
    worker_prefetch_multiplier=1,  # Pega 1 task por vez (melhor distribuição)
    task_reject_on_worker_lost=True,  # Rejeita task se worker morrer
)


# ----------------------------------------------------------------------------
# Task Simples
# ----------------------------------------------------------------------------

@celery_app.task(name='tasks.send_email')
def send_email(to: str, subject: str, body: str):
    """
    Task simples: enviar email

    Características:
    - Assíncrona: retorna imediatamente
    - Worker processa em background
    - Retry automático em caso de falha
    """
    logger.info(f"📧 Enviando email para {to}: {subject}")
    time.sleep(2)  # Simula envio
    logger.info(f"✅ Email enviado para {to}")
    return {"status": "sent", "to": to}


# ----------------------------------------------------------------------------
# Task com Retry e Exponential Backoff
# ----------------------------------------------------------------------------

@celery_app.task(
    name='tasks.fetch_external_api',
    bind=True,  # Permite acessar self (task instance)
    max_retries=5,
    default_retry_delay=60  # 1 minuto
)
def fetch_external_api(self, url: str):
    """
    Task com retry strategy

    Retry com exponential backoff:
    - Tentativa 1: imediato
    - Tentativa 2: 2^1 = 2 segundos
    - Tentativa 3: 2^2 = 4 segundos
    - Tentativa 4: 2^3 = 8 segundos
    - Tentativa 5: 2^4 = 16 segundos
    """
    try:
        logger.info(f"🌐 Fetching {url} (tentativa {self.request.retries + 1}/5)")

        # Simula falha intermitente (50% de chance)
        import random
        if random.random() < 0.5:
            raise ConnectionError("API temporariamente indisponível")

        # Simula sucesso
        time.sleep(1)
        logger.info(f"✅ API fetch successful: {url}")
        return {"url": url, "status": "success"}

    except ConnectionError as exc:
        # Exponential backoff: 2^retry_count
        countdown = 2 ** self.request.retries
        logger.warning(f"⚠️  Tentativa {self.request.retries + 1} falhou. Retry em {countdown}s")

        # Raise Retry exception
        raise self.retry(exc=exc, countdown=countdown)


# ----------------------------------------------------------------------------
# Task com Idempotência (Executar múltiplas vezes = mesmo resultado)
# ----------------------------------------------------------------------------

from redis import Redis
redis_client = Redis(host='localhost', port=6379, decode_responses=True)

@celery_app.task(name='tasks.process_payment')
def process_payment(payment_id: str, amount: float):
    """
    Task idempotente: pode executar múltiplas vezes sem problemas

    Idempotência garante que:
    - Se task for re-executada (ex: worker crash), não causa duplicação
    - Usa Redis para rastrear payments já processados
    """
    lock_key = f"payment:lock:{payment_id}"

    # Tentar adquirir lock (SETNX = SET if Not eXists)
    acquired = redis_client.set(lock_key, "processing", nx=True, ex=300)  # 5min TTL

    if not acquired:
        logger.warning(f"⚠️  Payment {payment_id} já está sendo processado")
        return {"status": "duplicate", "payment_id": payment_id}

    try:
        logger.info(f"💳 Processando pagamento {payment_id}: R${amount}")
        time.sleep(2)  # Simula processamento

        # Salvar resultado
        redis_client.set(f"payment:result:{payment_id}", "success", ex=86400)  # 24h

        logger.info(f"✅ Pagamento {payment_id} processado com sucesso")
        return {"status": "success", "payment_id": payment_id, "amount": amount}

    finally:
        # Liberar lock
        redis_client.delete(lock_key)


# ----------------------------------------------------------------------------
# Task Chain: Encadear tasks (output de uma vira input da outra)
# ----------------------------------------------------------------------------

@celery_app.task(name='tasks.download_video')
def download_video(video_url: str) -> str:
    """Passo 1: Baixar vídeo"""
    logger.info(f"⬇️  Baixando vídeo: {video_url}")
    time.sleep(2)
    video_path = f"/tmp/video_{int(time.time())}.mp4"
    logger.info(f"✅ Vídeo baixado: {video_path}")
    return video_path


@celery_app.task(name='tasks.encode_video')
def encode_video(video_path: str) -> str:
    """Passo 2: Encodar vídeo"""
    logger.info(f"🎬 Encodando vídeo: {video_path}")
    time.sleep(3)
    encoded_path = video_path.replace(".mp4", "_encoded.mp4")
    logger.info(f"✅ Vídeo encodado: {encoded_path}")
    return encoded_path


@celery_app.task(name='tasks.upload_to_cdn')
def upload_to_cdn(encoded_path: str) -> str:
    """Passo 3: Upload para CDN"""
    logger.info(f"☁️  Fazendo upload: {encoded_path}")
    time.sleep(2)
    cdn_url = f"https://cdn.example.com/{encoded_path.split('/')[-1]}"
    logger.info(f"✅ Upload completo: {cdn_url}")
    return cdn_url


@celery_app.task(name='tasks.notify_user')
def notify_user(cdn_url: str, user_id: int):
    """Passo 4: Notificar usuário"""
    logger.info(f"🔔 Notificando usuário {user_id}: vídeo disponível em {cdn_url}")
    time.sleep(1)
    logger.info(f"✅ Usuário {user_id} notificado")
    return {"status": "notified", "user_id": user_id, "cdn_url": cdn_url}


# ----------------------------------------------------------------------------
# Exemplos de Uso
# ----------------------------------------------------------------------------

def exemplo_celery_basico():
    """Exemplo 1: Task assíncrona simples"""
    print("\n" + "="*70)
    print("EXEMPLO 1: Task Assíncrona Simples")
    print("="*70)

    # Enviar task para fila (retorna imediatamente)
    result = send_email.delay("joao@example.com", "Bem-vindo", "Olá João!")

    print(f"Task enviada! Task ID: {result.id}")
    print(f"Estado inicial: {result.state}")  # PENDING

    # Aguardar resultado (bloqueante)
    print("Aguardando conclusão...")
    output = result.get(timeout=10)
    print(f"Resultado: {output}")
    print(f"Estado final: {result.state}")  # SUCCESS


def exemplo_celery_retry():
    """Exemplo 2: Task com retry"""
    print("\n" + "="*70)
    print("EXEMPLO 2: Task com Retry e Exponential Backoff")
    print("="*70)

    result = fetch_external_api.delay("https://api.example.com/data")
    print(f"Task enviada! Task ID: {result.id}")

    try:
        output = result.get(timeout=30)
        print(f"✅ Sucesso: {output}")
    except Exception as e:
        print(f"❌ Falha após retries: {e}")


def exemplo_celery_idempotencia():
    """Exemplo 3: Task idempotente"""
    print("\n" + "="*70)
    print("EXEMPLO 3: Idempotência (executar 2x = mesmo resultado)")
    print("="*70)

    payment_id = "PAY-123456"

    # Enviar task 2 vezes (simula retry acidental)
    result1 = process_payment.delay(payment_id, 100.00)
    result2 = process_payment.delay(payment_id, 100.00)  # Duplicata!

    print(f"Task 1: {result1.get()}")
    print(f"Task 2: {result2.get()}")  # Deve detectar duplicata


def exemplo_celery_chain():
    """Exemplo 4: Chain de tasks (pipeline)"""
    print("\n" + "="*70)
    print("EXEMPLO 4: Chain de Tasks (Pipeline)")
    print("="*70)

    from celery import chain

    # Chain: download -> encode -> upload -> notify
    # Output de cada task vira input da próxima
    workflow = chain(
        download_video.s("https://example.com/video.mp4"),
        encode_video.s(),  # Recebe output de download_video
        upload_to_cdn.s(),  # Recebe output de encode_video
        notify_user.s(user_id=123)  # Recebe output de upload_to_cdn
    )

    result = workflow.apply_async()
    print(f"Workflow iniciado! Task ID: {result.id}")

    print("Processando... (pode demorar ~10s)")
    final_result = result.get(timeout=20)
    print(f"✅ Workflow completo: {final_result}")


# ============================================================================
# EXEMPLO 2: Dead Letter Queue (DLQ)
# ============================================================================

@celery_app.task(
    name='tasks.risky_task',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def risky_task(self, data: dict):
    """
    Task que pode falhar permanentemente

    Se falhar após todos os retries:
    - Vai para Dead Letter Queue (DLQ)
    - DLQ permite análise manual
    - Pode ser re-enfileirada depois de fix
    """
    try:
        logger.info(f"🎲 Executando risky task: {data}")

        # Simula erro permanente (ex: data inválida)
        if not data.get("valid"):
            raise ValueError("Invalid data")

        time.sleep(1)
        return {"status": "success", "data": data}

    except Exception as exc:
        logger.error(f"❌ Risky task falhou: {exc}")

        # Se esgotou retries, enviar para DLQ
        if self.request.retries >= self.max_retries:
            send_to_dlq.delay(task_name=self.name, data=data, error=str(exc))
            logger.error(f"💀 Task enviada para DLQ após {self.max_retries} retries")

        raise


@celery_app.task(name='tasks.send_to_dlq')
def send_to_dlq(task_name: str, data: dict, error: str):
    """Envia task falhada para Dead Letter Queue"""
    dlq_entry = {
        "task": task_name,
        "data": data,
        "error": error,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Salvar no Redis (ou DB, S3, etc)
    redis_client.lpush("dlq:failed_tasks", json.dumps(dlq_entry))
    logger.info(f"💀 Task salva na DLQ: {task_name}")


# ============================================================================
# EXEMPLO 3: Padrões de Mensageria
# ============================================================================

class MessagePattern(Enum):
    """Padrões comuns de mensageria"""
    POINT_TO_POINT = "point_to_point"  # 1 producer → 1 consumer
    PUBLISH_SUBSCRIBE = "pub_sub"      # 1 producer → N consumers
    FANOUT = "fanout"                   # Broadcast para todos
    DIRECT = "direct"                   # Routing por chave


def exemplo_fanout_pattern():
    """
    Fanout: broadcast para múltiplos consumers

    Caso de uso: Notificar múltiplos serviços sobre um evento

    Evento: "Novo usuário registrado"
    Consumers:
    - Serviço de email (enviar boas-vindas)
    - Serviço de analytics (rastrear signup)
    - Serviço de onboarding (iniciar tutorial)
    """
    print("\n" + "="*70)
    print("EXEMPLO 5: Fanout Pattern (Broadcast)")
    print("="*70)

    from celery import group

    user_data = {"id": 123, "email": "joao@example.com", "name": "João"}

    # Group: executar tasks em paralelo (não em sequência)
    tasks = group(
        send_welcome_email.s(user_data),
        track_signup.s(user_data),
        start_onboarding.s(user_data)
    )

    result = tasks.apply_async()
    print(f"Broadcast enviado! {len(result)} tasks executando em paralelo")

    # Aguardar todas
    results = result.get(timeout=10)
    print(f"✅ Todas as tasks completaram: {results}")


@celery_app.task(name='tasks.send_welcome_email')
def send_welcome_email(user_data: dict):
    logger.info(f"📧 Enviando email de boas-vindas para {user_data['email']}")
    time.sleep(1)
    return {"service": "email", "status": "sent"}


@celery_app.task(name='tasks.track_signup')
def track_signup(user_data: dict):
    logger.info(f"📊 Rastreando signup no analytics: user {user_data['id']}")
    time.sleep(1)
    return {"service": "analytics", "status": "tracked"}


@celery_app.task(name='tasks.start_onboarding')
def start_onboarding(user_data: dict):
    logger.info(f"🎓 Iniciando onboarding para user {user_data['id']}")
    time.sleep(1)
    return {"service": "onboarding", "status": "started"}


# ============================================================================
# EXEMPLO 4: Monitoramento
# ============================================================================

from celery.events.snapshot import Polaroid

@celery_app.task(name='tasks.monitor_queue_health')
def monitor_queue_health():
    """
    Monitora saúde das filas

    Métricas importantes:
    - Tamanho da fila (backlog)
    - Taxa de processamento
    - Taxa de erro
    - Workers ativos
    """
    from celery import current_app

    # Inspecionar workers
    inspect = current_app.control.inspect()

    active = inspect.active()  # Tasks sendo executadas
    scheduled = inspect.scheduled()  # Tasks agendadas
    registered = inspect.registered()  # Tasks disponíveis

    stats = {
        "active_tasks": sum(len(tasks) for tasks in (active or {}).values()),
        "scheduled_tasks": sum(len(tasks) for tasks in (scheduled or {}).values()),
        "registered_tasks": len(list((registered or {}).values())[0]) if registered else 0,
        "timestamp": datetime.utcnow().isoformat()
    }

    logger.info(f"📊 Queue Health: {stats}")
    return stats


# ============================================================================
# COMPARAÇÃO: Celery vs RabbitMQ vs Kafka
# ============================================================================

def print_comparison():
    """Imprime comparação de sistemas de fila"""
    print("\n" + "="*70)
    print("COMPARAÇÃO: Celery vs RabbitMQ vs Kafka vs AWS SQS")
    print("="*70)

    comparison = """
┌────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Característica │    Celery    │   RabbitMQ   │     Kafka    │    AWS SQS   │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Tipo           │ Task Queue   │ Message      │ Event Stream │ Message      │
│                │              │ Broker       │              │ Queue        │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Throughput     │ ~50k msg/s   │ ~50k msg/s   │ ~1M msg/s    │ ~300 msg/s   │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Latência       │ <10ms        │ <5ms         │ <10ms        │ ~100ms       │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Persistência   │ Redis/RMQ    │ Sim          │ Sim (log)    │ Sim          │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Order          │ ❌ Não       │ ✅ Por queue │ ✅ Por parti │ ❌ FIFO queue│
│ Guarantee      │              │              │ ção          │ (separado)   │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Replay         │ ❌ Não       │ ❌ Não       │ ✅ Sim       │ ❌ Não       │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Complexidade   │ ⭐⭐         │ ⭐⭐⭐       │ ⭐⭐⭐⭐     │ ⭐           │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Escalabilidade │ Média        │ Média        │ Alta         │ Alta         │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Custo          │ Baixo        │ Baixo        │ Médio        │ Pay-per-use  │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Use quando     │ Tasks        │ Mensageria   │ Event        │ Serverless,  │
│                │ assíncronas, │ entre        │ Sourcing,    │ AWS nativo   │
│                │ job queue    │ serviços     │ analytics    │              │
└────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘

📚 GUIA DE DECISÃO:

✅ Use CELERY quando:
   - Precisa processar tasks assíncronas em Python
   - Background jobs (emails, reports, etc)
   - Retry e scheduling são importantes
   - Fácil integração com Django/FastAPI
   - 80% dos casos de task queue

✅ Use RABBITMQ quando:
   - Mensageria entre microserviços
   - Precisa routing complexo
   - Garantias de entrega são críticas
   - Language-agnostic (Java, Go, Node, etc)

✅ Use KAFKA quando:
   - Event Sourcing / CQRS
   - Analytics em tempo real
   - Precisa replay de eventos
   - Altíssimo throughput (milhões de msgs/s)
   - Stream processing

✅ Use AWS SQS quando:
   - Infraestrutura toda na AWS
   - Serverless (Lambda)
   - Não quer gerenciar infra
   - Não precisa alta performance
"""
    print(comparison)


# ============================================================================
# PADRÕES AVANÇADOS
# ============================================================================

def exemplo_saga_pattern():
    """
    Saga Pattern: Transação distribuída

    Caso de uso: Processar pedido e-commerce

    Passos:
    1. Reservar estoque
    2. Processar pagamento
    3. Criar ordem de envio
    4. Notificar usuário

    Se qualquer passo falhar: executar compensação (rollback)
    """
    print("\n" + "="*70)
    print("EXEMPLO 6: Saga Pattern (Transação Distribuída)")
    print("="*70)

    from celery import chain, chord

    order_data = {"order_id": "ORD-123", "user_id": 456, "items": [1, 2, 3]}

    # Chord: executar tasks em paralelo, depois executar callback
    workflow = chord([
        reserve_stock.s(order_data),
        process_payment_saga.s(order_data),
        create_shipment.s(order_data)
    ])(finalize_order.s(order_data))  # Callback após todas completarem

    result = workflow.get(timeout=15)
    print(f"✅ Saga completa: {result}")


@celery_app.task(name='tasks.reserve_stock')
def reserve_stock(order_data: dict):
    logger.info(f"📦 Reservando estoque para order {order_data['order_id']}")
    time.sleep(1)
    # Se falhar: raise exception (saga será compensada)
    return {"step": "stock", "status": "reserved"}


@celery_app.task(name='tasks.process_payment_saga')
def process_payment_saga(order_data: dict):
    logger.info(f"💳 Processando pagamento para order {order_data['order_id']}")
    time.sleep(2)
    return {"step": "payment", "status": "processed"}


@celery_app.task(name='tasks.create_shipment')
def create_shipment(order_data: dict):
    logger.info(f"🚚 Criando ordem de envio para order {order_data['order_id']}")
    time.sleep(1)
    return {"step": "shipment", "status": "created"}


@celery_app.task(name='tasks.finalize_order')
def finalize_order(results: List[dict], order_data: dict):
    """Callback: executado após todas as tasks do chord"""
    logger.info(f"✅ Finalizando order {order_data['order_id']}")
    logger.info(f"Resultados: {results}")
    return {"order_id": order_data['order_id'], "status": "completed", "steps": results}


# ============================================================================
# MAIN: Executar Exemplos
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                    MÓDULO 06: FILAS E STREAMING                          ║
║                Exemplos de Message Queues com Celery                     ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️  IMPORTANTE: Antes de executar, inicie:
   1. Redis: docker run -d -p 6379:6379 redis:alpine
   2. Celery Worker: celery -A 01_message_queues_comparison:celery_app worker --loglevel=info

Escolha um exemplo para executar:
1. Task assíncrona simples
2. Task com retry e exponential backoff
3. Idempotência (executar 2x = mesmo resultado)
4. Chain de tasks (pipeline)
5. Fanout pattern (broadcast)
6. Saga pattern (transação distribuída)
7. Ver comparação de sistemas

Digite o número (ou 0 para sair): """)

    choice = input().strip()

    if choice == "1":
        exemplo_celery_basico()
    elif choice == "2":
        exemplo_celery_retry()
    elif choice == "3":
        exemplo_celery_idempotencia()
    elif choice == "4":
        exemplo_celery_chain()
    elif choice == "5":
        exemplo_fanout_pattern()
    elif choice == "6":
        exemplo_saga_pattern()
    elif choice == "7":
        print_comparison()
    elif choice == "0":
        print("👋 Até logo!")
    else:
        print("❌ Opção inválida")

    print("\n" + "="*70)
    print("💡 CONCEITOS APRENDIDOS:")
    print("="*70)
    print("""
1. ✅ Task Queue: Processar trabalho em background
2. ✅ Retry Strategy: Exponential backoff para resiliência
3. ✅ Idempotência: Executar múltiplas vezes = mesmo resultado
4. ✅ Chain: Encadear tasks (output → input)
5. ✅ Group: Executar tasks em paralelo
6. ✅ Chord: Paralelo + callback
7. ✅ Dead Letter Queue: Analisar falhas permanentes
8. ✅ Fanout: Broadcast para múltiplos consumers
9. ✅ Saga Pattern: Transação distribuída com compensação
10. ✅ Monitoring: Rastrear saúde das filas

📚 QUANDO USAR FILAS:
- ✅ Processar trabalho demorado sem bloquear requisição HTTP
- ✅ Retry automático em caso de falha
- ✅ Distribuir carga entre múltiplos workers
- ✅ Processar trabalho em horários específicos (scheduling)
- ✅ Desacoplar serviços (microserviços)

⚠️  CUIDADOS:
- ❌ Tasks devem ser idempotentes (podem ser re-executadas)
- ❌ Não guardar estado em memória (workers podem morrer)
- ❌ Monitorar tamanho das filas (backlog)
- ❌ Implementar timeout para evitar tasks travadas
- ❌ Ter DLQ para análise de falhas permanentes
""")
