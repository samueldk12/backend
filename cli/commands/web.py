"""
Comando para abrir interface web do projeto
"""

import typer
from rich.console import Console
from pathlib import Path
import webbrowser
import http.server
import socketserver
import threading
import time

app = typer.Typer()
console = Console()


@app.command("open")
def open_web(
    local: bool = typer.Option(False, "--local", "-l", help="Abrir servidor local ao invés do GitHub Pages"),
    port: int = typer.Option(8000, "--port", "-p", help="Porta para servidor local"),
):
    """🌐 Abrir interface web do projeto"""

    if local:
        # Start local server
        docs_path = Path("docs")

        if not docs_path.exists():
            console.print("[red]❌ Pasta 'docs' não encontrada[/red]")
            console.print("[dim]Execute este comando na raiz do repositório[/dim]")
            return

        console.print()
        console.print(f"[cyan]🚀 Iniciando servidor local na porta {port}...[/cyan]")
        console.print()

        # Change to docs directory
        import os
        os.chdir(docs_path)

        # Create server
        Handler = http.server.SimpleHTTPRequestHandler

        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                url = f"http://localhost:{port}"
                console.print(f"[green]✅ Servidor rodando em {url}[/green]")
                console.print()
                console.print("[dim]Pressione Ctrl+C para parar o servidor[/dim]")
                console.print()

                # Open browser after short delay
                def open_browser():
                    time.sleep(1)
                    webbrowser.open(url)

                threading.Thread(target=open_browser, daemon=True).start()

                # Serve forever
                httpd.serve_forever()

        except KeyboardInterrupt:
            console.print()
            console.print("[yellow]👋 Servidor encerrado[/yellow]")
            console.print()
        except OSError as e:
            if "Address already in use" in str(e):
                console.print(f"[red]❌ Porta {port} já está em uso[/red]")
                console.print(f"[dim]Tente outro porta: --port {port + 1}[/dim]")
            else:
                console.print(f"[red]❌ Erro ao iniciar servidor: {e}[/red]")
    else:
        # Open GitHub Pages
        # TODO: Update this URL with your actual GitHub Pages URL
        url = "https://YOUR_USERNAME.github.io/backend-study-repository/"

        console.print()
        console.print("[cyan]🌐 Abrindo interface web no navegador...[/cyan]")
        console.print()
        console.print(f"[dim]URL: {url}[/dim]")
        console.print()
        console.print("[yellow]💡 Dica: Use --local para testar localmente antes de fazer deploy[/yellow]")
        console.print()

        webbrowser.open(url)


@app.command("serve")
def serve_local(port: int = typer.Argument(8000, help="Porta do servidor")):
    """🖥️  Iniciar servidor local para desenvolvimento"""
    open_web(local=True, port=port)


if __name__ == "__main__":
    app()
