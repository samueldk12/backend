#!/usr/bin/env python3
"""
Backend Study CLI - Main Entry Point

Uma CLI interativa para gerenciar seus estudos de backend
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from pathlib import Path

# Import commands
from cli.commands import modules, projects, progress, quiz, setup, web

app = typer.Typer(
    name="study",
    help="🎓 CLI para gerenciar seus estudos de backend",
    add_completion=True,
)

console = Console()

# Add subcommands
app.add_typer(modules.app, name="module", help="📚 Gerenciar módulos teóricos")
app.add_typer(projects.app, name="project", help="🚀 Gerenciar projetos práticos")
app.add_typer(progress.app, name="progress", help="📊 Tracking de progresso")
app.add_typer(quiz.app, name="quiz", help="🎯 Testar conhecimento")
app.add_typer(setup.app, name="setup", help="⚙️  Setup de ambientes")
app.add_typer(web.app, name="web", help="🌐 Interface web interativa")


@app.command()
def info():
    """📖 Informações sobre o repositório"""
    console.print()

    panel = Panel.fit(
        """[bold cyan]🎓 Backend Study Repository[/bold cyan]

[yellow]Repositório completo de estudos de backend[/yellow]
Do nível júnior ao sênior

[bold]Conteúdo:[/bold]
• 8 Módulos Teóricos
• 8 Exercícios Práticos (Rede Social)
• 12 Projetos de Entrevista
• 9 Guias de Suporte

[bold]Comandos disponíveis:[/bold]
• [cyan]study module[/cyan] - Gerenciar módulos
• [cyan]study project[/cyan] - Gerenciar projetos
• [cyan]study progress[/cyan] - Ver progresso
• [cyan]study quiz[/cyan] - Testar conhecimento
• [cyan]study setup[/cyan] - Setup de ambiente
• [cyan]study web[/cyan] - Interface web interativa

Use [cyan]study <comando> --help[/cyan] para mais informações
        """,
        title="[bold green]Backend Study CLI v1.0.0[/bold green]",
        border_style="green",
    )

    console.print(panel)
    console.print()


@app.command()
def stats():
    """📈 Estatísticas do repositório"""
    console.print()
    console.print("[bold cyan]📊 Estatísticas do Repositório[/bold cyan]\n")

    # Create table
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Categoria", style="cyan", width=30)
    table.add_column("Quantidade", justify="right", style="green")
    table.add_column("Status", justify="center")

    table.add_row("Módulos Teóricos", "8", "✅")
    table.add_row("Exercícios Práticos", "8", "✅")
    table.add_row("Projetos de Entrevista", "12", "✅")
    table.add_row("Guias de Suporte", "9", "✅")
    table.add_row("Exemplos Executáveis", "13+", "✅")
    table.add_row("Linhas de Código", "30,000+", "✅")

    console.print(table)
    console.print()


@app.command()
def roadmap():
    """🗺️  Ver roadmap de estudos"""
    from cli.utils.display import show_roadmap
    show_roadmap()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    🎓 Backend Study CLI

    Use --help para ver comandos disponíveis
    """
    if ctx.invoked_subcommand is None:
        info()


if __name__ == "__main__":
    app()
