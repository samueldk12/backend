# 🎓 Backend Study CLI

CLI interativa para gerenciar seus estudos de backend.

## 🚀 Instalação Rápida

```bash
# 1. Instalar dependências
pip install -r requirements-cli.txt

# 2. Executar CLI
./study

# Ou adicionar ao PATH para usar globalmente
echo 'alias study="$PWD/study"' >> ~/.bashrc
source ~/.bashrc
```

## 📚 Comandos Disponíveis

### Informações Gerais

```bash
# Ver informações do repositório
study info

# Ver estatísticas
study stats

# Ver roadmap de estudos
study roadmap
```

### Módulos Teóricos

```bash
# Listar todos os módulos
study module list

# Ver detalhes de um módulo
study module show 01

# Ler teoria completa
study module read 01

# Listar exemplos do módulo
study module examples 01

# Executar exemplo
study module run 01 1
```

### Projetos

```bash
# Listar todos os projetos
study project list

# Listar apenas exercícios práticos
study project list --type practice

# Listar apenas projetos de entrevista
study project list --type interview

# Ver detalhes de um projeto
study project show practice 01
study project show interview 07

# Ver roadmap de entrevistas
study project roadmap
```

### Tracking de Progresso

```bash
# Ver seu progresso
study progress show

# Marcar item como concluído
study progress mark module 01
study progress mark exercise 02
study progress mark interview 07

# Exportar progresso
study progress export

# Resetar progresso
study progress reset --yes
```

### Quiz Interativo

```bash
# Iniciar quiz aleatório
study quiz start

# Quiz de tópico específico
study quiz start --topic fundamentos
study quiz start --topic database
study quiz start --topic system_design

# Listar tópicos disponíveis
study quiz topics

# Quiz com 10 questões
study quiz start --num-questions 10
```

### Setup de Ambiente

```bash
# Verificar dependências
study setup check

# Instalar dependências Python
study setup install

# Criar docker-compose.yml
study setup docker

# Criar arquivo .env
study setup env

# Setup completo (tudo de uma vez)
study setup project
```

## 🎯 Exemplos de Uso

### 1. Começar a estudar um módulo

```bash
# Ver módulos disponíveis
study module list

# Ler teoria do módulo 01 (Fundamentos)
study module read 01

# Executar primeiro exemplo
study module run 01 1

# Marcar como concluído
study progress mark module 01
```

### 2. Estudar projeto de entrevista

```bash
# Listar projetos de entrevista
study project list --type interview

# Ler sobre Twitter Clone
study project show interview 07

# Ver roadmap completo de entrevistas
study project roadmap
```

### 3. Testar conhecimento

```bash
# Quiz aleatório com 5 questões
study quiz start

# Quiz específico de banco de dados
study quiz start --topic database --num-questions 10

# Ver tópicos disponíveis
study quiz topics
```

### 4. Setup do ambiente

```bash
# Setup completo (recomendado para iniciantes)
study setup project

# Ou passo a passo:
study setup check          # Verificar dependências
study setup docker         # Criar docker-compose.yml
study setup env            # Criar .env
docker-compose up -d       # Iniciar containers
```

### 5. Acompanhar progresso

```bash
# Ver progresso geral
study progress show

# Marcar módulo como concluído
study progress mark module 01

# Marcar exercício como concluído
study progress mark exercise 02

# Marcar projeto de entrevista como concluído
study progress mark interview 07

# Exportar progresso para JSON
study progress export
```

## 🎨 Features

### ✨ Interface Rica

- **Tabelas formatadas** para listar módulos e projetos
- **Syntax highlighting** para código e configs
- **Progress bars** para tracking de progresso
- **Painéis coloridos** para melhor visualização

### 📊 Tracking de Progresso

- Salva progresso localmente em `~/.backend_study_progress.json`
- Mostra % de conclusão por categoria
- Exporta progresso para JSON
- Rastreia tempo de estudo

### 🎯 Quiz Interativo

- Perguntas de múltipla escolha
- Feedback imediato
- Explicações detalhadas
- Múltiplos tópicos

### ⚙️ Setup Automático

- Verifica dependências instaladas
- Cria docker-compose.yml
- Cria arquivo .env
- Instala pacotes Python
- Inicia containers Docker

## 🛠️ Estrutura da CLI

```
cli/
├── __init__.py
├── main.py              # Entry point principal
├── commands/            # Comandos da CLI
│   ├── __init__.py
│   ├── modules.py       # Gerenciar módulos
│   ├── projects.py      # Gerenciar projetos
│   ├── progress.py      # Tracking de progresso
│   ├── quiz.py          # Quiz interativo
│   └── setup.py         # Setup de ambiente
└── utils/               # Utilitários
    ├── __init__.py
    └── display.py       # Funções de display
```

## 📝 Adicionando Novos Comandos

### Exemplo: Adicionar novo comando

```python
# cli/commands/new_command.py

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command("action")
def my_action():
    """Descrição da ação"""
    console.print("Hello World!")

if __name__ == "__main__":
    app()
```

```python
# cli/main.py

from cli.commands import new_command

# Add subcommand
app.add_typer(new_command.app, name="new", help="Novo comando")
```

## 🎓 Dicas de Uso

### Para Iniciantes

```bash
# 1. Setup completo
study setup project

# 2. Ver roadmap
study roadmap

# 3. Começar pelo módulo 01
study module read 01
study module run 01 1

# 4. Praticar com quiz
study quiz start --topic fundamentos
```

### Para Preparação de Entrevistas

```bash
# 1. Ver roadmap de entrevistas
study project roadmap

# 2. Estudar projetos por ordem de frequência
study project show interview 01  # URL Shortener
study project show interview 03  # LRU Cache
study project show interview 07  # Twitter

# 3. Quiz de system design
study quiz start --topic system_design

# 4. Tracking de progresso
study progress show
```

### Para Prática Hands-on

```bash
# 1. Setup do ambiente
study setup project

# 2. Executar exemplos
study module run 01 1  # Fundamentos
study module run 03 1  # Banco de dados
study module run 08 1  # Estruturas de dados

# 3. Marcar como concluído
study progress mark module 01
```

## 🐛 Troubleshooting

### Erro: "Module not found"

```bash
# Certifique-se de executar do diretório raiz
cd /caminho/para/backend

# Ou adicione ao PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$PWD
```

### Erro: "Permission denied"

```bash
# Torne o script executável
chmod +x study
```

### Docker não inicia

```bash
# Verificar se Docker está rodando
docker ps

# Iniciar Docker
sudo systemctl start docker

# Verificar logs
docker-compose logs
```

## 📚 Help

Todos os comandos têm help integrado:

```bash
# Help geral
study --help

# Help de um comando
study module --help
study project --help
study progress --help
study quiz --help
study setup --help

# Help de um subcomando
study module list --help
study quiz start --help
```

## 🎉 Features Futuras

- [ ] Modo interativo com questionary
- [ ] Integração com LeetCode API
- [ ] Gráficos de progresso (matplotlib)
- [ ] Timer de estudo (Pomodoro)
- [ ] Notas e anotações
- [ ] Sync com GitHub Gists
- [ ] Estatísticas avançadas
- [ ] Recomendações personalizadas

## 🤝 Contribuindo

Para adicionar novos recursos à CLI:

1. Criar novo arquivo em `cli/commands/`
2. Adicionar comando ao `cli/main.py`
3. Atualizar este README
4. Testar: `./study <novo-comando>`

---

**Divirta-se estudando! 🚀**
