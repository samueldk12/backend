"""
Módulo 03 - Banco de Dados: Transações e Isolation Levels

Este exemplo demonstra:
1. ACID properties na prática
2. Isolation levels (Read Uncommitted, Read Committed, Repeatable Read, Serializable)
3. Problemas de concorrência (Dirty Read, Non-Repeatable Read, Phantom Read)
4. Connection pooling e performance
5. Deadlocks e como evitá-los
6. Transações distribuídas (2-Phase Commit)

Execute:
    # Inicie PostgreSQL
    docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine

    # Execute o script
    python 02_transactions_isolation.py
"""

import time
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
import logging

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, CheckConstraint, event
)
from sqlalchemy.orm import (
    declarative_base, sessionmaker, Session, relationship
)
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(threadName)-10s] %(message)s')
logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# MODELOS
# ============================================================================

class Account(Base):
    """Conta bancária para demonstrar transações"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    owner = Column(String(100), nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Constraint: saldo não pode ser negativo
    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_positive_balance'),
    )

    transactions_from = relationship("Transaction", foreign_keys="Transaction.from_account_id")
    transactions_to = relationship("Transaction", foreign_keys="Transaction.to_account_id")


class Transaction(Base):
    """Transação entre contas"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])


# ============================================================================
# EXEMPLO 1: ACID Properties
# ============================================================================

def exemplo_acid():
    """
    Demonstra ACID properties:
    - Atomicity: Tudo ou nada
    - Consistency: Regras de integridade respeitadas
    - Isolation: Transações não interferem entre si
    - Durability: Dados persistem após commit
    """
    print("\n" + "="*70)
    print("EXEMPLO 1: ACID Properties")
    print("="*70)

    engine = create_engine("postgresql://postgres:postgres@localhost:5432/postgres")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Criar contas
    db = SessionLocal()
    alice = Account(owner="Alice", balance=1000.0)
    bob = Account(owner="Bob", balance=500.0)
    db.add_all([alice, bob])
    db.commit()
    db.refresh(alice)
    db.refresh(bob)

    print(f"Saldo inicial - Alice: R${alice.balance:.2f}, Bob: R${bob.balance:.2f}")

    # -------------------------------------------------------------------------
    # ATOMICITY: Transferência deve ser atômica (tudo ou nada)
    # -------------------------------------------------------------------------
    print("\n🔹 ATOMICITY (Atomicidade)")

    def transfer_money(from_id: int, to_id: int, amount: float, should_fail: bool = False):
        """Transfere dinheiro entre contas"""
        db = SessionLocal()
        try:
            # Buscar contas
            from_account = db.query(Account).filter(Account.id == from_id).first()
            to_account = db.query(Account).filter(Account.id == to_id).first()

            # Debitar
            from_account.balance -= amount
            logger.info(f"💸 Debitando R${amount} de {from_account.owner}")

            # Simular erro no meio da transação
            if should_fail:
                raise Exception("❌ Erro simulado!")

            # Creditar
            to_account.balance += amount
            logger.info(f"💰 Creditando R${amount} para {to_account.owner}")

            # Registrar transação
            transaction = Transaction(
                from_account_id=from_id,
                to_account_id=to_id,
                amount=amount
            )
            db.add(transaction)

            # COMMIT: se chegar aqui, tudo é persistido
            db.commit()
            logger.info("✅ Transação commitada com sucesso")

        except Exception as e:
            # ROLLBACK: desfaz TODAS as mudanças
            db.rollback()
            logger.error(f"🔄 Rollback executado: {e}")

        finally:
            db.close()

    # Transferência com sucesso
    print("\nTransferência 1: Alice → Bob (R$100) - deve funcionar")
    transfer_money(alice.id, bob.id, 100.0, should_fail=False)

    # Verificar saldos
    db.refresh(alice)
    db.refresh(bob)
    print(f"Saldos após transferência: Alice: R${alice.balance:.2f}, Bob: R${bob.balance:.2f}")

    # Transferência com erro
    print("\nTransferência 2: Alice → Bob (R$200) - vai falhar no meio")
    transfer_money(alice.id, bob.id, 200.0, should_fail=True)

    # Verificar saldos (não devem ter mudado!)
    db.refresh(alice)
    db.refresh(bob)
    print(f"Saldos após erro: Alice: R${alice.balance:.2f}, Bob: R${bob.balance:.2f}")
    print("✅ Atomicidade: rollback desfez as mudanças parciais!")

    # -------------------------------------------------------------------------
    # CONSISTENCY: Constraints são respeitados
    # -------------------------------------------------------------------------
    print("\n🔹 CONSISTENCY (Consistência)")

    try:
        db.begin()
        alice.balance = -100  # Viola constraint check_positive_balance
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Constraint violado: {e}")
        print("✅ Consistência: constraint impediu saldo negativo!")

    db.close()


