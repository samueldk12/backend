"""
Comandos para tracking de progresso
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.panel import Panel
from rich import box
from pathlib import Path
import json
from datetime import datetime

app = typer.Typer()
console = Console()

# Progress file
PROGRESS_FILE = Path.home() / ".backend_study_progress.json"


def load_progress():
    """Carregar progresso do arquivo"""
    if not PROGRESS_FILE.exists():
        return {
            "modules": {},
            "exercises": {},
            "interview_projects": {},
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

    with open(PROGRESS_FILE, "r") as f:
        return json.load(f)


def save_progress(data):
    """Salvar progresso no arquivo"""
    data["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.command("show")
def show_progress():
    """📊 Ver seu progresso geral"""
    progress_data = load_progress()

    console.print()
    console.print("[bold cyan]📊 Seu Progresso de Estudos[/bold cyan]\n")

    # Summary
    total_modules = 8
    total_exercises = 8
    total_interviews = 12

    completed_modules = len([m for m in progress_data.get("modules", {}).values() if m.get("completed")])
    completed_exercises = len([e for e in progress_data.get("exercises", {}).values() if e.get("completed")])
    completed_interviews = len([i for i in progress_data.get("interview_projects", {}).values() if i.get("completed")])

    # Progress bars
    with Progress(
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        progress.add_task(
            f"Módulos Teóricos      [{completed_modules}/{total_modules}]",
            total=total_modules,
            completed=completed_modules,
        )
        progress.add_task(
            f"Exercícios Práticos   [{completed_exercises}/{total_exercises}]",
            total=total_exercises,
            completed=completed_exercises,
        )
        progress.add_task(
            f"Projetos de Entrevista [{completed_interviews}/{total_interviews}]",
            total=total_interviews,
            completed=completed_interviews,
        )

    # Total
    total_items = total_modules + total_exercises + total_interviews
    completed_items = completed_modules + completed_exercises + completed_interviews
    overall_percentage = (completed_items / total_items) * 100

    console.print()
    console.print(f"[bold]Progresso Geral:[/bold] [cyan]{completed_items}/{total_items}[/cyan] ([green]{overall_percentage:.1f}%[/green])")

    # Time stats
    started = datetime.fromisoformat(progress_data.get("started_at", datetime.now().isoformat()))
    days_studying = (datetime.now() - started).days

    console.print(f"[bold]Estudando há:[/bold] [yellow]{days_studying} dias[/yellow]")

    console.print()


@app.command("mark")
def mark_completed(
    type: str = typer.Argument(..., help="Tipo: module, exercise, interview"),
    id: str = typer.Argument(..., help="ID do item (ex: 01)"),
):
    """✅ Marcar item como concluído"""
    progress_data = load_progress()

    if type == "module":
        if "modules" not in progress_data:
            progress_data["modules"] = {}

        progress_data["modules"][id] = {
            "completed": True,
            "completed_at": datetime.now().isoformat(),
        }
        item_name = f"Módulo {id}"

    elif type == "exercise":
        if "exercises" not in progress_data:
            progress_data["exercises"] = {}

        progress_data["exercises"][id] = {
            "completed": True,
            "completed_at": datetime.now().isoformat(),
        }
        item_name = f"Exercício {id}"

    elif type == "interview":
        if "interview_projects" not in progress_data:
            progress_data["interview_projects"] = {}

        progress_data["interview_projects"][id] = {
            "completed": True,
            "completed_at": datetime.now().isoformat(),
        }
        item_name = f"Projeto de Entrevista {id}"

    else:
        console.print("[red]❌ Tipo inválido. Use: module, exercise, interview[/red]")
        return

    save_progress(progress_data)

    console.print()
    console.print(f"[green]✅ {item_name} marcado como concluído![/green]")
    console.print()


@app.command("reset")
def reset_progress(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Confirmar reset"),
):
    """🔄 Resetar todo o progresso"""
    if not confirm:
        console.print("[yellow]⚠️  Isso vai resetar todo seu progresso![/yellow]")
        console.print("Use [cyan]--yes[/cyan] para confirmar")
        return

    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    console.print("[green]✅ Progresso resetado![/green]")


@app.command("export")
def export_progress():
    """💾 Exportar progresso para JSON"""
    progress_data = load_progress()

    output_file = Path("my_progress.json")
    with open(output_file, "w") as f:
        json.dump(progress_data, f, indent=2)

    console.print()
    console.print(f"[green]✅ Progresso exportado para {output_file}[/green]")
    console.print()


if __name__ == "__main__":
    app()
