# MovieUniverse Hub

Aplicação web para pesquisar filmes (API da TMDB), criar playlists pessoais e dar notas.
Calcula uma **nota combinada** que junta a média da TMDB às notas dos utilizadores da
aplicação, tendo em conta o número de votos de cada lado.

> Projeto em construção. Este README vai sendo completado a cada passo.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend / API REST | Python + FastAPI (Swagger em `/docs`) |
| Base de dados | SQLite *(a partir do passo 2)* |
| Frontend | HTML/CSS/JavaScript simples, servido pelo próprio FastAPI |
| Testes | pytest |

## Pré-requisitos

- Python 3.11 ou superior
- Git
- Uma conta na [TMDB](https://www.themoviedb.org/) e o respetivo **API Read Access Token**

## Instalação (numa máquina limpa)

**Windows (PowerShell)**

```powershell
git clone <url-do-repositorio>
cd MovieUniverseHub
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env    # depois abre o .env e cola o token da TMDB
```

> Se o PowerShell bloquear o `Activate.ps1` ("running scripts is disabled"), corre uma vez
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tenta de novo.

**macOS / Linux**

```bash
git clone <url-do-repositorio>
cd MovieUniverseHub
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # depois abre o .env e cola o token da TMDB
```

## Executar

```bash
python -m movieuniverse
```

No VS Code também dá para usar **F5** (configuração "MovieUniverse Hub" em `.vscode/launch.json`):
sobe o servidor com o debugger e abre o navegador.

- Aplicação: <http://127.0.0.1:8000>
- Documentação da API (Swagger): <http://127.0.0.1:8000/docs>

## Testes

```bash
pytest
```

## Estrutura

```
MovieUniverseHub/
├── src/movieuniverse/     # código da aplicação
│   ├── api.py             # app FastAPI (rotas + ficheiros estáticos)
│   ├── config.py          # leitura do .env
│   ├── __main__.py        # ponto de entrada: "python -m movieuniverse"
│   └── static/            # frontend (HTML/CSS/JS)
├── tests/                 # testes automáticos (pytest)
├── .env.example           # variáveis necessárias, sem valores
└── pyproject.toml         # dependências e configuração do projeto
```

## Atribuição

Este produto usa a API da TMDB, mas não é endossado nem certificado pela TMDB.

*This product uses the TMDB API but is not endorsed or certified by TMDB.*
