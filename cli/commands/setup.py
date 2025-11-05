"""
Comandos para setup de ambientes
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import subprocess
import os

app = typer.Typer()
console = Console()


@app.command("check")
def check_requirements():
    """🔍 Verificar dependências instaladas"""
    console.print()
    console.print("[bold cyan]🔍 Verificando Dependências[/bold cyan]\n")

    requirements = {
        "python": "python3 --version",
        "docker": "docker --version",
        "docker-compose": "docker-compose --version",
        "git": "git --version",
        "pip": "pip --version",
    }

    optional = {
        "bat": "bat --version",
        "less": "less --version",
    }

    console.print("[bold]Requisitos:[/bold]")
    for name, command in requirements.items():
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            console.print(f"  ✅ {name}: [green]{version}[/green]")
        else:
            console.print(f"  ❌ {name}: [red]não encontrado[/red]")

    console.print("\n[bold]Opcionais (para melhor experiência):[/bold]")
    for name, command in optional.items():
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"  ✅ {name}: [green]instalado[/green]")
        else:
            console.print(f"  ⚠️  {name}: [yellow]não instalado (opcional)[/yellow]")

    console.print()


@app.command("install")
def install_dependencies():
    """📦 Instalar dependências Python do CLI"""
    console.print()
    console.print("[bold cyan]📦 Instalando Dependências[/bold cyan]\n")

    requirements_cli = [
        "typer[all]",
        "rich",
        "questionary",
    ]

    console.print("Instalando pacotes:")
    for package in requirements_cli:
        console.print(f"  • {package}")

    console.print()

    # Install
    result = subprocess.run(
        ["pip", "install"] + requirements_cli,
        capture_output=False,
    )

    console.print()
    if result.returncode == 0:
        console.print("[green]✅ Dependências instaladas com sucesso![/green]")
    else:
        console.print("[red]❌ Erro na instalação[/red]")

    console.print()


@app.command("docker")
def setup_docker():
    """🐳 Setup do ambiente Docker (PostgreSQL + Redis)"""
    console.print()
    console.print("[bold cyan]🐳 Setup do Ambiente Docker[/bold cyan]\n")

    docker_compose_content = """version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: backend_study_postgres
    environment:
      POSTGRES_USER: backend_user
      POSTGRES_PASSWORD: backend_pass
      POSTGRES_DB: backend_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine
    container_name: backend_study_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
"""

    # Check if docker-compose.yml exists
    if os.path.exists("docker-compose.yml"):
        console.print("[yellow]⚠️  docker-compose.yml já existe[/yellow]")
        console.print("Conteúdo sugerido:\n")
    else:
        with open("docker-compose.yml", "w") as f:
            f.write(docker_compose_content)
        console.print("[green]✅ docker-compose.yml criado![/green]\n")

    syntax = Syntax(docker_compose_content, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)

    console.print("\n[bold]Para iniciar:[/bold]")
    console.print("  [cyan]docker-compose up -d[/cyan]\n")

    console.print("[bold]Para parar:[/bold]")
    console.print("  [cyan]docker-compose down[/cyan]\n")


@app.command("env")
def setup_env():
    """⚙️  Criar arquivo .env com configurações"""
    console.print()
    console.print("[bold cyan]⚙️  Setup do arquivo .env[/bold cyan]\n")

    env_content = """# Database
DATABASE_URL=postgresql://backend_user:backend_pass@localhost:5432/backend_db

# Redis
REDIS_URL=redis://localhost:6379

# JWT
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=True
"""

    if os.path.exists(".env"):
        console.print("[yellow]⚠️  .env já existe[/yellow]")
        console.print("Conteúdo sugerido:\n")
    else:
        with open(".env", "w") as f:
            f.write(env_content)
        console.print("[green]✅ .env criado![/green]\n")

    syntax = Syntax(env_content, "bash", theme="monokai", line_numbers=True)
    console.print(syntax)

    console.print()


@app.command("project")
def setup_project():
    """🚀 Setup completo do projeto (Docker + .env + dependências)"""
    console.print()
    panel = Panel.fit(
        """[bold cyan]🚀 Setup Completo do Projeto[/bold cyan]

Este comando vai:
1. Verificar dependências
2. Criar docker-compose.yml
3. Criar .env
4. Instalar dependências Python
5. Iniciar containers Docker

        """,
        border_style="cyan",
    )
    console.print(panel)

    # Step 1: Check
    console.print("[bold]Passo 1/5:[/bold] Verificando dependências...")
    check_requirements()

    # Step 2: Docker
    console.print("[bold]Passo 2/5:[/bold] Criando docker-compose.yml...")
    setup_docker()

    # Step 3: Env
    console.print("[bold]Passo 3/5:[/bold] Criando .env...")
    setup_env()

    # Step 4: Install
    console.print("[bold]Passo 4/5:[/bold] Instalando dependências Python...")
    install_dependencies()

    # Step 5: Docker up
    console.print("[bold]Passo 5/5:[/bold] Iniciando containers Docker...")
    result = subprocess.run(["docker-compose", "up", "-d"], capture_output=True)

    if result.returncode == 0:
        console.print("[green]✅ Containers iniciados![/green]")
    else:
        console.print("[yellow]⚠️  Execute manualmente: docker-compose up -d[/yellow]")

    console.print()
    console.print("[bold green]✅ Setup Completo![/bold green]\n")

    console.print("[bold]Próximos passos:[/bold]")
    console.print("  1. Verificar containers: [cyan]docker ps[/cyan]")
    console.print("  2. Ver módulos: [cyan]study module list[/cyan]")
    console.print("  3. Ver projetos: [cyan]study project list[/cyan]")
    console.print()


if __name__ == "__main__":
    app()