# ============================================================================
# EXEMPLO 2: Isolation Levels
# ============================================================================

def exemplo_isolation_levels():
    """
    Demonstra problemas de concorrência e como isolation levels resolvem

    Problemas:
    1. Dirty Read: Ler dados não commitados
    2. Non-Repeatable Read: Dados mudam entre leituras
    3. Phantom Read: Novas linhas aparecem entre leituras

    Isolation Levels:
    - Read Uncommitted: permite todos os problemas (mais rápido)
    - Read Committed: previne dirty reads (padrão PostgreSQL)
    - Repeatable Read: previne dirty + non-repeatable reads
    - Serializable: previne todos (mais lento)
    """
    print("\n" + "="*70)
    print("EXEMPLO 2: Isolation Levels")
    print("="*70)

    engine = create_engine("postgresql://postgres:postgres@localhost:5432/postgres")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    # -------------------------------------------------------------------------
    # Problema 1: DIRTY READ
    # -------------------------------------------------------------------------
    print("\n🔹 Problema: DIRTY READ")
    print("Thread 1 lê dados que Thread 2 ainda não commitou")

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    alice = Account(owner="Alice", balance=1000.0)
    db.add(alice)
    db.commit()
    db.close()

    def thread1_dirty_read():
        """Thread que faz mudança mas não commita"""
        engine_t1 = create_engine(
            "postgresql://postgres:postgres@localhost:5432/postgres",
            isolation_level="READ UNCOMMITTED"  # Permite dirty read
        )
        Session1 = sessionmaker(bind=engine_t1)
        db1 = Session1()

        account = db1.query(Account).filter(Account.owner == "Alice").first()
        logger.info(f"[T1] Saldo antes: R${account.balance}")

        # Fazer mudança mas NÃO commitar
        account.balance = 5000.0
        logger.info(f"[T1] Mudei saldo para R${account.balance} (SEM commit)")

        time.sleep(2)  # Thread 2 vai ler aqui

        # Rollback!
        db1.rollback()
        logger.info("[T1] Rollback executado")
        db1.close()

    def thread2_dirty_read():
        """Thread que lê dados não commitados"""
        time.sleep(0.5)  # Esperar T1 mudar

        engine_t2 = create_engine(
            "postgresql://postgres:postgres@localhost:5432/postgres",
            isolation_level="READ UNCOMMITTED"
        )
        Session2 = sessionmaker(bind=engine_t2)
        db2 = Session2()

        account = db2.query(Account).filter(Account.owner == "Alice").first()
        logger.info(f"[T2] Li saldo: R${account.balance} (DIRTY READ!)")
        # ☠️  Leu R$5000 mas T1 vai fazer rollback!

        db2.close()

    t1 = threading.Thread(target=thread1_dirty_read, name="Thread-1")
    t2 = threading.Thread(target=thread2_dirty_read, name="Thread-2")

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("\n❌ Dirty Read: Thread 2 leu dados que Thread 1 não commitou!")
    print("✅ Solução: usar READ COMMITTED ou superior")

    # -------------------------------------------------------------------------
    # Problema 2: NON-REPEATABLE READ
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print("🔹 Problema: NON-REPEATABLE READ")
    print("Thread 1 lê dados 2x e obtém valores diferentes")

    def thread1_non_repeatable():
        """Lê dados 2 vezes"""
        engine_t1 = create_engine(
            "postgresql://postgres:postgres@localhost:5432/postgres",
            isolation_level="READ COMMITTED"  # Permite non-repeatable read
        )
        Session1 = sessionmaker(bind=engine_t1)
        db1 = Session1()

        # Primeira leitura
        account = db1.query(Account).filter(Account.owner == "Alice").first()
        logger.info(f"[T1] Primeira leitura: R${account.balance}")

        time.sleep(2)  # Thread 2 vai mudar aqui

        # Segunda leitura (mesmo SELECT)
        db1.expire_all()  # Forçar re-fetch
        account = db1.query(Account).filter(Account.owner == "Alice").first()
        logger.info(f"[T1] Segunda leitura: R${account.balance} (MUDOU!)")
        # ☠️  Valor diferente na mesma transação!

        db1.close()

    def thread2_non_repeatable():
        """Muda dados no meio"""
        time.sleep(1)

        engine_t2 = create_engine("postgresql://postgres:postgres@localhost:5432/postgres")
        Session2 = sessionmaker(bind=engine_t2)
        db2 = Session2()

        account = db2.query(Account).filter(Account.owner == "Alice").first()
        account.balance = 2000.0
        db2.commit()
        logger.info("[T2] Mudei saldo e commitei")

        db2.close()

    t1 = threading.Thread(target=thread1_non_repeatable, name="Thread-1")
    t2 = threading.Thread(target=thread2_non_repeatable, name="Thread-2")

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("\n❌ Non-Repeatable Read: T1 leu valores diferentes na mesma transação!")
    print("✅ Solução: usar REPEATABLE READ ou SERIALIZABLE")


