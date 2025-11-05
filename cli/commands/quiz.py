"""
Comandos para testar conhecimento com quiz interativo
"""

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich import box
import random

app = typer.Typer()
console = Console()

# Quiz questions by topic
QUIZ_QUESTIONS = {
    "fundamentos": [
        {
            "question": "Qual a diferença entre Thread e Process?",
            "options": [
                "A) Thread compartilha memória, Process não",
                "B) Process é mais rápido que Thread",
                "C) Thread não pode rodar em paralelo",
                "D) Não há diferença"
            ],
            "correct": "A",
            "explanation": "Threads compartilham o mesmo espaço de memória, enquanto Processes têm memória isolada."
        },
        {
            "question": "O que é GIL (Global Interpreter Lock)?",
            "options": [
                "A) Um tipo de threading",
                "B) Um lock que permite apenas 1 thread executar Python bytecode por vez",
                "C) Um tipo de processo",
                "D) Um framework de concorrência"
            ],
            "correct": "B",
            "explanation": "GIL é um mutex que protege acesso a objetos Python, permitindo apenas uma thread executar por vez."
        },
        {
            "question": "Quando usar async/await ao invés de threads?",
            "options": [
                "A) Sempre",
                "B) Para operações CPU-bound",
                "C) Para operações I/O-bound (network, disk)",
                "D) Nunca"
            ],
            "correct": "C",
            "explanation": "Async/await é ideal para I/O-bound. Para CPU-bound, use multiprocessing."
        },
    ],
    "database": [
        {
            "question": "O que é o problema N+1?",
            "options": [
                "A) Fazer N queries em loop ao invés de 1 query com JOIN",
                "B) Ter N+1 tabelas no banco",
                "C) Usar N+1 índices",
                "D) Ter N+1 conexões"
            ],
            "correct": "A",
            "explanation": "N+1 é quando fazemos 1 query principal + N queries em loop (uma para cada item)."
        },
        {
            "question": "Qual index usar para range queries (BETWEEN)?",
            "options": [
                "A) Hash index",
                "B) B-Tree index",
                "C) Bitmap index",
                "D) Não precisa de index"
            ],
            "correct": "B",
            "explanation": "B-Tree é ideal para range queries. Hash index só funciona para equality (=)."
        },
    ],
    "architecture": [
        {
            "question": "Quando usar Cache-Aside vs Write-Through?",
            "options": [
                "A) Cache-Aside para reads, Write-Through para writes",
                "B) Sempre usar Cache-Aside",
                "C) Cache-Aside = lazy loading, Write-Through = consistência forte",
                "D) São a mesma coisa"
            ],
            "correct": "C",
            "explanation": "Cache-Aside é mais comum (lazy). Write-Through garante cache sempre atualizado."
        },
    ],
    "system_design": [
        {
            "question": "Twitter: Push (write fanout) vs Pull (read fanout)?",
            "options": [
                "A) Push para todos usuários",
                "B) Pull para todos usuários",
                "C) Hybrid: Push para users normais, Pull para celebridades",
                "D) Não importa"
            ],
            "correct": "C",
            "explanation": "Twitter usa hybrid: Push (<5k followers) e Pull (>5k) para evitar write amplification."
        },
        {
            "question": "Como escalar para 100M conexões WebSocket?",
            "options": [
                "A) 1 servidor gigante",
                "B) Múltiplos servidores + Redis Pub/Sub",
                "C) Não é possível",
                "D) Usar HTTP ao invés de WebSocket"
            ],
            "correct": "B",
            "explanation": "1 servidor suporta ~65k conexões. Usar múltiplos + Redis para routing."
        },
    ]
}


@app.command("start")
def start_quiz(
    topic: str = typer.Option("random", help="Tópico: fundamentos, database, architecture, system_design, random"),
    num_questions: int = typer.Option(5, help="Número de questões"),
):
    """🎯 Iniciar quiz interativo"""
    console.print()
    console.print("[bold cyan]🎯 Quiz de Backend[/bold cyan]\n")

    # Select questions
    if topic == "random":
        all_questions = []
        for topic_questions in QUIZ_QUESTIONS.values():
            all_questions.extend(topic_questions)
        questions = random.sample(all_questions, min(num_questions, len(all_questions)))
    elif topic in QUIZ_QUESTIONS:
        questions = random.sample(
            QUIZ_QUESTIONS[topic],
            min(num_questions, len(QUIZ_QUESTIONS[topic]))
        )
    else:
        console.print(f"[red]❌ Tópico inválido: {topic}[/red]")
        console.print(f"[dim]Tópicos disponíveis: {', '.join(QUIZ_QUESTIONS.keys())}, random[/dim]")
        return

    score = 0
    total = len(questions)

    for i, q in enumerate(questions, 1):
        console.print(f"[bold]Questão {i}/{total}:[/bold]")
        console.print(f"[yellow]{q['question']}[/yellow]\n")

        for option in q["options"]:
            console.print(f"  {option}")

        console.print()
        answer = Prompt.ask("Sua resposta", choices=["A", "B", "C", "D"])

        if answer.upper() == q["correct"]:
            console.print("[green]✅ Correto![/green]")
            score += 1
        else:
            console.print(f"[red]❌ Incorreto. Resposta correta: {q['correct']}[/red]")

        console.print(f"[dim]{q['explanation']}[/dim]\n")
        console.print("[dim]" + "-" * 60 + "[/dim]\n")

    # Results
    percentage = (score / total) * 100

    panel = Panel.fit(
        f"""[bold]Resultado Final:[/bold]

[cyan]Acertos:[/cyan] {score}/{total}
[cyan]Percentual:[/cyan] {percentage:.1f}%

""" + (
            "[green]🎉 Excelente! Você domina o conteúdo![/green]" if percentage >= 80 else
            "[yellow]📚 Bom! Continue estudando para melhorar![/yellow]" if percentage >= 60 else
            "[red]💪 Pratique mais e revise os conceitos![/red]"
        ),
        title="[bold cyan]Quiz Finalizado[/bold cyan]",
        border_style="cyan",
    )

    console.print(panel)
    console.print()


@app.command("topics")
def list_topics():
    """📚 Listar tópicos disponíveis para quiz"""
    console.print()
    console.print("[bold cyan]📚 Tópicos de Quiz Disponíveis[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Tópico", style="cyan", width=20)
    table.add_column("Questões", justify="center", style="green")
    table.add_column("Comando", style="yellow")

    for topic, questions in QUIZ_QUESTIONS.items():
        table.add_row(
            topic,
            str(len(questions)),
            f"study quiz start --topic {topic}"
        )

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
