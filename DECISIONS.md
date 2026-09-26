# Decisões

## 1. Stack

Python + FastAPI + SQLite + HTML/CSS/JS simples. Faz parte das tecnologias recomendadas
no enunciado. O FastAPI gera a especificação OpenAPI/Swagger automaticamente, e o SQLite
não precisa de instalação, o que ajuda a cumprir o requisito de "arrancar numa máquina limpa".

## 2. Identificação dos utilizadores

Os utilizadores identificam-se apenas pelo **nome**, sem palavra-passe, como o enunciado
permite. Assim não se guardam dados pessoais (secção 6), e os utilizadores do
`seed_playlists.json` (que só têm nome) funcionam sem casos especiais.

"Entrar" é só escrever o nome: se já existir, usa-se esse utilizador; se não, é criado.
O frontend lembra-se de quem entrou (no navegador) e envia o id do utilizador no caminho
dos pedidos (`/api/utilizadores/{id}/...`). Consequência assumida: sem palavra-passe,
qualquer pessoa com acesso à aplicação pode agir como outro utilizador. Para uma aplicação
local de demonstração isto é aceitável; com login, seria preciso verificar o dono de cada
playlist e nota em cada pedido.

## 3. Base de dados e cache

- **Os filmes não têm tabela própria.** Playlists e notas guardam só o `tmdb_id`, que é a
  referência ao filme na TMDB. Assim a importação do seed não depende da internet.
- **As regras do enunciado estão na própria base de dados:** chave primária composta
  `(playlist_id, tmdb_id)` (um filme não se repete na mesma playlist),
  `UNIQUE (utilizador_id, tmdb_id)` nas notas (uma nota por utilizador e por filme),
  `CHECK` de 1 a 10 nas estrelas e nome de utilizador único sem distinguir maiúsculas.
- **Apagar uma playlist só a marca como `apagada`** (soft delete), o mesmo modelo do seed.
- **Sem migrations.** As tabelas são criadas no arranque com `create_all`, que só cria as
  que faltam. Para este escopo, uma ferramenta como o Alembic seria excessiva.
- **Chaves estrangeiras ativas no SQLite.** O SQLite ignora-as por omissão; a aplicação
  liga-as (`PRAGMA foreign_keys=ON`) em cada ligação.
- **Cache na base de dados, válida por 24 horas**, com cópia antiga como recurso quando a
  TMDB falha. Os detalhes estão no README, na secção "Cache das respostas da TMDB".

## 4. Nota combinada

**Regra: média bayesiana.** Antes de olhar para os votos de um filme, assumimos que ele já tem
**m = 100 votos "imaginários"** com uma **nota neutra C = 6,5**. Depois juntamos os votos reais,
da TMDB e dos utilizadores da aplicação:

```
                 v × R  +  m × C
nota combinada = ───────────────        v = votos reais (TMDB + aplicação)
                     v  +  m            R = média ponderada dos votos reais
```

- Com **poucos votos**, os votos imaginários dominam e a nota fica perto de 6,5 ("ainda não
  sabemos o suficiente"). Com **muitos votos**, quase não pesam e a nota fica perto da média real.
- **Um voto de um utilizador da aplicação vale o mesmo que um voto da TMDB.** Assim, três
  utilizadores não conseguem virar a tabela contra milhares de votos da TMDB, mas contam a
  sério nos filmes pouco conhecidos.
- **Sem votos nenhuns** (TMDB e aplicação), não há nota combinada: a ficha mostra
  "informação insuficiente".
- A nota fica sempre entre 0 e 10, porque é uma média ponderada de valores entre 0 e 10.

**Os casos do enunciado** (provados em `tests/test_nota_combinada.py`):

| Filme | Votos reais | Média real | Nota combinada |
|---|---|---|---|
| A: 8,9 com 12 votos na TMDB | 12 | 8,9 | 6,76 |
| A + 3 utilizadores a dar 10 | 15 | 9,12 | 6,84 |
| B: 8,4 com 30 000 votos na TMDB | 30 000 | 8,4 | 8,39 |

B fica sempre acima de A.

**Pergunta sobre o número de votos: a partir de quantos votos confiamos numa média?**
A partir de cerca de **100**. As notas de um filme variam tipicamente ±1,8 pontos entre
pessoas, e a margem de erro de uma média cai com a raiz do número de votos (1,8 / √n):
com 12 votos é cerca de ±0,5 (pouco fiável), com 100 votos ±0,2 e com 300 votos ±0,1.
Por isso m = 100: com 100 votos reais, a média real já pesa metade, e a partir daí pesa cada
vez mais. Chegou-se a considerar m = 500 (inspirado no Top 250 do IMDb), mas isso castigava
demasiado filmes com algumas centenas de votos, que já têm médias fiáveis (ver AI_LOG.md).

**Onde está o código:** a função pura `calcular_nota_combinada()` em
`src/movieuniverse/nota_combinada.py` recebe médias e números de votos e devolve a nota e uma
explicação. Não depende da interface, da base de dados nem da rede. A comparação de
playlists e o jogo usam esta mesma função.

## 5. Regras do jogo

*(a definir no passo 9, se o jogo for implementado)*

## 6. Problemas encontrados nos dados

O `dados/seed_playlists.json` tem armadilhas de propósito. A importação
(`python -m movieuniverse importar-seed`, código em `src/movieuniverse/importar.py`) trata-as assim:

| Problema no seed | Decisão |
|---|---|
| Playlists marcadas como apagadas (pl-03 "Rascunho antigo", pl-07 "Lista de teste") | São importadas **com `apagada = sim`**, o mesmo soft delete usado na aplicação. Ficam na base de dados, fiéis ao ficheiro, mas não aparecem em lado nenhum. |
| O filme 27205 aparece duas vezes na pl-01 (ordem 1 e ordem 6) | Fica **só a 1.ª ocorrência** (ordem 1). A repetição é ignorada e aparece como aviso no relatório. A chave primária `(playlist_id, tmdb_id)` impede, de qualquer forma, que o mesmo filme entre duas vezes. |
| Filmes que só existem em playlists apagadas (289, 348, 550, 807) | Ficam guardados dentro dessas playlists, mas não aparecem na aplicação nem contam para comparações. O relatório da importação lista-os. |
| Filmes com o mesmo título e anos diferentes (ex.: dois "Dune", dois "O Rei Leão") | A aplicação identifica os filmes sempre pelo `tmdb_id`, nunca pelo título, por isso não há confusão. Os cards e a ficha mostram o ano para o utilizador os distinguir. |

**Correr a importação duas vezes não duplica nada.** Os utilizadores são reconhecidos pelo nome
(sem distinguir maiúsculas), as playlists pelo id do seed (guardado em `Playlist.id_seed`) e as
notas pelo par (utilizador, filme). A importação **só cria o que falta**: nunca altera nem apaga
dados que já existem, por isso as alterações feitas na aplicação (uma nota mudada, um filme
retirado) sobrevivem a uma nova importação.

Outras escolhas: as notas mantêm a data do ficheiro; a importação não contacta a TMDB (guarda
só os `tmdb_id`, e os dados dos filmes chegam quando forem vistos); tudo corre numa transação,
por isso um ficheiro com formato errado não deixa nada a meio.
