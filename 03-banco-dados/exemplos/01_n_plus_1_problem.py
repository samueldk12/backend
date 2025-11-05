"""
Exemplo: Demonstração do N+1 Problem e Soluções

Execute: python 01_n_plus_1_problem.py
"""

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, selectinload
from sqlalchemy.pool import StaticPool
import time
from contextlib import contextmanager

# ============================================
# DATABASE SETUP
# ============================================

# In-memory SQLite para demonstração
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # Set True to see SQL queries
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ============================================
# MODELS
# ============================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100))

    # Relationship
    posts = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    content = Column(String(1000))

    # Relationship
    user = relationship("User", back_populates="posts")


# Create tables
Base.metadata.create_all(engine)


# ============================================
# SEED DATA
# ============================================

def seed_data():
    """Criar dados de exemplo"""
    session = SessionLocal()

    # Create 50 users
    users = []
    for i in range(1, 51):
        user = User(
            name=f"User {i}",
            email=f"user{i}@example.com"
        )
        users.append(user)

    session.add_all(users)
    session.flush()

    # Each user has 5 posts
    posts = []
    for user in users:
        for j in range(1, 6):
            post = Post(
                user_id=user.id,
                title=f"Post {j} by {user.name}",
                content=f"Content of post {j}"
            )
            posts.append(post)

    session.add_all(posts)
    session.commit()
    session.close()

    print(f"✅ Seeded {len(users)} users with {len(posts)} posts")


# ============================================
# QUERY COUNTER
# ============================================

query_count = 0


@contextmanager
def count_queries():
    """Context manager to count queries"""
    global query_count
    query_count = 0

    # Enable query logging
    engine.echo = True

    yield

    # Disable query logging
    engine.echo = False

    return query_count


# ============================================
# N+1 PROBLEM
# ============================================

def n_plus_1_problem():
    """
    ❌ PROBLEMA: N+1 queries

    1 query para buscar users
    + N queries para buscar posts de cada user
    = 1 + N queries total
    """
    print("\n" + "=" * 60)
    print("❌ N+1 PROBLEM")
    print("=" * 60)

    session = SessionLocal()

    # 1 query: SELECT users
    users = session.query(User).limit(10).all()
    print(f"\n📊 Query 1: Fetched {len(users)} users")

    # N queries: SELECT posts for each user
    for i, user in enumerate(users, 1):
        posts = user.posts  # Lazy loading triggers query!
        print(f"📊 Query {i+1}: Fetched {len(posts)} posts for {user.name}")

    session.close()

    print(f"\n⚠️  Total queries: {len(users) + 1} (1 + {len(users)})")
    print("💸 Cost: High database load, slow performance")


# ============================================
# SOLUTION 1: EAGER LOADING (JOIN)
# ============================================

def solution_eager_loading():
    """
    ✅ SOLUÇÃO 1: Eager Loading com JOIN

    2 queries total:
    1. SELECT users
    2. SELECT posts WHERE user_id IN (...)
    """
    print("\n" + "=" * 60)
    print("✅ SOLUTION 1: EAGER LOADING")
    print("=" * 60)

    session = SessionLocal()

    # Query 1: SELECT users
    # Query 2: SELECT posts WHERE user_id IN (...)
    users = session.query(User).options(
        selectinload(User.posts)
    ).limit(10).all()

    print(f"\n📊 Fetched {len(users)} users with posts")

    # Access posts - NO additional queries!
    for user in users:
        posts = user.posts  # Already loaded!
        print(f"✅ {user.name}: {len(posts)} posts (no query)")

    session.close()

    print(f"\n✅ Total queries: 2")
    print("💰 Cost: Low, efficient")


# ============================================
# SOLUTION 2: AGGREGATE
# ============================================

def solution_aggregate():
    """
    ✅ SOLUÇÃO 2: Aggregate (COUNT) em 1 query

    Quando você só precisa do COUNT, não dos dados
    """
    print("\n" + "=" * 60)
    print("✅ SOLUTION 2: AGGREGATE (COUNT)")
    print("=" * 60)

    session = SessionLocal()

    # Single query with COUNT
    results = session.query(
        User.id,
        User.name,
        func.count(Post.id).label('post_count')
    ).outerjoin(Post).group_by(User.id).limit(10).all()

    print(f"\n📊 Single query with aggregate")

    for user_id, user_name, post_count in results:
        print(f"✅ {user_name}: {post_count} posts")

    session.close()

    print(f"\n✅ Total queries: 1")
    print("💰 Cost: Very low, fastest")


# ============================================
# SOLUTION 3: BATCH LOADING
# ============================================

