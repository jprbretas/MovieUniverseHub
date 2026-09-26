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

## 3. Número de votos "imaginários" da nota combinada (m = 500 → m = 100)
- **Contexto:** passo 7, escolha da regra da nota combinada (média bayesiana).
- **Sugestão da IA:** usar m = 500 votos imaginários, inspirado no Top 250 do IMDb.
- **Problema / porque não usei:** questionei o valor porque a MovieUniverse é uma aplicação
  pequena. Ao analisar, vimos que o tamanho da aplicação pesa pouco (a maioria dos votos vem
  da TMDB), mas que 500 era mesmo demasiado desconfiado por outra razão: com 300 votos, a
  margem de erro de uma média já é de cerca de ±0,1, e mesmo assim um filme com 7,5 e 300 votos
  ficava com 6,9. O IMDb usa um valor alto porque quer uma lista exclusiva, que não é o nosso caso.
- **O que fiz em vez disso:** escolhi m = 100 (margem de erro de cerca de ±0,2), que continua
  a garantir os casos do enunciado (8,9 com 12 votos → 6,8; 8,4 com 30 000 votos → 8,4).

## 4. Race condition na cache ao abrir a ficha de um filme
- **Contexto:** passo 7. O endpoint das notas passou a consultar também o catálogo (para a
  nota combinada), e a ficha pede o filme e as notas em paralelo.
- **Sugestão da IA:** a cache fazia "ler o registo; se não existir, fazer INSERT".
- **Problema:** num teste no navegador, os dois pedidos paralelos não encontravam o filme na
  cache e ambos tentavam o INSERT; o segundo falhava com `UNIQUE constraint failed` e a ficha
  mostrava um erro.
- **O que fiz em vez disso:** a cache passou a gravar com um upsert
  (`INSERT ... ON CONFLICT DO UPDATE`), que é atómico. Acrescentei um teste que reproduz a
  situação com duas sessões e que falhava com o código antigo.


## 5. O README descrevia um ficheiro que não estava no repositório
- **Contexto:** revisão final da documentação, antes da entrega.
- **Sugestão da IA:** o README dizia que se podia arrancar a aplicação com **F5** no VS Code,
  através de uma configuração em `.vscode/launch.json`.
- **Problema:** esse ficheiro ficou como passo opcional e nunca chegou ao repositório. Quem
  clonasse o projeto numa máquina limpa não o teria, e a instrução não funcionava. Um comentário
  do `config.py` apontava para o mesmo ficheiro.
- **O que fiz em vez disso:** retirei a instrução do README e corrigi o comentário. O único
  arranque documentado é `python -m movieuniverse`, e segui o README do início ao fim numa
  pasta limpa para confirmar que as instruções funcionam.
