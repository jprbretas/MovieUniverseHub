# Registo de utilização de IA

Situações em que a IA sugeriu algo errado, ou em que decidi não usar a sugestão,
e o que fiz em vez disso.

<!--
Modelo para cada entrada:

## N. Título curto
- **Contexto:** o que estava a fazer
- **Sugestão da IA:** o que foi sugerido
- **Problema / porque não usei:** ...
- **O que fiz em vez disso:** ...
-->

## 1. Biblioteca desatualizada no TestClient (httpx → httpx2)
- **Contexto:** passo 0, criação do esqueleto do projeto e do primeiro teste automático.
- **Sugestão da IA:** usar o `httpx` como dependência de desenvolvimento para o `TestClient` do FastAPI.
- **Problema:** ao correr o `pytest`, o Starlette 1.7 emitiu um `StarletteDeprecationWarning`
  a dizer que o uso do `httpx` com o `TestClient` está obsoleto e que se deve instalar o `httpx2`.
  A sugestão vinha de conhecimento anterior a essa mudança.
- **O que fiz em vez disso:** confirmei no PyPI que o `httpx2` é do mesmo autor (Tom Christie),
  troquei a dependência no `pyproject.toml` e voltei a correr os testes, que passaram sem aviso.

## 2. Respostas da API sairiam com os nomes em inglês da TMDB (alias → validation_alias)
- **Contexto:** passo 3, primeiros endpoints REST (`/api/filmes`).
- **Sugestão da IA:** nos modelos Pydantic, ligar os nomes em português aos campos da TMDB com
  `Field(alias="title")`.
- **Problema:** ao testar os endpoints, vimos que o FastAPI serializa as respostas **pelo alias**
  por omissão. A nossa API devolveria `title`, `vote_count`... em vez de `titulo`, `num_votos`.
  A opção `response_model_by_alias=False` corrigia o JSON, mas o Swagger continuava a mostrar os
  nomes em inglês, ou seja, a documentação não batia certo com a resposta real.
- **O que fiz em vez disso:** troquei `alias` por `validation_alias`, que só é usado para **ler**
  o JSON da TMDB. As respostas da API e o Swagger passaram a usar os nomes em português, e
  confirmei os dois no `/openapi.json`.
