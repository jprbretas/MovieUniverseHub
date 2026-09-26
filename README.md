# MovieUniverse Hub

Uma aplicação web para quem gosta de cinema: pesquisas filmes na [TMDB](https://www.themoviedb.org/),
guardas os que te interessam em playlists e dás-lhes a tua nota. Cada filme passa a ter uma
**nota combinada**, que junta a média da TMDB às notas dos utilizadores da aplicação e tem em
conta quantos votos há de cada lado. Também dá para **comparar duas playlists** e ver qual tem
o melhor rating.

A aplicação corre toda no teu computador (backend, frontend e base de dados). A única
dependência externa é a API da TMDB.

**Índice:**
[Início rápido](#início-rápido) ·
[O que a aplicação faz](#o-que-a-aplicação-faz) ·
[Instalação passo a passo](#instalação-passo-a-passo) ·
[Dados de exemplo](#importar-os-dados-de-exemplo) ·
[Exportar](#exportar-os-dados) ·
[Testes](#testes) ·
[Casos de teste](#casos-de-teste) ·
[API REST](#api-rest) ·
[Como funciona por dentro](#como-funciona-por-dentro) ·
[Estrutura](#estrutura-do-projeto) ·
[Documentação](#outros-documentos) ·
[Atribuição](#atribuição)

---

## Início rápido

Para quem já tem Python 3.11+ e Git e quer ver a aplicação a correr (Windows, PowerShell):

```powershell
git clone https://github.com/jprbretas/MovieUniverseHub.git
cd MovieUniverseHub
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env                    # abre o .env e cola o token da TMDB
python -m movieuniverse importar-seed     # dados de exemplo (opcional)
python -m movieuniverse                   # abre http://127.0.0.1:8000
```

Cada passo está explicado em [Instalação passo a passo](#instalação-passo-a-passo).

---

## O que a aplicação faz

| Ecrã | O que se pode fazer |
|---|---|
| **Pesquisa** (caixa no topo) | Procurar filmes por título. Cada card mostra o cartaz, o ano e a nota da TMDB com o número de votos, por exemplo "8,4 · 40 258 votos". Um filme sem votos mostra "sem votos". |
| **Ficha do filme** | Sinopse, géneros, duração e cartaz. Três caixas lado a lado: a **nota da TMDB**, a **nota combinada** (com o número de votos em que se baseia e uma explicação do cálculo) e a **média dos utilizadores da aplicação**. Quem entrou pode dar ou mudar a sua nota de 1 a 10. |
| **★ nos cards e na ficha** | Adicionar o filme a uma playlist ou tirá-lo de lá. |
| **Início** | As playlists de quem entrou, em destaque, e o formulário para criar uma nova. |
| **Playlist** | Os filmes da playlist, com o botão ✕ para tirar um filme, "Apagar playlist" e "Comparar com…". |
| **Comparar** | Escolhem-se duas playlists e a aplicação indica a que tem o **melhor rating** (média das notas combinadas dos filmes). Mostra também o número de filmes, o melhor filme de cada uma, os filmes em comum e os que só estão numa delas. |
| **Sobre** | O estado da API, se o token da TMDB está configurado e a atribuição à TMDB. |

**Entrar:** não há palavra-passe. Escreve-se um nome no canto superior direito e, se ainda não
existir, o utilizador é criado. É o que o enunciado permite e está explicado no
[DECISIONS.md](DECISIONS.md#utilizadores-e-dados-pessoais).

O jogo "mais alto ou mais baixo" era opcional e não foi implementado nesta entrega.

---

## Instalação passo a passo

### Pré-requisitos

- **Python 3.11 ou superior**, de <https://www.python.org/downloads/>. No Windows, marca
  "Add python.exe to PATH" durante a instalação.
- **Git**, de <https://git-scm.com/downloads>.
- Uma **conta na TMDB** (gratuita, para uso não comercial).

Não é preciso instalar nenhuma base de dados: a aplicação usa SQLite, que já vem com o Python.

### 1. Obter o token da TMDB

1. Cria uma conta em <https://www.themoviedb.org/signup> e confirma o e-mail.
2. Vai a **Settings → API** (<https://www.themoviedb.org/settings/api>) e pede uma chave
   para uso pessoal/educativo.
3. Na mesma página, copia o **API Read Access Token**. É o texto **longo**, que começa por
   `eyJ`. A "API Key" curta não serve.

> A chave é só tua: fica no ficheiro `.env`, que o Git ignora. Nunca a coles no código, num
> commit ou numa ferramenta de IA.

### 2. Descarregar o projeto e instalar as dependências

**Windows (PowerShell)**

```powershell
git clone https://github.com/jprbretas/MovieUniverseHub.git
cd MovieUniverseHub
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**macOS / Linux**

```bash
git clone https://github.com/jprbretas/MovieUniverseHub.git
cd MovieUniverseHub
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

O que estes comandos fazem:

- `python -m venv .venv` cria um **ambiente virtual**, uma pasta `.venv` com um Python só deste
  projeto. As bibliotecas ficam lá dentro e não se misturam com as de outros projetos.
- `Activate.ps1` (ou `source .../activate`) **ativa** esse ambiente no terminal atual. O prompt
  passa a começar por `(.venv)`. Num terminal novo, é preciso ativar outra vez.
- `pip install -e ".[dev]"` instala as dependências do `pyproject.toml` (FastAPI, SQLAlchemy...)
  e o pytest, para os testes.

> Se o PowerShell recusar o `Activate.ps1` ("running scripts is disabled on this system"), corre
> uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tenta de novo.

### 3. Configurar o `.env`

```powershell
copy .env.example .env        # macOS/Linux: cp .env.example .env
```

Abre o `.env` num editor de texto e cola o token depois do `=`:

```
TMDB_API_TOKEN=eyJ...o-teu-token...
```

As outras variáveis são opcionais e já têm valores por omissão:

| Variável | Para quê | Por omissão |
|---|---|---|
| `TMDB_API_TOKEN` | token da TMDB (obrigatório) | — |
| `HOST` / `PORT` | endereço e porta do servidor | `127.0.0.1` / `8000` |
| `RELOAD` | reiniciar o servidor sozinho ao gravar um `.py` | `true` |
| `DATABASE_URL` | onde fica a base de dados | o ficheiro `dados/movieuniverse.db` |

### 4. Arrancar

```powershell
python -m movieuniverse
```

- Aplicação: <http://127.0.0.1:8000>
- Documentação interativa da API (Swagger): <http://127.0.0.1:8000/docs>

A base de dados (`dados/movieuniverse.db`) é **criada automaticamente** no primeiro arranque,
com todas as tabelas. Para parar o servidor, carrega em `Ctrl+C` no terminal.

Para confirmar que o token foi lido, abre o ecrã **Sobre** ou <http://127.0.0.1:8000/api/health>
(`"tmdb_configurada": true`).

---

## Importar os dados de exemplo

```powershell
python -m movieuniverse importar-seed
```

Carrega o `dados/seed_playlists.json` fornecido com o enunciado: 3 utilizadores (ana, bruno e
carla), 10 playlists e 20 notas. No fim mostra um relatório do que foi criado e avisa sobre os
problemas encontrados no ficheiro:

```
Importação de seed_playlists.json concluída:
  Utilizadores: 3 criados, 0 já existiam
  Playlists:    10 criadas (2 marcadas como apagadas), 0 já existiam
  Notas:        20 criadas, 0 já existiam
  Avisos:
   - pl-01: o filme 27205 aparece repetido (ordem 6); ficou só a 1.ª ocorrência.
   - Filmes que só existem em playlists apagadas (ficam guardados, mas não aparecem na aplicação): 289, 348, 550, 807.
```

- **Pode correr mais do que uma vez sem duplicar nada.** Só cria o que falta e nunca altera o
  que já existe.
- Não precisa do token nem de internet: guarda só os ids dos filmes. Os títulos, cartazes e
  notas da TMDB aparecem quando os filmes são vistos na aplicação.
- Também importa outro ficheiro no mesmo formato: `python -m movieuniverse importar-seed --ficheiro caminho.json`.

Como foram tratados os problemas do ficheiro (playlists apagadas, filme repetido...):
[DECISIONS.md, "Problemas encontrados nos dados"](DECISIONS.md#problemas-encontrados-nos-dados).

---

## Exportar os dados

```powershell
python -m movieuniverse exportar                             # grava dados/exportacao.json
python -m movieuniverse exportar --ficheiro copia.json       # ou noutro sítio
```

Grava todos os utilizadores, playlists (também as apagadas, marcadas como tal) e notas num JSON
com **o mesmo formato do seed**. Serve para fazer uma cópia de segurança ou para levar os dados
para outra instalação, com `importar-seed --ficheiro`. Importar uma exportação na mesma base de
dados não duplica nada.

O ficheiro tem dados dos utilizadores, por isso o `.gitignore` impede que vá para o repositório.

---

## Testes

```powershell
pytest
```

São **110 testes automáticos**. Correm em poucos segundos e **não usam a internet nem a base
de dados real**:

- as respostas da TMDB vêm de uma TMDB "falsa", com respostas reais gravadas em `tests/fixtures/tmdb/`;
- cada teste usa uma base de dados nova, em memória, que desaparece no fim.

Por isso os testes funcionam mesmo sem token e sem rede. Para ver o nome de cada teste, usa
`pytest -v`.

---

## Casos de teste

Os casos de teste vêm do enunciado (a nota combinada com poucos votos, o filme sem votos, as
armadilhas do seed...) e de regras que a própria aplicação garante (uma nota por utilizador e
por filme, notas só de 1 a 10...). A lista completa, com **o resultado de cada caso numa frase**
e o teste que o prova, está no **[RELATORIO.md](RELATORIO.md)**.

### Demonstração no navegador (5 minutos)

Com os dados de exemplo importados e a aplicação a correr:

1. **Nota TMDB e nota combinada.** Pesquisa "Matrix" e abre o filme. Os votos da TMDB aparecem
   sempre ao lado da nota, e a nota combinada vem com a explicação do cálculo.
2. **Mesmo título, anos diferentes.** Pesquisa "Dune": os dois filmes distinguem-se pelo ano.
3. **Comparar.** Entra como `ana`, abre **Comparar** e compara "Ficção científica" com
   "Maratona sci-fi". Aparecem a vencedora, as médias e 3 filmes em comum.
4. **Poucos votos.** Cria uma playlist, junta-lhe um filme que diga "sem votos" e compara-a com
   outra: dá "informação insuficiente". Depois dá nota 10 a esse filme e compara de novo. A
   playlist passa a ter média 6,53, porque um único voto não chega para ganhar a filmes com
   milhares de votos.
5. **Nota 20 pela API.** No Swagger (`/docs`), em `PUT /api/utilizadores/{utilizador_id}/notas/{tmdb_id}`,
   envia `{"estrelas": 20}`. A resposta é `422` e nada é gravado.

---

## API REST

Toda a comunicação entre o navegador e o servidor passa por esta API. A documentação
interativa (Swagger) está em `/docs` e a especificação OpenAPI em `/openapi.json`.

| Método | Caminho | O que faz |
|---|---|---|
| GET | `/api/filmes?titulo=Matrix&pagina=1` | pesquisa filmes por título (20 por página) |
| GET | `/api/filmes/{tmdb_id}` | ficha de um filme (sinopse, géneros, duração, cartaz, nota TMDB) |
| GET | `/api/filmes/{tmdb_id}/notas` | notas dos utilizadores, a média delas e a nota combinada |
| GET | `/api/utilizadores` | lista de utilizadores |
| POST | `/api/utilizadores` | "entrar" com um nome (cria o utilizador se não existir) |
| GET | `/api/utilizadores/{id}/playlists` | playlists do utilizador, com os ids dos filmes |
| POST | `/api/utilizadores/{id}/playlists` | cria uma playlist |
| PUT | `/api/utilizadores/{id}/notas/{tmdb_id}` | dá ou muda a nota (1 a 10) do utilizador a um filme |
| DELETE | `/api/utilizadores/{id}/notas/{tmdb_id}` | retira a nota |
| GET | `/api/playlists` | todas as playlists (sem as apagadas) |
| GET | `/api/playlists/comparar?a={id}&b={id}` | compara duas playlists |
| GET | `/api/playlists/{id}` | uma playlist com os dados de cada filme |
| DELETE | `/api/playlists/{id}` | apaga a playlist (fica marcada como apagada) |
| PUT | `/api/playlists/{id}/filmes/{tmdb_id}` | adiciona o filme à playlist (repetir não duplica) |
| DELETE | `/api/playlists/{id}/filmes/{tmdb_id}` | tira o filme da playlist |
| GET | `/api/health` | estado da API e se o token da TMDB está configurado |

**Erros:** o corpo é sempre `{"detail": "mensagem"}`.

| Código | Quando |
|---|---|
| `404` | o filme, a playlist ou o utilizador não existe |
| `422` | parâmetros inválidos (ex.: nota fora de 1 a 10, comparar uma playlist com ela própria) |
| `503` | a TMDB não responde ou pediu para abrandar |
| `500` | o token da TMDB está em falta ou foi recusado |

---

## Como funciona por dentro

### Nota combinada

A nota combinada é uma **média bayesiana**. Antes de contar os votos de um filme, a aplicação
finge que ele já tem **100 votos "imaginários" com nota 6,5**. Depois junta os votos reais, da
TMDB e da aplicação, e cada voto conta o mesmo:

- com **poucos votos**, os imaginários pesam mais e a nota fica perto de 6,5 ("ainda não sabemos
  o suficiente");
- com **muitos votos**, quase não contam e a nota fica perto da média real;
- **sem votos nenhuns**, não há nota combinada e a ficha mostra "informação insuficiente".

Exemplo do enunciado: um filme com 8,9 e 12 votos fica com **6,76**, e um com 8,4 e 30 000 votos
fica com **8,39**. Mesmo com três utilizadores a dar 10 ao primeiro, ele só sobe para 6,84.

A regra completa, a justificação dos números e a resposta à pergunta "a partir de quantos votos
confiamos numa média?" estão no [DECISIONS.md](DECISIONS.md#nota-combinada). O código é a função
`calcular_nota_combinada()`, em `src/movieuniverse/nota_combinada.py`.

### Comparação de playlists

O rating de uma playlist é a **média das notas combinadas dos seus filmes**, e ganha a média
mais alta. Filmes sem nota combinada ficam de fora da média, mas a comparação diz quantos foram.
Regras completas no [DECISIONS.md](DECISIONS.md#comparação-de-playlists).

### Cache das respostas da TMDB

A TMDB limita o número de pedidos, por isso a aplicação guarda as respostas na própria base de
dados (tabelas `filmes_cache` e `pesquisas_cache`). A lógica está em `src/movieuniverse/catalogo.py`:

1. Antes de pedir à TMDB, procura a resposta na cache.
2. Se ela tiver menos de **24 horas**, usa-a e não faz pedido nenhum.
3. Se não tiver, pede à TMDB e atualiza a cache.
4. Se a TMDB não responder (sem rede ou "demasiados pedidos"), usa a cópia antiga, se houver.

As pesquisas são normalizadas: " Matrix " e "matrix" contam como a mesma. Como a cache está em
SQLite e não em memória, continua lá depois de a aplicação reiniciar. Isto é importante para a
comparação, que precisa dos dados de muitos filmes de uma vez.

### Segurança e dados pessoais

- **Dados pessoais:** a aplicação só guarda o nome que cada pessoa escolhe. Não pede e-mail,
  palavra-passe nem data de nascimento.
- **Entradas validadas em duas camadas:** a API recusa com `422` notas fora de 1 a 10 ou que não
  sejam números inteiros, e a base de dados tem uma regra (`CHECK`) que as recusa mesmo que o
  código da aplicação fosse contornado.
- **SQL injection:** todas as consultas passam pelo SQLAlchemy com parâmetros. Um nome como
  `ana'; DROP TABLE notas; --` é guardado como texto e nunca executado.
- **XSS:** o frontend escapa todo o texto que vem da API antes de o mostrar (função `esc()` em
  `static/js/util.js`).
- **Token da TMDB:** fica só no `.env`, que não vai para o Git, e nunca é devolvido pela API.
- **Limitação assumida:** sem palavra-passe, qualquer pessoa com acesso à aplicação pode agir
  como outro utilizador. Para uma aplicação local de demonstração é aceitável (ver DECISIONS).

Os testes em `tests/test_seguranca.py` reproduzem estas tentativas.

---

## Estrutura do projeto

```
MovieUniverseHub/
├── src/movieuniverse/        código da aplicação
│   ├── __main__.py           comandos: arrancar, importar-seed, exportar
│   ├── api.py                monta a app FastAPI: rotas, erros e frontend
│   ├── rotas/                endpoints REST: filmes, utilizadores, playlists
│   ├── servicos.py           regras de negócio (playlists, notas, comparação)
│   ├── nota_combinada.py     regra da nota combinada (função pura)
│   ├── comparacao.py         comparação de duas playlists (função pura)
│   ├── catalogo.py           TMDB + cache na base de dados
│   ├── tmdb.py               cliente da API da TMDB e modelos das respostas
│   ├── entidades.py          tabelas da base de dados
│   ├── db.py                 ligação à base de dados
│   ├── esquemas.py           formato do JSON que entra e sai da API
│   ├── dependencias.py       injeção de dependências (sessão, TMDB, catálogo)
│   ├── importar.py           importação do seed
│   ├── exportar.py           exportação para JSON
│   ├── config.py             leitura do .env
│   └── static/               frontend: index.html, css/, js/
├── tests/                    testes automáticos (pytest)
│   └── fixtures/tmdb/        respostas reais da TMDB usadas nos testes
├── scripts/explorar_tmdb.py  script usado para explorar a API da TMDB no início
├── dados/seed_playlists.json dados de exemplo do enunciado (não alterar)
├── .env.example              variáveis de configuração, sem valores
└── pyproject.toml            dependências e configuração do projeto
```

A aplicação está dividida em três camadas, como pede o enunciado:

- **Apresentação:** `static/` (HTML, CSS e JavaScript) e `rotas/` (a API REST).
- **Negócio:** `servicos.py`, `nota_combinada.py`, `comparacao.py`, `catalogo.py` e `tmdb.py`.
- **Dados:** `entidades.py` e `db.py`.

---

## Outros documentos

| Ficheiro | Conteúdo |
|---|---|
| [DECISIONS.md](DECISIONS.md) | as decisões tomadas e porquê: nota combinada, comparação, dados do seed... |
| [RELATORIO.md](RELATORIO.md) | o resultado de cada caso de teste, numa frase |
| [AI_LOG.md](AI_LOG.md) | situações em que a IA sugeriu algo errado e o que se fez em vez disso |
| [LICENSE](LICENSE) | licença MIT |

---

## Atribuição

Os dados e as imagens dos filmes vêm da [TMDB](https://www.themoviedb.org/).

Este produto usa a API da TMDB, mas não é endossado nem certificado pela TMDB.

*This product uses the TMDB API but is not endorsed or certified by TMDB.*
