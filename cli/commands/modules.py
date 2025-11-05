"""
Comandos para gerenciar módulos teóricos
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich import box
from pathlib import Path
import subprocess
import os

app = typer.Typer()
console = Console()

# Módulos disponíveis
MODULES = {
    "01": {
        "name": "Fundamentos",
        "path": "01-fundamentos",
        "topics": ["CPU", "Memória", "Threads", "GIL", "Async"],
        "examples": 3,
    },
    "02": {
        "name": "Protocolos",
        "path": "02-protocolos",
        "topics": ["REST", "GraphQL", "gRPC", "WebSocket"],
        "examples": 3,
    },
    "03": {
        "name": "Banco de Dados",
        "path": "03-banco-dados",
        "topics": ["SQL", "NoSQL", "Indexes", "Transactions", "N+1"],
        "examples": 2,
    },
    "04": {
        "name": "Arquiteturas",
        "path": "04-arquiteturas",
        "topics": ["Monolith", "Microservices", "Clean", "DDD"],
        "examples": 1,
    },
    "05": {
        "name": "Performance",
        "path": "05-performance-concorrencia",
        "topics": ["Caching", "Async vs Sync", "Profiling"],
        "examples": 2,
    },
    "06": {
        "name": "Filas e Streaming",
        "path": "06-filas-streaming",
        "topics": ["Celery", "Kafka", "RabbitMQ", "Saga"],
        "examples": 1,
    },
    "07": {
        "name": "Cloud e High Architecture",
        "path": "07-cloud-high-architecture",
        "topics": ["Observability", "Logs", "Metrics", "Traces"],
        "examples": 1,
    },
    "08": {
        "name": "Estruturas de Dados",
        "path": "08-estruturas-dados",
        "topics": ["Hash Tables", "Trees", "Graphs", "Heaps", "Tries"],
        "examples": 3,
    },
}


@app.command("list")
def list_modules():
    """📚 Listar todos os módulos disponíveis"""
    console.print()
    console.print("[bold cyan]📚 Módulos Teóricos Disponíveis[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Nome", style="yellow", width=30)
    table.add_column("Tópicos", style="green", width=50)
    table.add_column("Exemplos", justify="center", style="blue")

    for module_id, module in MODULES.items():
        topics = ", ".join(module["topics"][:3])
        if len(module["topics"]) > 3:
            topics += f" +{len(module['topics']) - 3}"

        table.add_row(
            module_id,
            module["name"],
            topics,
            str(module["examples"]),
        )

    console.print(table)
    console.print()
    console.print("[dim]Use [cyan]study module show <id>[/cyan] para ver detalhes[/dim]")
    console.print()


@app.command("show")
def show_module(module_id: str = typer.Argument(..., help="ID do módulo (ex: 01)")):
    """📖 Ver detalhes de um módulo"""
    if module_id not in MODULES:
        console.print(f"[red]❌ Módulo {module_id} não encontrado[/red]")
        console.print("[dim]Use [cyan]study module list[/cyan] para ver módulos disponíveis[/dim]")
        return

    module = MODULES[module_id]
    module_path = Path(module["path"])

    console.print()
    console.print(f"[bold cyan]📚 Módulo {module_id}: {module['name']}[/bold cyan]\n")

    # Read teoria README
    teoria_path = module_path / "teoria" / "README.md"
    if teoria_path.exists():
        with open(teoria_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Show first 1000 chars
        preview = content[:1000]
        md = Markdown(preview + "\n\n[...continua...]")

        panel = Panel(
            md,
            title=f"[bold green]Preview - {module['name']}[/bold green]",
            border_style="green",
        )
        console.print(panel)
    else:
        console.print("[yellow]⚠️  Teoria não encontrada[/yellow]")

    # Show examples
    console.print(f"\n[bold]Exemplos disponíveis:[/bold]")
    exemplos_path = module_path / "exemplos"

    if exemplos_path.exists():
        examples = sorted(exemplos_path.glob("*.py"))
        for i, example in enumerate(examples, 1):
            console.print(f"  {i}. [cyan]{example.name}[/cyan]")
    else:
        console.print("[dim]  Nenhum exemplo disponível[/dim]")

    console.print()
    console.print(f"[dim]Use [cyan]study module read {module_id}[/cyan] para ler teoria completa[/dim]")
    console.print(f"[dim]Use [cyan]study module run {module_id} <exemplo>[/cyan] para executar exemplo[/dim]")
    console.print()


@app.command("read")
def read_module(module_id: str = typer.Argument(..., help="ID do módulo (ex: 01)")):
    """📖 Ler teoria completa de um módulo"""
    if module_id not in MODULES:
        console.print(f"[red]❌ Módulo {module_id} não encontrado[/red]")
        return

    module = MODULES[module_id]
    teoria_path = Path(module["path"]) / "teoria" / "README.md"

    if not teoria_path.exists():
        console.print(f"[red]❌ Teoria não encontrada em {teoria_path}[/red]")
        return

    # Use less or bat for pagination
    if os.system("which bat > /dev/null 2>&1") == 0:
        os.system(f"bat {teoria_path}")
    elif os.system("which less > /dev/null 2>&1") == 0:
        os.system(f"less {teoria_path}")
    else:
        # Fallback: print to console
        with open(teoria_path, "r", encoding="utf-8") as f:
            md = Markdown(f.read())
            console.print(md)


@app.command("run")
def run_example(
    module_id: str = typer.Argument(..., help="ID do módulo (ex: 01)"),
    example_num: int = typer.Argument(1, help="Número do exemplo"),
):
    """▶️  Executar exemplo de um módulo"""
    if module_id not in MODULES:
        console.print(f"[red]❌ Módulo {module_id} não encontrado[/red]")
        return

    module = MODULES[module_id]
    exemplos_path = Path(module["path"]) / "exemplos"

    if not exemplos_path.exists():
        console.print("[red]❌ Pasta de exemplos não encontrada[/red]")
        return

    examples = sorted(exemplos_path.glob("*.py"))

    if example_num < 1 or example_num > len(examples):
        console.print(f"[red]❌ Exemplo {example_num} não encontrado[/red]")
        console.print(f"[dim]Exemplos disponíveis: 1-{len(examples)}[/dim]")
        return

    example_path = examples[example_num - 1]

    console.print()
    console.print(f"[bold cyan]▶️  Executando: {example_path.name}[/bold cyan]\n")
    console.print("[dim]" + "=" * 60 + "[/dim]\n")

    # Execute
    try:
        result = subprocess.run(
            ["python", str(example_path)],
            capture_output=False,
            text=True,
        )

        console.print()
        console.print("[dim]" + "=" * 60 + "[/dim]")

        if result.returncode == 0:
            console.print("\n[green]✅ Executado com sucesso![/green]\n")
        else:
            console.print(f"\n[red]❌ Erro na execução (código {result.returncode})[/red]\n")

    except Exception as e:
        console.print(f"[red]❌ Erro: {e}[/red]")


@app.command("examples")
def list_examples(module_id: str = typer.Argument(..., help="ID do módulo (ex: 01)")):
    """📝 Listar exemplos de um módulo"""
    if module_id not in MODULES:
        console.print(f"[red]❌ Módulo {module_id} não encontrado[/red]")
        return

    module = MODULES[module_id]
    exemplos_path = Path(module["path"]) / "exemplos"

    console.print()
    console.print(f"[bold cyan]📝 Exemplos - Módulo {module_id}: {module['name']}[/bold cyan]\n")

    if not exemplos_path.exists():
        console.print("[yellow]⚠️  Nenhum exemplo disponível[/yellow]")
        return

    examples = sorted(exemplos_path.glob("*.py"))

    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("#", style="cyan", width=5)
    table.add_column("Nome", style="yellow", width=40)
    table.add_column("Comando", style="green")

    for i, example in enumerate(examples, 1):
        table.add_row(
            str(i),
            example.name,
            f"study module run {module_id} {i}",
        )

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
