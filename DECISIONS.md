# Decisões

## 1. Stack

Python + FastAPI + SQLite + HTML/CSS/JS simples. Faz parte das tecnologias recomendadas
no enunciado. O FastAPI gera a especificação OpenAPI/Swagger automaticamente, e o SQLite
não precisa de instalação, o que ajuda a cumprir o requisito de "arrancar numa máquina limpa".

## 2. Identificação dos utilizadores

Os utilizadores identificam-se apenas pelo **nome**, sem palavra-passe, como o enunciado
permite. Assim não se guardam dados pessoais (secção 6), e os utilizadores do
`seed_playlists.json` (que só têm nome) funcionam sem casos especiais.

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

*(a preencher no passo 6: importação do seed)*
