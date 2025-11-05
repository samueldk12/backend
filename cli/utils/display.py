"""
Display utilities
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from pathlib import Path

console = Console()


def show_roadmap():
    """Show study roadmap"""
    console.print()
    console.print("[bold cyan]🗺️  Roadmap de Estudos[/bold cyan]\n")

    roadmap = """
## Cronograma de 8-12 Semanas

### Semanas 1-2: Fundamentos
- Arrays, Strings, Hash Tables
- Two pointers, sliding window
- Meta: 45 problemas

### Semanas 3-4: Estruturas Intermediárias
- Stacks, Queues, Trees, BST
- DFS, BFS, recursion
- Meta: 45 problemas

### Semanas 5-6: Algoritmos Avançados
- Graphs, Dynamic Programming
- Shortest path, topological sort
- Meta: 35 problemas

### Semanas 7-8: System Design (Low-Level)
- URL Shortener, LRU Cache, Rate Limiter
- Distributed Lock
- Meta: 4 projetos

### Semanas 9-10: System Design (High-Level)
- Twitter, Uber, WhatsApp, Netflix
- Scalability, trade-offs
- Meta: 4 designs

### Semanas 11-12: Mock Interviews
- 5+ mock coding interviews
- 2+ mock system design
- Revisão completa

## Comandos Úteis

```bash
# Ver módulos
study module list

# Ver projetos de entrevista
study project list --type interview

# Ver roadmap completo
study project roadmap

# Tracking de progresso
study progress show
```
    """

    md = Markdown(roadmap)
    console.print(md)
    console.print()