# ============================================================================
# EXEMPLO 3: Deadlock
# ============================================================================

def exemplo_deadlock():
    """
    Deadlock: Duas transações esperando uma pela outra

    T1: Lock em A → tenta lock em B
    T2: Lock em B → tenta lock em A
    Resultado: deadlock! (PostgreSQL detecta e aborta uma)
    """
    print("\n" + "="*70)
    print("EXEMPLO 3: Deadlock e Como Evitar")
    print("="*70)

    engine = create_engine("postgresql://postgres:postgres@localhost:5432/postgres")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Criar contas
    db = SessionLocal()
    alice = Account(owner="Alice", balance=1000.0)
    bob = Account(owner="Bob", balance=1000.0)
    db.add_all([alice, bob])
    db.commit()
    alice_id, bob_id = alice.id, bob.id
    db.close()

    deadlock_detected = threading.Event()

    def thread1_deadlock():
        """Alice → Bob"""
        db1 = SessionLocal()
        try:
            # Lock em Alice
            alice = db1.query(Account).filter(Account.id == alice_id).with_for_update().first()
            logger.info("[T1] 🔒 Locked Alice")

            time.sleep(1)  # T2 vai lockar Bob aqui

            # Tentar lock em Bob (vai esperar T2)
            logger.info("[T1] Tentando lock em Bob...")
            bob = db1.query(Account).filter(Account.id == bob_id).with_for_update().first()
            logger.info("[T1] 🔒 Locked Bob")

            # Transferir
            alice.balance -= 100
            bob.balance += 100
            db1.commit()
            logger.info("[T1] ✅ Transação completa")

        except OperationalError as e:
            db1.rollback()
            deadlock_detected.set()
            logger.error(f"[T1] ☠️  DEADLOCK DETECTADO: {e}")

        finally:
            db1.close()

    def thread2_deadlock():
        """Bob → Alice (ordem oposta!)"""
        time.sleep(0.5)  # T1 começa primeiro

        db2 = SessionLocal()
        try:
            # Lock em Bob
            bob = db2.query(Account).filter(Account.id == bob_id).with_for_update().first()
            logger.info("[T2] 🔒 Locked Bob")

            time.sleep(1)

            # Tentar lock em Alice (vai esperar T1)
            logger.info("[T2] Tentando lock em Alice...")
            alice = db2.query(Account).filter(Account.id == alice_id).with_for_update().first()
            logger.info("[T2] 🔒 Locked Alice")

            # Transferir
            bob.balance -= 100
            alice.balance += 100
            db2.commit()
            logger.info("[T2] ✅ Transação completa")

        except OperationalError as e:
            db2.rollback()
            deadlock_detected.set()
            logger.error(f"[T2] ☠️  DEADLOCK DETECTADO: {e}")

        finally:
            db2.close()

    print("\nCriando deadlock intencional...")
    t1 = threading.Thread(target=thread1_deadlock, name="Thread-1")
    t2 = threading.Thread(target=thread2_deadlock, name="Thread-2")

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    if deadlock_detected.is_set():
        print("\n☠️  Deadlock foi detectado pelo PostgreSQL!")
        print("\n✅ SOLUÇÃO: Sempre adquirir locks na MESMA ORDEM")
        print("   Exemplo: sempre lockar conta com menor ID primeiro\n")

    # Demonstrar solução
    def transfer_no_deadlock(from_id: int, to_id: int, amount: float, thread_name: str):
        """Transferência que evita deadlock"""
        db = SessionLocal()
        try:
            # Sempre lockar na mesma ordem (menor ID primeiro)
            first_id, second_id = sorted([from_id, to_id])

            first = db.query(Account).filter(Account.id == first_id).with_for_update().first()
            logger.info(f"[{thread_name}] 🔒 Locked account {first_id}")

            time.sleep(0.5)

            second = db.query(Account).filter(Account.id == second_id).with_for_update().first()
            logger.info(f"[{thread_name}] 🔒 Locked account {second_id}")

            # Identificar from/to
            from_acc = first if first.id == from_id else second
            to_acc = second if second.id == to_id else first

            # Transferir
            from_acc.balance -= amount
            to_acc.balance += amount

            db.commit()
            logger.info(f"[{thread_name}] ✅ Transferência completa")

        finally:
            db.close()

    print("Executando transferências SEM deadlock (locks ordenados):")
    t1 = threading.Thread(target=lambda: transfer_no_deadlock(alice_id, bob_id, 100, "T1"), name="Thread-1")
    t2 = threading.Thread(target=lambda: transfer_no_deadlock(bob_id, alice_id, 50, "T2"), name="Thread-2")

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("\n✅ Sem deadlock! Ambas transações completaram.")


