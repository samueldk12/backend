# Projeto Prático: Rede Social

Construa uma rede social completa do zero, aprendendo backend step-by-step.

## Estrutura do Projeto

```
rede-social/
├── 01-setup/              ✅ Docker, PostgreSQL, Redis
├── 02-usuarios/           ✅ CRUD básico de usuários
├── 03-autenticacao/       ✅ JWT, login, registro
├── 04-posts-texto/        ✅ Criar e listar posts
├── 05-posts-video/        ✅ Upload e streaming de vídeo
├── 06-likes-comentarios/  ✅ Interações sociais
├── 07-timeline-feed/      ✅ Feed personalizado
└── 08-notificacoes/       ✅ Real-time com WebSocket
```

## Roadmap de Aprendizado

### Semana 1-2: Fundamentos
- **Exercício 01**: Setup do ambiente
- **Exercício 02**: CRUD de usuários
- **Exercício 03**: Autenticação JWT

### Semana 3-4: Features Principais
- **Exercício 04**: Posts de texto
- **Exercício 05**: Posts de vídeo
- **Exercício 06**: Likes e comentários

### Semana 5-6: Features Avançadas
- **Exercício 07**: Timeline e Feed Algorithm
- **Exercício 08**: Notificações real-time

## Tecnologias

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL + Redis
- **ORM**: SQLAlchemy
- **Auth**: JWT (python-jose)
- **Storage**: MinIO (S3-compatible)
- **Real-time**: WebSocket
- **Queue**: Celery + Redis
- **Container**: Docker + Docker Compose

## Como Usar

```bash
# Clone o repositório
git clone <repo-url>
cd projeto-pratico

# Comece pelo exercício 01
cd exercicio-01-setup
```

Cada exercício tem seu próprio README com instruções detalhadas.

---

## Começar

➡️ [Exercício 01 - Setup](./exercicio-01-setup/README.md)
