"""
Exemplo: Celery - Tasks Assíncronas

Setup:
1. pip install celery redis
2. docker run -d -p 6379:6379 redis
3. Terminal 1: python 01_celery_tasks.py worker
4. Terminal 2: python 01_celery_tasks.py client

Demonstra como usar Celery para processar tarefas assíncronas.
"""

from celery import Celery
import time
from datetime import datetime

# ============================================
# CELERY APP SETUP
# ============================================

app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

# Configuração
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo',
    enable_utc=True,
    task_track_started=True,
)


# ============================================
# TASK 1: SIMPLE TASK
# ============================================

@app.task(name='send_email')
def send_email(email: str, subject: str, body: str):
    """
    Task simples: enviar email

    Use case: Não bloqueia requisição HTTP
    """
    print(f"📧 [TASK START] Sending email to {email}")
    print(f"   Subject: {subject}")

    # Simula envio (SMTP, SendGrid, etc)
    time.sleep(3)  # Demora 3 segundos

    print(f"✅ [TASK DONE] Email sent to {email}")
    return {"status": "sent", "email": email, "timestamp": datetime.now().isoformat()}


# ============================================
# TASK 2: RETRY WITH EXPONENTIAL BACKOFF
# ============================================

@app.task(
    name='process_payment',
    bind=True,  # Passa 'self' como primeiro argumento
    max_retries=3,  # Máximo de retries
    default_retry_delay=60  # Delay entre retries (segundos)
)
def process_payment(self, order_id: int, amount: float):
    """
    Task com retry: processar pagamento

    Use case: API externa pode falhar temporariamente
    """
    print(f"💳 [TASK START] Processing payment for order {order_id}")
    print(f"   Amount: ${amount}")

    try:
        # Simula chamada a gateway de pagamento
        time.sleep(2)

        # Simula falha aleatória (30% chance)
        import random
        if random.random() < 0.3:
            raise Exception("Payment gateway timeout")

        print(f"✅ [TASK DONE] Payment processed")
        return {"order_id": order_id, "status": "completed", "amount": amount}

    except Exception as exc:
        # Retry com exponential backoff
        countdown = 2 ** self.request.retries  # 1s, 2s, 4s, 8s...
        print(f"⚠️  [RETRY] Attempt {self.request.retries + 1}/3")
        print(f"   Retrying in {countdown}s...")

        raise self.retry(exc=exc, countdown=countdown)


# ============================================
# TASK 3: LONG RUNNING TASK
# ============================================

@app.task(name='process_video', bind=True)
def process_video(self, video_id: int):
    """
    Task longa: processar vídeo

    Use case: Encoding pode demorar minutos/horas

    Usa self.update_state() para reportar progresso
    """
    print(f"🎬 [TASK START] Processing video {video_id}")

    stages = [
        ("Downloading", 10),
        ("Transcoding", 30),
        ("Generating thumbnails", 5),
        ("Uploading to CDN", 15),
    ]

    total_steps = len(stages)

    for idx, (stage_name, duration) in enumerate(stages):
        # Update progress
        progress = int((idx / total_steps) * 100)
        self.update_state(
            state='PROGRESS',
            meta={
                'current': idx,
                'total': total_steps,
                'stage': stage_name,
                'progress': progress
            }
        )

        print(f"  [{progress}%] {stage_name}...")
        time.sleep(duration)

    print(f"✅ [TASK DONE] Video {video_id} processed")
    return {"video_id": video_id, "status": "ready", "url": f"https://cdn.example.com/{video_id}.mp4"}


# ============================================
# TASK 4: TASK CHAIN (WORKFLOW)
# ============================================

@app.task(name='step1_fetch_data')
def step1_fetch_data(user_id: int):
    """Step 1: Buscar dados do usuário"""
    print(f"📥 [STEP 1] Fetching data for user {user_id}")
    time.sleep(2)
    return {"user_id": user_id, "name": "Alice", "email": "alice@example.com"}


@app.task(name='step2_process_data')
def step2_process_data(user_data: dict):
    """Step 2: Processar dados"""
    print(f"⚙️  [STEP 2] Processing data for {user_data['name']}")
    time.sleep(2)
    user_data['processed'] = True
    return user_data


@app.task(name='step3_save_data')
def step3_save_data(user_data: dict):
    """Step 3: Salvar no banco"""
    print(f"💾 [STEP 3] Saving data for {user_data['name']}")
    time.sleep(1)
    return {"status": "saved", "user_id": user_data['user_id']}


# ============================================
# TASK 5: PERIODIC TASK (CRON)
# ============================================

@app.task(name='cleanup_old_files')
def cleanup_old_files():
    """
    Task periódica: limpar arquivos antigos

    Configurar no beat:
    celery -A 01_celery_tasks beat --loglevel=info
    """
    print("🧹 [CRON] Running cleanup...")
    time.sleep(2)
    print("✅ [CRON] Cleanup completed")
    return {"deleted": 42, "timestamp": datetime.now().isoformat()}


# Configuração do Celery Beat (cron)
app.conf.beat_schedule = {
    'cleanup-every-hour': {
        'task': 'cleanup_old_files',
        'schedule': 3600.0,  # Cada hora (em segundos)
    },
}


# ============================================
# CLIENT CODE
# ============================================