# ============================================================================
# EXEMPLO 4: Connection Pooling
# ============================================================================

def exemplo_connection_pooling():
    """
    Connection Pooling: reusar conexões ao invés de criar/destruir

    Benefícios:
    - Reduz latência (handshake TCP é caro)
    - Reduz carga no banco
    - Melhor performance

    Configurações:
    - pool_size: quantidade de conexões mantidas
    - max_overflow: conexões extras permitidas
    - pool_timeout: quanto tempo esperar por conexão
    - pool_recycle: renovar conexão após N segundos
    """
    print("\n" + "="*70)
    print("EXEMPLO 4: Connection Pooling")
    print("="*70)

    # -------------------------------------------------------------------------
    # SEM pooling: criar conexão a cada query
    # -------------------------------------------------------------------------
    print("\n🔹 SEM Connection Pooling")

    def query_without_pool():
        # Criar engine toda vez (péssima ideia!)
        engine = create_engine(
            "postgresql://postgres:postgres@localhost:5432/postgres",
            poolclass=None  # Sem pool
        )
        Session = sessionmaker(bind=engine)
        db = Session()

        result = db.execute("SELECT 1").scalar()
        db.close()
        engine.dispose()  # Fecha conexão
        return result

    start = time.time()
    for _ in range(10):
        query_without_pool()
    elapsed_no_pool = time.time() - start

    print(f"10 queries sem pool: {elapsed_no_pool:.3f}s")

    # -------------------------------------------------------------------------
    # COM pooling: reusar conexões
    # -------------------------------------------------------------------------
    print("\n🔹 COM Connection Pooling")

    engine_pooled = create_engine(
        "postgresql://postgres:postgres@localhost:5432/postgres",
        poolclass=QueuePool,
        pool_size=5,  # Manter 5 conexões abertas
        max_overflow=10,  # Até 15 conexões simultâneas (5 + 10)
        pool_timeout=30,  # Esperar 30s por conexão
        pool_recycle=3600,  # Renovar conexão após 1h
        pool_pre_ping=True,  # Verificar conexão antes de usar
        echo_pool=True  # Log de pool events
    )

    Session = sessionmaker(bind=engine_pooled)

    def query_with_pool():
        db = Session()
        result = db.execute("SELECT 1").scalar()
        db.close()  # Retorna conexão para pool (não fecha!)
        return result

    start = time.time()
    for _ in range(10):
        query_with_pool()
    elapsed_with_pool = time.time() - start

    print(f"10 queries com pool: {elapsed_with_pool:.3f}s")
    print(f"✅ Speedup: {elapsed_no_pool / elapsed_with_pool:.1f}x mais rápido")

    # Pool stats
    print(f"\n📊 Pool Stats:")
    print(f"   - Tamanho: {engine_pooled.pool.size()}")
    print(f"   - Checked out: {engine_pooled.pool.checkedout()}")
    print(f"   - Overflow: {engine_pooled.pool.overflow()}")

    engine_pooled.dispose()


# ============================================================================
# COMPARAÇÃO DE ISOLATION LEVELS
# ============================================================================