def solution_batch_loading():
    """
    ✅ SOLUÇÃO 3: Batch loading manual

    Carrega posts em batch para todos users de uma vez
    """
    print("\n" + "=" * 60)
    print("✅ SOLUTION 3: BATCH LOADING")
    print("=" * 60)

    session = SessionLocal()

    # Query 1: Get users
    users = session.query(User).limit(10).all()
    print(f"\n📊 Query 1: Fetched {len(users)} users")

    # Query 2: Batch load posts for all users
    user_ids = [u.id for u in users]
    posts_by_user = {}

    posts = session.query(Post).filter(Post.user_id.in_(user_ids)).all()
    print(f"📊 Query 2: Fetched {len(posts)} posts in batch")

    for post in posts:
        if post.user_id not in posts_by_user:
            posts_by_user[post.user_id] = []
        posts_by_user[post.user_id].append(post)

    # Map posts to users
    for user in users:
        user._posts = posts_by_user.get(user.id, [])
        print(f"✅ {user.name}: {len(user._posts)} posts (no query)")

    session.close()

    print(f"\n✅ Total queries: 2")
    print("💰 Cost: Low")


# ============================================
# PERFORMANCE COMPARISON
# ============================================

def performance_comparison():
    """Compare performance of different approaches"""
    print("\n" + "=" * 60)
    print("⏱️  PERFORMANCE COMPARISON")
    print("=" * 60)

    def measure_time(func, name):
        start = time.time()
        func()
        elapsed = time.time() - start
        print(f"\n{name}: {elapsed:.4f} seconds")
        return elapsed

    # Warm up
    session = SessionLocal()
    session.query(User).first()
    session.close()

    # Test N+1 problem
    time_n_plus_1 = measure_time(n_plus_1_problem, "N+1 Problem")

    # Test eager loading
    time_eager = measure_time(solution_eager_loading, "Eager Loading")

    # Test aggregate
    time_aggregate = measure_time(solution_aggregate, "Aggregate")

    # Test batch
    time_batch = measure_time(solution_batch_loading, "Batch Loading")

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"N+1 Problem:     {time_n_plus_1:.4f}s (baseline)")
    print(f"Eager Loading:   {time_eager:.4f}s ({time_n_plus_1/time_eager:.1f}x faster)")
    print(f"Aggregate:       {time_aggregate:.4f}s ({time_n_plus_1/time_aggregate:.1f}x faster)")
    print(f"Batch Loading:   {time_batch:.4f}s ({time_n_plus_1/time_batch:.1f}x faster)")


# ============================================
# REAL-WORLD EXAMPLE: API ENDPOINT
# ============================================

def api_endpoint_comparison():
    """
    Simula endpoint de API:
    GET /users?include=posts
    """
    print("\n" + "=" * 60)
    print("🌐 REAL-WORLD: API ENDPOINT")
    print("=" * 60)

    def bad_endpoint():
        """❌ BAD: N+1 problem"""
        session = SessionLocal()
        users = session.query(User).limit(10).all()

        result = []
        for user in users:
            result.append({
                "id": user.id,
                "name": user.name,
                "posts": [
                    {"id": p.id, "title": p.title}
                    for p in user.posts  # N queries!
                ]
            })

        session.close()
        return result

    def good_endpoint():
        """✅ GOOD: Eager loading"""
        session = SessionLocal()
        users = session.query(User).options(
            selectinload(User.posts)
        ).limit(10).all()

        result = []
        for user in users:
            result.append({
                "id": user.id,
                "name": user.name,
                "posts": [
                    {"id": p.id, "title": p.title}
                    for p in user.posts  # Already loaded!
                ]
            })

        session.close()
        return result

    print("\n❌ Bad Endpoint (N+1):")
    start = time.time()
    bad_result = bad_endpoint()
    bad_time = time.time() - start
    print(f"   Time: {bad_time:.4f}s")
    print(f"   Queries: 11 (1 + 10)")

    print("\n✅ Good Endpoint (Eager Loading):")
    start = time.time()
    good_result = good_endpoint()
    good_time = time.time() - start
    print(f"   Time: {good_time:.4f}s")
    print(f"   Queries: 2")

    print(f"\n📊 Improvement: {bad_time/good_time:.1f}x faster!")


# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("🐛 N+1 PROBLEM DEMONSTRATION")
    print("=" * 60)
    print()
    print("This script demonstrates the N+1 query problem")
    print("and various solutions in SQLAlchemy.")
    print()

    # Seed data
    seed_data()

    # Demonstrate N+1 problem
    n_plus_1_problem()

    # Show solutions
    solution_eager_loading()
    solution_aggregate()
    solution_batch_loading()

    # Performance comparison
    performance_comparison()

    # Real-world example
    api_endpoint_comparison()

    print("\n" + "=" * 60)
    print("✅ RECOMMENDATIONS")
    print("=" * 60)
    print("1. Always use eager loading (.options(selectinload()))")
    print("2. Use aggregate queries when you only need counts")
    print("3. Monitor slow queries with EXPLAIN ANALYZE")
    print("4. Set up database query logging in production")
    print("5. Use APM tools (New Relic, Datadog) to detect N+1")


if __name__ == "__main__":
    main()
