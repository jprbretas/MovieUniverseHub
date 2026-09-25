# MovieUniverse Hub

Aplicação web para pesquisar filmes (API da TMDB), criar playlists pessoais e dar notas.
Calcula uma **nota combinada** que junta a média da TMDB às notas dos utilizadores da
aplicação, tendo em conta o número de votos de cada lado.

> Projeto em construção. Este README vai sendo completado a cada passo.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend / API REST | Python + FastAPI (Swagger em `/docs`) |
| Base de dados | SQLite, através do ORM SQLAlchemy (ficheiro `dados/movieuniverse.db`, criado no arranque) |
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

## API REST

| Método | Caminho | Descrição |
|---|---|---|
| GET | `/api/filmes?titulo=Matrix&pagina=1` | pesquisa filmes por título (20 por página) |
| GET | `/api/filmes/{tmdb_id}` | ficha de um filme (sinopse, géneros, duração, poster, nota TMDB) |
| GET | `/api/health` | estado da API e se o token da TMDB está configurado |

Erros: `404` filme inexistente · `422` parâmetros inválidos · `503` TMDB indisponível ·
`500` token da TMDB em falta ou inválido. O corpo do erro é `{"detail": "mensagem"}`.
A especificação OpenAPI completa está em `/openapi.json`.

## Testes

```bash
pytest
```

Os testes não usam a internet: as respostas da TMDB vêm de ficheiros guardados em
`tests/fixtures/tmdb/` e a base de dados é criada em memória para cada teste.

## Cache das respostas da TMDB

As respostas da TMDB ficam guardadas na própria base de dados SQLite, nas tabelas
`filmes_cache` (fichas dos filmes) e `pesquisas_cache` (páginas de pesquisa).
A lógica está em `src/movieuniverse/catalogo.py`:

1. Antes de pedir à TMDB, procura a resposta na cache.
2. Se ela tiver menos de **24 horas** (`VALIDADE_CACHE`), usa-a e não faz nenhum pedido.
3. Caso contrário, pede à TMDB e atualiza a cache.
4. Se a TMDB não responder (sem rede ou erro 429), usa a cópia antiga, se existir.

As pesquisas são normalizadas antes de montar a chave: " Matrix " e "matrix" contam como
a mesma pesquisa.

Porquê: o enunciado refere um limite de 40 pedidos a cada 10 segundos (a documentação atual
da TMDB fala em cerca de 40 por segundo e pede para respeitar o erro 429). Com a cache, abrir
de novo um filme ou uma playlist não gasta pedidos. Isto é importante para a comparação de
playlists, que precisa das notas de vários filmes ao mesmo tempo. Como a cache fica em
SQLite e não em memória, também sobrevive quando a aplicação reinicia.

## Estrutura

```
MovieUniverseHub/
├── src/movieuniverse/     # código da aplicação
│   ├── __main__.py        # ponto de entrada: "python -m movieuniverse"
│   ├── api.py             # app FastAPI: regista rotas, erros e ficheiros estáticos
│   ├── rotas/filmes.py    # endpoints /api/filmes
│   ├── dependencias.py    # injeção de dependências (sessão, cliente TMDB, catálogo)
│   ├── config.py          # leitura do .env
│   ├── tmdb.py            # cliente da API da TMDB e modelos das respostas
│   ├── catalogo.py        # TMDB + cache na base de dados
│   ├── db.py              # ligação à base de dados (SQLAlchemy)
│   ├── entidades.py       # tabelas da base de dados
│   └── static/            # frontend (HTML/CSS/JS)
├── dados/
│   └── seed_playlists.json  # dados de exemplo fornecidos (não alterar)
├── scripts/
│   └── explorar_tmdb.py   # script de exploração da API da TMDB
├── tests/                 # testes automáticos (pytest)
│   └── fixtures/tmdb/     # respostas reais da TMDB usadas nos testes
├── .env.example           # variáveis necessárias, sem valores
└── pyproject.toml         # dependências e configuração do projeto
```

## Atribuição

Este produto usa a API da TMDB, mas não é endossado nem certificado pela TMDB.

*This product uses the TMDB API but is not endorsed or certified by TMDB.*