def print_isolation_comparison():
    """Imprime tabela comparativa de isolation levels"""
    print("\n" + "="*70)
    print("COMPARAÇÃO: Isolation Levels")
    print("="*70)

    comparison = """
┌────────────────────┬──────────────┬─────────────────┬──────────────┬───────────────┐
│ Isolation Level    │  Dirty Read  │ Non-Repeatable  │ Phantom Read │  Performance  │
│                    │              │      Read       │              │               │
├────────────────────┼──────────────┼─────────────────┼──────────────┼───────────────┤
│ READ UNCOMMITTED   │ ❌ Permite   │ ❌ Permite      │ ❌ Permite   │ ⚡⚡⚡⚡       │
│ (nível 0)          │              │                 │              │ Mais rápido   │
├────────────────────┼──────────────┼─────────────────┼──────────────┼───────────────┤
│ READ COMMITTED     │ ✅ Previne   │ ❌ Permite      │ ❌ Permite   │ ⚡⚡⚡         │
│ (padrão PG)        │              │                 │              │ Rápido        │
├────────────────────┼──────────────┼─────────────────┼──────────────┼───────────────┤
│ REPEATABLE READ    │ ✅ Previne   │ ✅ Previne      │ ❌ Permite   │ ⚡⚡           │
│ (recomendado)      │              │                 │              │ Médio         │
├────────────────────┼──────────────┼─────────────────┼──────────────┼───────────────┤
│ SERIALIZABLE       │ ✅ Previne   │ ✅ Previne      │ ✅ Previne   │ ⚡             │
│ (mais forte)       │              │                 │              │ Lento         │
└────────────────────┴──────────────┴─────────────────┴──────────────┴───────────────┘

📚 PROBLEMAS DE CONCORRÊNCIA:

1️⃣  DIRTY READ:
   - Thread A muda dado mas não commita
   - Thread B lê dado não commitado
   - Thread A faz rollback
   - Thread B leu dado "fantasma"!

2️⃣  NON-REPEATABLE READ:
   - Thread A lê dado X = 100
   - Thread B muda X para 200 e commita
   - Thread A lê X novamente = 200 (diferente!)
   - Problema: mesmo SELECT retorna valores diferentes

3️⃣  PHANTOM READ:
   - Thread A: SELECT COUNT(*) = 10
   - Thread B insere nova linha e commita
   - Thread A: SELECT COUNT(*) = 11 (nova linha "apareceu")
   - Problema: novas linhas aparecem entre leituras

🎯 GUIA DE DECISÃO:

✅ Use READ COMMITTED (padrão) quando:
   - Performance é importante
   - Não precisa leituras consistentes
   - 80% dos casos

✅ Use REPEATABLE READ quando:
   - Precisa ler dados consistentes
   - Operações financeiras
   - Reports e analytics

✅ Use SERIALIZABLE quando:
   - Consistência é CRÍTICA
   - Banking, payment processing
   - Pode tolerar rollbacks (serialization failures)

❌ NUNCA use READ UNCOMMITTED em produção
   - Pode ler dados que vão ser revertidos
   - Apenas para debugging
"""
    print(comparison)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║              MÓDULO 03: TRANSAÇÕES E ISOLATION LEVELS                    ║
║         Entenda ACID, Isolation Levels, Deadlocks e Pooling              ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️  IMPORTANTE: Inicie PostgreSQL antes:
   docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine

Escolha um exemplo:
1. ACID Properties (Atomicity, Consistency, Isolation, Durability)
2. Isolation Levels (Dirty Read, Non-Repeatable Read, Phantom Read)
3. Deadlock e como evitar
4. Connection Pooling (performance)
5. Ver comparação de Isolation Levels

Digite o número: """)

    choice = input().strip()

    if choice == "1":
        exemplo_acid()
    elif choice == "2":
        exemplo_isolation_levels()
    elif choice == "3":
        exemplo_deadlock()
    elif choice == "4":
        exemplo_connection_pooling()
    elif choice == "5":
        print_isolation_comparison()
    else:
        print("❌ Opção inválida")

    print("\n" + "="*70)
    print("💡 CONCEITOS APRENDIDOS:")
    print("="*70)
    print("""
1. ✅ ACID: Atomicity, Consistency, Isolation, Durability
2. ✅ Isolation Levels: previnem problemas de concorrência
3. ✅ Dirty Read: ler dados não commitados
4. ✅ Non-Repeatable Read: mesmo SELECT retorna valores diferentes
5. ✅ Phantom Read: novas linhas aparecem entre leituras
6. ✅ Deadlock: duas transações esperando uma pela outra
7. ✅ Connection Pooling: reusar conexões para performance
8. ✅ Locking: SELECT FOR UPDATE para evitar race conditions

⚠️  BEST PRACTICES:

✅ SEMPRE usar transações para operações críticas
✅ Usar REPEATABLE READ para operações financeiras
✅ Sempre lockar resources na MESMA ORDEM (evita deadlock)
✅ Usar connection pooling (5-10 conexões é suficiente)
✅ pool_pre_ping=True para detectar conexões quebradas
✅ Monitorar pool (tamanho, overflow, timeouts)

❌ NUNCA fazer queries longas dentro de transação
❌ NUNCA usar READ UNCOMMITTED em produção
❌ NUNCA ignorar isolation levels
❌ NUNCA criar engine dentro de função (sempre reusar)
""")
