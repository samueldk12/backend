"""
Comandos para gerenciar projetos práticos e projetos de entrevista
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich import box
from pathlib import Path
import os

app = typer.Typer()
console = Console()

# Exercícios práticos (rede social)
EXERCISES = {
    "01": {"name": "Setup (Docker, PostgreSQL, Redis)", "path": "projeto-pratico/exercicio-01-setup"},
    "02": {"name": "CRUD Usuários", "path": "projeto-pratico/exercicio-02-usuarios"},
    "03": {"name": "Autenticação JWT", "path": "projeto-pratico/exercicio-03-autenticacao"},
    "04": {"name": "Posts de Texto", "path": "projeto-pratico/exercicio-04-posts-texto"},
    "05": {"name": "Posts de Vídeo", "path": "projeto-pratico/exercicio-05-posts-video"},
    "06": {"name": "Likes e Comentários", "path": "projeto-pratico/exercicio-06-likes-comentarios"},
    "07": {"name": "Timeline e Feed", "path": "projeto-pratico/exercicio-07-timeline-feed"},
    "08": {"name": "Notificações Real-time", "path": "projeto-pratico/exercicio-08-notificacoes-realtime"},
}

# Projetos de entrevista
INTERVIEW_PROJECTS = {
    "01": {"name": "URL Shortener", "type": "Low-Level", "freq": "⭐⭐⭐⭐⭐"},
    "02": {"name": "Rate Limiter", "type": "Low-Level", "freq": "⭐⭐⭐⭐"},
    "03": {"name": "LRU Cache", "type": "Low-Level", "freq": "⭐⭐⭐⭐⭐"},
    "04": {"name": "Distributed Lock", "type": "Low-Level", "freq": "⭐⭐⭐⭐"},
    "05": {"name": "Consistent Hashing", "type": "Low-Level", "freq": "⭐⭐⭐"},
    "06": {"name": "Bloom Filter", "type": "Low-Level", "freq": "⭐⭐⭐"},
    "07": {"name": "Twitter Clone", "type": "High-Level", "freq": "⭐⭐⭐⭐⭐"},
    "08": {"name": "Uber/Lyft", "type": "High-Level", "freq": "⭐⭐⭐⭐⭐"},
    "09": {"name": "WhatsApp", "type": "High-Level", "freq": "⭐⭐⭐⭐⭐"},
    "10": {"name": "Netflix", "type": "High-Level", "freq": "⭐⭐⭐⭐"},
    "11": {"name": "Airbnb", "type": "High-Level", "freq": "⭐⭐⭐⭐"},
    "12": {"name": "Instagram", "type": "High-Level", "freq": "⭐⭐⭐⭐"},
}


@app.command("list")
def list_projects(
    type: str = typer.Option("all", help="Tipo: all, practice, interview")
):
    """📋 Listar projetos disponíveis"""
    console.print()

    if type in ["all", "practice"]:
        console.print("[bold cyan]🚀 Exercícios Práticos (Rede Social)[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Nome", style="yellow", width=50)

        for ex_id, exercise in EXERCISES.items():
            table.add_row(ex_id, exercise["name"])

        console.print(table)
        console.print()

    if type in ["all", "interview"]:
        console.print("[bold cyan]💼 Projetos de Entrevista[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Nome", style="yellow", width=25)
        table.add_column("Tipo", style="blue", width=15)
        table.add_column("Frequência", style="green", justify="center")

        for proj_id, project in INTERVIEW_PROJECTS.items():
            table.add_row(
                proj_id,
                project["name"],
                project["type"],
                project["freq"],
            )

        console.print(table)
        console.print()

    console.print("[dim]Use [cyan]study project show <type> <id>[/cyan] para ver detalhes[/dim]")
    console.print()


@app.command("show")
def show_project(
    type: str = typer.Argument(..., help="Tipo: practice ou interview"),
    project_id: str = typer.Argument(..., help="ID do projeto (ex: 01)"),
):
    """📖 Ver detalhes de um projeto"""
    if type == "practice":
        if project_id not in EXERCISES:
            console.print(f"[red]❌ Exercício {project_id} não encontrado[/red]")
            return

        exercise = EXERCISES[project_id]
        readme_path = Path(exercise["path"]) / "README.md"

    elif type == "interview":
        if project_id not in INTERVIEW_PROJECTS:
            console.print(f"[red]❌ Projeto {project_id} não encontrado[/red]")
            return

        project = INTERVIEW_PROJECTS[project_id]
        readme_path = Path(f"projetos-entrevista/{project_id}-{project['name'].lower().replace(' ', '-').replace('/', '-')}") / "README.md"

    else:
        console.print("[red]❌ Tipo inválido. Use 'practice' ou 'interview'[/red]")
        return

    if not readme_path.exists():
        console.print(f"[red]❌ README não encontrado em {readme_path}[/red]")
        return

    # Use less or bat for pagination
    if os.system("which bat > /dev/null 2>&1") == 0:
        os.system(f"bat {readme_path}")
    elif os.system("which less > /dev/null 2>&1") == 0:
        os.system(f"less {readme_path}")
    else:
        # Fallback: print to console
        with open(readme_path, "r", encoding="utf-8") as f:
            md = Markdown(f.read())
            console.print(md)


@app.command("roadmap")
def show_interview_roadmap():
    """🗺️  Ver roadmap de preparação para entrevistas"""
    roadmap_path = Path("projetos-entrevista/ROADMAP_ENTREVISTAS.md")

    if not roadmap_path.exists():
        console.print("[red]❌ Roadmap não encontrado[/red]")
        return

    # Use less or bat for pagination
    if os.system("which bat > /dev/null 2>&1") == 0:
        os.system(f"bat {roadmap_path}")
    elif os.system("which less > /dev/null 2>&1") == 0:
        os.system(f"less {roadmap_path}")
    else:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            md = Markdown(f.read())
            console.print(md)


if __name__ == "__main__":
    app()