def demo_simple_task():
    """Demo 1: Task simples"""
    print("\n" + "="*60)
    print("DEMO 1: SIMPLE TASK")
    print("="*60)

    # Envia task para a fila
    result = send_email.delay('user@example.com', 'Welcome!', 'Thanks for signing up')

    print(f"✅ Task queued: {result.id}")
    print(f"   Status: {result.status}")

    # Aguarda resultado (blocking)
    print("⏳ Waiting for result...")
    final_result = result.get(timeout=10)

    print(f"✅ Result: {final_result}")


def demo_retry_task():
    """Demo 2: Task com retry"""
    print("\n" + "="*60)
    print("DEMO 2: RETRY TASK")
    print("="*60)

    result = process_payment.delay(12345, 99.99)

    print(f"✅ Task queued: {result.id}")

    # Aguarda (pode demorar devido aos retries)
    print("⏳ Waiting for result (may retry)...")
    try:
        final_result = result.get(timeout=30)
        print(f"✅ Result: {final_result}")
    except Exception as e:
        print(f"❌ Task failed after retries: {e}")


def demo_progress_task():
    """Demo 3: Task com progresso"""
    print("\n" + "="*60)
    print("DEMO 3: LONG RUNNING TASK WITH PROGRESS")
    print("="*60)

    result = process_video.delay(999)

    print(f"✅ Task queued: {result.id}")
    print("⏳ Monitoring progress...")

    # Poll progress
    while not result.ready():
        if result.state == 'PROGRESS':
            meta = result.info
            print(f"  [{meta['progress']}%] {meta['stage']}...")
        time.sleep(2)

    print(f"✅ Result: {result.result}")


def demo_task_chain():
    """Demo 4: Chain de tasks (workflow)"""
    print("\n" + "="*60)
    print("DEMO 4: TASK CHAIN (WORKFLOW)")
    print("="*60)

    from celery import chain

    # Chain: step1 | step2 | step3
    workflow = chain(
        step1_fetch_data.s(123),  # .s() = signature
        step2_process_data.s(),   # Recebe output do anterior
        step3_save_data.s()
    )

    result = workflow.apply_async()

    print(f"✅ Workflow queued: {result.id}")
    print("⏳ Waiting for workflow...")

    final_result = result.get(timeout=30)
    print(f"✅ Result: {final_result}")


def demo_parallel_tasks():
    """Demo 5: Tasks paralelas"""
    print("\n" + "="*60)
    print("DEMO 5: PARALLEL TASKS")
    print("="*60)

    from celery import group

    # Envia 5 emails em paralelo
    job = group([
        send_email.s(f'user{i}@example.com', 'Welcome!', 'Thanks!')
        for i in range(5)
    ])

    result = job.apply_async()

    print(f"✅ 5 tasks queued in parallel")
    print("⏳ Waiting for all tasks...")

    results = result.get(timeout=30)
    print(f"✅ All tasks completed:")
    for r in results:
        print(f"   - {r['email']}: {r['status']}")


# ============================================
# MAIN
# ============================================

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python 01_celery_tasks.py worker    # Start Celery worker")
        print("  python 01_celery_tasks.py client    # Run client demos")
        return

    mode = sys.argv[1]

    if mode == 'worker':
        # Start Celery worker
        print("="*60)
        print("🚀 STARTING CELERY WORKER")
        print("="*60)
        print()
        print("Listening for tasks...")
        print("Press Ctrl+C to stop")
        print()

        # Run worker
        app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=4'  # 4 worker processes
        ])

    elif mode == 'client':
        # Run demos
        print("="*60)
        print("🎯 CELERY CLIENT DEMOS")
        print("="*60)
        print()
        print("Make sure Celery worker is running!")
        print("  Terminal 1: python 01_celery_tasks.py worker")
        print()

        demos = [
            ("Simple Task", demo_simple_task),
            ("Retry Task", demo_retry_task),
            ("Progress Task", demo_progress_task),
            ("Task Chain", demo_task_chain),
            ("Parallel Tasks", demo_parallel_tasks),
        ]

        for name, demo_func in demos:
            print(f"\n▶️  Running: {name}")
            input("Press ENTER to continue...")
            demo_func()

        print("\n" + "="*60)
        print("✅ ALL DEMOS COMPLETED")
        print("="*60)


if __name__ == "__main__":
    main()


"""
ARCHITECTURE:

┌─────────────────────────────────────────────────────────────┐
│                         CLIENT                              │
│  (FastAPI, Django, Flask, Script, etc.)                     │
│                                                             │
│  result = send_email.delay('user@example.com', ...)       │
└────────────────────┬────────────────────────────────────────┘
                     │ enqueue task
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      MESSAGE BROKER                         │
│                     (Redis / RabbitMQ)                      │
│                                                             │
│  Queue: [ task1, task2, task3, ... ]                       │
└────────────────────┬────────────────────────────────────────┘
                     │ dequeue task
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    CELERY WORKERS                           │
│             (Multiple worker processes)                     │
│                                                             │
│  Worker 1  →  Executes task1                               │
│  Worker 2  →  Executes task2                               │
│  Worker 3  →  Executes task3                               │
└────────────────────┬────────────────────────────────────────┘
                     │ save result
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     RESULT BACKEND                          │
│                     (Redis / Database)                      │
│                                                             │
│  task_id → result                                           │
└─────────────────────────────────────────────────────────────┘

USE CASES:

1. Send emails (não bloqueia HTTP response)
2. Process videos/images (long-running)
3. Generate reports (CPU-intensive)
4. Call external APIs (I/O-bound)
5. Scheduled tasks (cron jobs)
6. Data pipelines (ETL)
"""
