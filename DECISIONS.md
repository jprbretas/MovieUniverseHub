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

*(a definir no passo 7)*

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
