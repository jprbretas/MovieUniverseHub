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

## Importar os dados de exemplo

```bash
python -m movieuniverse importar-seed
```

Carrega o `dados/seed_playlists.json` (3 utilizadores, 10 playlists e 20 notas) e mostra um
relatório do que foi criado, com avisos sobre os problemas encontrados nos dados. Pode correr
mais do que uma vez sem duplicar nada. As decisões estão no `DECISIONS.md`, secção 6.

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
| GET | `/api/filmes/{tmdb_id}/notas` | notas dos utilizadores da aplicação para o filme e a média |
| GET | `/api/utilizadores` | lista de utilizadores |
| POST | `/api/utilizadores` | "entrar" com um nome (cria o utilizador se não existir) |
| GET | `/api/utilizadores/{id}/playlists` | playlists do utilizador, com os ids dos filmes |
| POST | `/api/utilizadores/{id}/playlists` | cria uma playlist |
| PUT | `/api/utilizadores/{id}/notas/{tmdb_id}` | dá ou altera a nota (1 a 10) do utilizador ao filme |
| DELETE | `/api/utilizadores/{id}/notas/{tmdb_id}` | retira a nota |
| GET | `/api/playlists` | todas as playlists (sem as apagadas) |
| GET | `/api/playlists/comparar?a={id}&b={id}` | compara duas playlists (rating, filmes em comum...) |
| GET | `/api/playlists/{id}` | playlist com os dados de cada filme |
| DELETE | `/api/playlists/{id}` | apaga a playlist (fica marcada como apagada) |
| PUT | `/api/playlists/{id}/filmes/{tmdb_id}` | adiciona o filme à playlist (repetir não duplica) |
| DELETE | `/api/playlists/{id}/filmes/{tmdb_id}` | tira o filme da playlist |
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

## Nota combinada

Cada filme tem uma nota de 0 a 10 que junta a média da TMDB e as notas dos utilizadores da
aplicação, pesando o número de votos de cada lado (média bayesiana com 100 votos
"imaginários" de nota 6,5). A ficha do filme mostra-a ao lado da nota da TMDB, com o número de
votos em que se baseia e uma explicação. A regra e a sua justificação estão no `DECISIONS.md`,
secção 4, e o código em `src/movieuniverse/nota_combinada.py`.

## Comparar playlists

No menu **Comparar** (ou no botão "Comparar com…" de uma playlist) escolhem-se duas playlists.
A que tiver a maior média de nota combinada dos seus filmes tem o melhor rating. Também se mostram
o número de filmes, o melhor filme de cada uma, os filmes em comum e os que só estão numa delas.
Regras no `DECISIONS.md`, secção 7.

## Segurança

- **Entradas validadas em duas camadas.** A API recusa com `422` notas fora de 1 a 10 ou que não
  sejam números inteiros (por exemplo, uma nota 20 enviada diretamente à API), e a base de dados
  tem um `CHECK` que as recusa mesmo que o código da aplicação fosse contornado.
- **SQL injection.** Todas as consultas passam pelo SQLAlchemy com parâmetros, por isso um texto
  como `ana'; DROP TABLE notas; --` é guardado como texto e nunca executado.
- **XSS.** O frontend escapa todo o texto vindo da API antes de o pôr na página (`esc()` em
  `static/js/util.js`).
- **Token da TMDB.** Fica só no `.env` (fora do Git) e nunca é devolvido pela API (`/api/health`
  diz apenas se está configurado).
- **Sem palavra-passe.** Os utilizadores identificam-se só pelo nome, como o enunciado permite,
  por isso qualquer pessoa com acesso à aplicação pode agir como outro utilizador (ver `DECISIONS.md`, secção 2).

Os testes de `tests/test_seguranca.py` reproduzem estas tentativas.

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
│   ├── rotas/             # endpoints: filmes, utilizadores, playlists
│   ├── servicos.py        # regras de negócio de utilizadores, playlists e notas
│   ├── importar.py        # importação do seed_playlists.json
│   ├── nota_combinada.py  # regra da nota combinada (função pura)
│   ├── comparacao.py      # comparação de duas playlists (função pura)
│   ├── esquemas.py        # formato do JSON de entrada e saída da API (DTOs)
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
