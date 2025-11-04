# Backend Developer Cheatsheet

> Comandos e snippets essenciais para o dia a dia.

---

## 📚 Índice Rápido

- [Git](#git)
- [Docker](#docker)
- [PostgreSQL](#postgresql)
- [Redis](#redis)
- [FastAPI](#fastapi)
- [Python](#python)
- [Linux/Bash](#linuxbash)
- [Performance](#performance)
- [Debugging](#debugging)

---

## Git

### Básico
```bash
# Status
git status

# Adicionar arquivos
git add .
git add file.py

# Commit
git commit -m "feat: add user authentication"

# Push
git push origin main

# Pull
git pull origin main

# Ver histórico
git log --oneline --graph --all
```

### Branches
```bash
# Criar e mudar
git checkout -b feature/new-feature

# Listar
git branch -a

# Deletar local
git branch -d feature/old-feature

# Deletar remote
git push origin --delete feature/old-feature
```

### Desfazer
```bash
# Desfazer último commit (mantém changes)
git reset --soft HEAD~1

# Desfazer último commit (descarta changes)
git reset --hard HEAD~1

# Desfazer changes de arquivo
git checkout -- file.py

# Voltar para commit específico
git reset --hard abc123
```

### Stash
```bash
# Guardar changes temporariamente
git stash

# Listar stashes
git stash list

# Aplicar último stash
git stash pop

# Aplicar stash específico
git stash apply stash@{0}
```

---

## Docker

### Básico
```bash
# Build
docker build -t myapp:latest .

# Run
docker run -p 8000:8000 myapp:latest

# Run em background
docker run -d -p 8000:8000 myapp:latest

# Ver containers rodando
docker ps

# Ver todos (incluindo parados)
docker ps -a

# Logs
docker logs container_name
docker logs -f container_name  # Follow

# Stop
docker stop container_name

# Remove
docker rm container_name

# Remove imagem
docker rmi image_name
```

### Docker Compose
```bash
# Start
docker-compose up

# Start em background
docker-compose up -d

# Stop
docker-compose down

# Ver logs
docker-compose logs -f

# Rebuild
docker-compose up --build

# Executar comando em container
docker-compose exec api bash
docker-compose exec db psql -U postgres
```

### Cleanup
```bash
# Remover containers parados
docker container prune

# Remover imagens não usadas
docker image prune

# Remover tudo não usado
docker system prune -a

# Ver uso de disco
docker system df
```

---

## PostgreSQL

### Connection
```bash
# Conectar
psql -h localhost -U postgres -d mydb

# Conectar via docker-compose
docker-compose exec db psql -U postgres
```

### Database
```sql
-- Listar databases
\l

-- Criar database
CREATE DATABASE mydb;

-- Conectar a database
\c mydb

-- Deletar database
DROP DATABASE mydb;
```

### Tables
```sql
-- Listar tabelas
\dt

-- Descrever tabela
\d users

-- Criar tabela
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Deletar tabela
DROP TABLE users;
```

### Queries
```sql
-- Select
SELECT * FROM users LIMIT 10;
SELECT id, email FROM users WHERE active = true;

-- Insert
INSERT INTO users (email, name) VALUES ('joao@example.com', 'João');

-- Update
UPDATE users SET name = 'João Silva' WHERE id = 1;

-- Delete
DELETE FROM users WHERE id = 1;

-- Count
SELECT COUNT(*) FROM users;

-- Join
SELECT u.name, p.title
FROM users u
JOIN posts p ON u.id = p.user_id;
```

### Indexes
```sql
-- Criar index
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_user_id ON posts(user_id);

-- Listar indexes
\di

-- Deletar index
DROP INDEX idx_users_email;
```

### Performance
```sql
-- EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'joao@example.com';

-- Ver queries lentas (requer pg_stat_statements)
SELECT
    query,
    calls,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Ver tamanho das tabelas
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
```

---

## Redis

### Connection
```bash
# Conectar
redis-cli

# Conectar via docker-compose
docker-compose exec redis redis-cli

# Conectar com senha
redis-cli -a password
```

### Basic Commands
```bash
# Set/Get
SET key value
GET key

# Set com TTL (segundos)
SETEX key 3600 value

# Delete
DEL key

# Verificar se existe
EXISTS key

# Ver TTL
TTL key

# Ver todas as keys (CUIDADO em produção!)
KEYS *

# Flush database (deleta tudo!)
FLUSHDB

# Info
INFO
```

### Data Structures
```bash
# Hash
HSET user:1 name "João"
HSET user:1 email "joao@example.com"
HGET user:1 name
HGETALL user:1

# List
LPUSH mylist "item1"
LPUSH mylist "item2"
LRANGE mylist 0 -1

# Set
SADD myset "member1"
SADD myset "member2"
SMEMBERS myset

# Sorted Set
ZADD leaderboard 100 "player1"
ZADD leaderboard 200 "player2"
ZRANGE leaderboard 0 -1 WITHSCORES
```

---

## FastAPI

### Basic App
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

# Rodar: uvicorn main:app --reload
```

### Request/Response
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

@app.post("/items", status_code=201)
def create_item(item: Item):
    return item

@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(404, "Item not found")
    return items[item_id]
```

### Dependency Injection
```python
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

### Background Tasks
```python
from fastapi import BackgroundTasks

def send_email(email: str):
    # Send email logic
    pass

@app.post("/users")
def create_user(user: User, background_tasks: BackgroundTasks):
    # Save user
    background_tasks.add_task(send_email, user.email)
    return user
```

---

## Python

### Virtual Environment
```bash
# Criar
python -m venv venv

# Ativar
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Desativar
deactivate

# Instalar requirements
pip install -r requirements.txt

# Gerar requirements
pip freeze > requirements.txt
```

### List Comprehensions
```python
# Básico
numbers = [i for i in range(10)]

# Com condição
evens = [i for i in range(10) if i % 2 == 0]

# Dict comprehension
squares = {i: i**2 for i in range(5)}

# Generator (eficiente em memória)
gen = (i**2 for i in range(1000000))
```

### Decorators
```python
from functools import wraps
import time

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.2f}s")
        return result
    return wrapper

@timing_decorator
def slow_function():
    time.sleep(1)
```

### Context Managers
```python
# File handling
with open('file.txt', 'r') as f:
    content = f.read()

# Database transaction
with db.begin():
    db.add(user)
    db.add(post)
    # Commit automático ou rollback em exceção

# Custom context manager
from contextlib import contextmanager

@contextmanager
def timer():
    start = time.time()
    yield
    print(f"Elapsed: {time.time() - start:.2f}s")

with timer():
    # Code to time
    pass
```

---

## Linux/Bash

### Files
```bash
# Listar
ls -la

# Criar diretório
mkdir -p path/to/dir

# Copiar
cp source.txt dest.txt
cp -r source_dir dest_dir

# Mover/Renomear
mv old.txt new.txt

# Deletar
rm file.txt
rm -rf directory/

# Ver conteúdo
cat file.txt
less file.txt
head -n 20 file.txt
tail -n 20 file.txt
tail -f logs.txt  # Follow
```

### Search
```bash
# Buscar arquivo
find . -name "*.py"
find . -type f -mtime -7  # Modificados últimos 7 dias

# Buscar em conteúdo
grep -r "search_term" .
grep -i "error" logs.txt  # Case insensitive
```

### Processes
```bash
# Ver processos
ps aux
ps aux | grep python

# Top
top
htop  # Melhor

# Kill
kill PID
kill -9 PID  # Force kill
pkill python  # Kill by name
```

### Network
```bash
# Ver portas abertas
netstat -tuln
lsof -i :8000  # Ver o que está na porta 8000

# Curl
curl http://localhost:8000/api/users
curl -X POST http://localhost:8000/api/users -H "Content-Type: application/json" -d '{"name":"João"}'

# Test connectivity
ping google.com
telnet localhost 5432
```

### Disk
```bash
# Ver uso de disco
df -h

# Ver tamanho de diretórios
du -sh *
du -h --max-depth=1

# Espaço livre
free -h
```

---

## Performance

### cProfile
```bash
# Profile script
python -m cProfile -s cumulative script.py

# Salvar output
python -m cProfile -o profile.stats script.py
```

### Memory
```bash
# Ver uso de memória
free -h

# Ver memória por processo
ps aux --sort=-%mem | head

# Memory profiler
python -m memory_profiler script.py
```

### Load Testing
```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:8000/

# wrk
wrk -t4 -c100 -d30s http://localhost:8000/

# locust (Python)
locust -f locustfile.py
```

---

## Debugging

### Python Debugger
```python
# Set breakpoint
import pdb; pdb.set_trace()
breakpoint()  # Python 3.7+

# Commands:
# n - next
# s - step into
# c - continue
# l - list code
# p variable - print
# q - quit
```

### Logging
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Exception with traceback")
```

### Timeit
```python
import timeit

# Time function
timeit.timeit("sum(range(100))", number=10000)

# Time code block
start = timeit.default_timer()
# Code to time
print(f"Elapsed: {timeit.default_timer() - start}")
```

---

## 🎯 Quick References

### HTTP Status Codes
```
200 OK              - Success
201 Created         - Resource created
204 No Content      - Success, no body
400 Bad Request     - Invalid input
401 Unauthorized    - Not authenticated
403 Forbidden       - Not authorized
404 Not Found       - Resource not found
409 Conflict        - Duplicate resource
422 Unprocessable   - Validation error
429 Too Many Requests - Rate limited
500 Internal Error  - Server error
503 Service Unavailable - Temporary issue
```

### REST Conventions
```
GET    /users          - List users
GET    /users/123      - Get user 123
POST   /users          - Create user
PUT    /users/123      - Update user 123 (full)
PATCH  /users/123      - Update user 123 (partial)
DELETE /users/123      - Delete user 123
```

### Common Ports
```
80   - HTTP
443  - HTTPS
5432 - PostgreSQL
6379 - Redis
3306 - MySQL
27017 - MongoDB
8000 - Django/FastAPI (dev)
5000 - Flask (dev)
```

---

## 💡 Tips

### Aliases (add to ~/.bashrc or ~/.zshrc)
```bash
# Docker
alias dc='docker-compose'
alias dcu='docker-compose up'
alias dcd='docker-compose down'
alias dcl='docker-compose logs -f'

# Git
alias gs='git status'
alias ga='git add'
alias gc='git commit -m'
alias gp='git push'
alias gl='git log --oneline --graph --all'

# Python
alias py='python'
alias ipy='ipython'

# Common
alias ll='ls -alh'
alias ..='cd ..'
alias ...='cd ../..'
```

### Git Commit Messages
```
feat: add user authentication
fix: resolve N+1 query in posts endpoint
refactor: extract user service
docs: update API documentation
test: add unit tests for user service
chore: upgrade dependencies
perf: optimize database queries
style: format code with black
```

---

**Salve este cheatsheet! Sempre útil! 📖**
