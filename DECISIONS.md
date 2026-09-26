# Decisões

Este ficheiro explica as escolhas que fiz no MovieUniverse Hub e porquê. Começa pelas três
decisões mais importantes; as secções seguintes dão os detalhes.

**Índice:**
[As três decisões principais](#as-três-decisões-principais) ·
[Stack](#stack) ·
[Nota combinada](#nota-combinada) ·
[Comparação de playlists](#comparação-de-playlists) ·
[Utilizadores e dados pessoais](#utilizadores-e-dados-pessoais) ·
[Base de dados e cache](#base-de-dados-e-cache) ·
[Problemas encontrados nos dados](#problemas-encontrados-nos-dados) ·
[Importação e exportação](#importação-e-exportação) ·
[Jogo](#jogo-mais-alto-ou-mais-baixo) ·
[Limitações conhecidas](#limitações-conhecidas)

---

## As três decisões principais

1. **A nota combinada é uma média bayesiana**, com 100 votos "imaginários" de nota 6,5, e cada
   voto de um utilizador vale o mesmo que um voto da TMDB. Assim, um filme com poucos votos não
   passa à frente de um filme com milhares, e três utilizadores não conseguem virar a tabela.
   [Detalhes](#nota-combinada)
2. **Os utilizadores identificam-se só pelo nome, sem palavra-passe**, como o enunciado permite.
   A aplicação não guarda dados pessoais, e os utilizadores do seed (que só têm nome) funcionam
   sem casos especiais. [Detalhes](#utilizadores-e-dados-pessoais)
3. **A base de dados guarda só a referência aos filmes (`tmdb_id`), e as respostas da TMDB ficam
   numa cache na mesma base de dados**, válida por 24 horas. As playlists e as notas não dependem
   da internet, e abrir de novo um filme ou uma playlist não gasta pedidos à TMDB.
   [Detalhes](#base-de-dados-e-cache)

---

## Stack

**Python + FastAPI + SQLite + HTML/CSS/JavaScript simples.** Todas fazem parte das tecnologias
recomendadas no enunciado.

- O **FastAPI** gera sozinho a especificação OpenAPI/Swagger, que o enunciado valoriza.
- O **SQLite** não precisa de instalação, o que ajuda a cumprir o requisito de arrancar numa
  máquina limpa com um só comando. O acesso é feito pelo ORM **SQLAlchemy**.
- O **frontend não usa frameworks** (nem React, nem build): são ficheiros HTML, CSS e JavaScript
  servidos pelo próprio FastAPI. Menos peças para instalar e para explicar.
- Os testes usam o **pytest**.

---

## Nota combinada

### A regra

Antes de olhar para os votos de um filme, assumimos que ele já tem **m = 100 votos
"imaginários"** com uma **nota neutra C = 6,5**. Depois juntamos os votos reais, da TMDB e dos
utilizadores da aplicação:

```
                 v × R  +  m × C
nota combinada = ───────────────        v = número de votos reais (TMDB + aplicação)
                     v  +  m            R = média desses votos reais
```

Na prática:

- Com **poucos votos**, os votos imaginários dominam e a nota fica perto de 6,5. É a forma de
  dizer "ainda não sabemos o suficiente sobre este filme".
- Com **muitos votos**, os imaginários quase não pesam e a nota fica perto da média real.
- **Um voto de um utilizador da aplicação vale o mesmo que um voto da TMDB.** Três utilizadores
  não conseguem virar a tabela contra milhares de votos, mas contam a sério nos filmes pouco
  conhecidos.
- **Sem votos nenhuns** (nem na TMDB, nem na aplicação), não há nota combinada: a ficha mostra
  "informação insuficiente".
- A nota fica sempre entre 0 e 10, porque é uma média ponderada de valores entre 0 e 10.

A ficha do filme mostra a nota combinada ao lado da nota da TMDB, com o número de votos em que
se baseia e uma frase que explica o cálculo (por exemplo, quanto pesou a média real).

### Porquê esta regra e não uma média simples

Uma média simples das duas médias daria o mesmo peso a 30 000 votos da TMDB e a 3 votos da
aplicação, que é exatamente o que o enunciado proíbe. A média bayesiana resolve os dois problemas
de uma vez: pesa cada lado pelo número de votos e desconfia de médias feitas com poucos votos.
É a mesma ideia que o IMDb usa no seu Top 250.

### Os casos do enunciado

Provados em `tests/test_nota_combinada.py`:

| Filme | Votos reais | Média real | Nota combinada |
|---|---|---|---|
| A: 8,9 com 12 votos na TMDB | 12 | 8,9 | **6,76** |
| A + 3 utilizadores a dar 10 | 15 | 9,12 | **6,84** |
| B: 8,4 com 30 000 votos na TMDB | 30 000 | 8,4 | **8,39** |

B fica sempre acima de A, mesmo depois dos três votos de 10.

### Pergunta sobre o número de votos: a partir de quantos votos confiamos numa média?

**A partir de cerca de 100 votos.** As notas que as pessoas dão a um mesmo filme variam
tipicamente cerca de ±1,8 pontos, e a margem de erro de uma média diminui com a raiz quadrada do
número de votos (1,8 / √n):

| Votos | Margem de erro da média | Confiança |
|---|---|---|
| 12 | ± 0,5 | pouca: a média pode estar meio ponto ao lado |
| 100 | ± 0,2 | razoável |
| 300 | ± 0,1 | boa |

Por isso m = 100: com 100 votos reais, a média real já pesa metade da nota, e a partir daí pesa
cada vez mais. Cheguei a considerar m = 500 (o valor do Top 250 do IMDb), mas isso castigava
demasiado filmes com algumas centenas de votos, que já têm médias fiáveis (ver
[AI_LOG.md](AI_LOG.md), entrada 3).

**A nota neutra C = 6,5** fica ligeiramente acima do meio da escala: representa um filme
"normal", nem bom nem mau. É para lá que puxamos um filme sobre o qual ainda há pouca informação.

### Onde está o código

A função pura `calcular_nota_combinada()`, em `src/movieuniverse/nota_combinada.py`, recebe as
médias e os números de votos e devolve a nota e a explicação. Não depende da interface, da base
de dados nem da rede, como pede o enunciado. A ficha do filme e a comparação de playlists usam
esta mesma função.

---

## Comparação de playlists

O enunciado pede que a comparação indique a playlist com o melhor rating "com base na média do
rating individual de cada filme". As regras (código em `src/movieuniverse/comparacao.py`, também
uma função pura):

- **O rating de cada filme é a sua nota combinada**, e não a nota da TMDB. Assim, um filme com
  8,9 e 12 votos não puxa uma playlist para cima, que é o mesmo problema que a nota combinada
  resolve.
- **O rating da playlist é a média das notas combinadas dos seus filmes.**
- **Filmes sem nota combinada** (sem votos nenhuns, ou que a TMDB não conseguiu devolver) ficam
  de fora da média, mas são contados e o resultado diz quantos foram.
- **Ganha a média mais alta.** Médias iguais até à 2.ª casa decimal contam como empate.
- **Se uma das playlists não tiver nenhum filme com nota**, não há vencedora: o resultado diz
  "informação insuficiente".
- Só se comparam playlists ativas (as apagadas dão `404`) e não se compara uma playlist com ela
  própria (`422`).

**Outras comparações mostradas:** o número de filmes de cada uma, o melhor filme de cada uma, os
filmes em comum e os filmes que só estão numa delas.

---

## Utilizadores e dados pessoais

Os utilizadores identificam-se apenas pelo **nome**, sem palavra-passe, como o enunciado permite.

- "Entrar" é só escrever o nome: se já existir, usa-se esse utilizador; se não, é criado.
  "Ana" e "ana" são a mesma pessoa.
- O navegador lembra-se de quem entrou e envia o id do utilizador no caminho dos pedidos
  (`/api/utilizadores/{id}/...`).
- A aplicação **não guarda dados pessoais**: nada de e-mail, palavra-passe ou data de nascimento.

**Consequência assumida:** sem palavra-passe, qualquer pessoa com acesso à aplicação pode agir
como outro utilizador. Para uma aplicação local de demonstração isto é aceitável. Com login, as
palavras-passe teriam de ser guardadas com hashing (bcrypt ou Argon2) e cada pedido teria de
confirmar que a playlist ou a nota pertence a quem está autenticado.

---

## Base de dados e cache

- **Os filmes não têm tabela própria.** As playlists e as notas guardam só o `tmdb_id`, que é a
  referência ao filme na TMDB. Assim a importação do seed não precisa da internet.
- **As regras do enunciado estão na própria base de dados**, e não só no código:
  - um filme não se repete na mesma playlist (chave primária `(playlist_id, tmdb_id)`);
  - uma nota por utilizador e por filme (`UNIQUE (utilizador_id, tmdb_id)`);
  - notas só de 1 a 10 (`CHECK`);
  - nomes de utilizador únicos, sem distinguir maiúsculas.
- **Apagar uma playlist só a marca como apagada** (soft delete), o mesmo modelo que o seed usa.
  Ela deixa de aparecer, mas os dados não se perdem.
- **As tabelas são criadas no arranque** e na importação, só as que faltam. Para este tamanho de
  projeto, uma ferramenta de migrações (como o Alembic) seria excessiva.
- **Chaves estrangeiras ativas.** O SQLite ignora-as por omissão; a aplicação liga-as em cada
  ligação (`PRAGMA foreign_keys=ON`).
- **Cache das respostas da TMDB na mesma base de dados**, válida por **24 horas**: as notas e os
  votos da TMDB mudam devagar, e um dia é um bom equilíbrio entre dados frescos e poucos pedidos.
  Se a TMDB falhar, usa-se a cópia antiga. A cache grava com um "upsert" (`INSERT ... ON CONFLICT
  DO UPDATE`) para aguentar dois pedidos ao mesmo filme ao mesmo tempo (ver
  [AI_LOG.md](AI_LOG.md), entrada 4). O funcionamento passo a passo está no README.

---

## Problemas encontrados nos dados

O `dados/seed_playlists.json` tem armadilhas de propósito. A importação
(`python -m movieuniverse importar-seed`, código em `src/movieuniverse/importar.py`) trata-as assim:

| Problema no seed | O que a aplicação faz |
|---|---|
| **Playlists marcadas como apagadas** (pl-03 "Rascunho antigo" e pl-07 "Lista de teste") | São importadas **como apagadas**, o mesmo soft delete da aplicação. Ficam na base de dados, fiéis ao ficheiro, mas não aparecem em lado nenhum. |
| **O filme 27205 aparece duas vezes na pl-01** (ordem 1 e ordem 6) | Fica **só a 1.ª ocorrência** (ordem 1) e a repetição aparece como aviso no relatório. A chave primária da tabela impede, de qualquer forma, que o mesmo filme entre duas vezes. |
| **Filmes que só existem em playlists apagadas** (289, 348, 550 e 807) | Ficam guardados dentro dessas playlists, mas não aparecem na aplicação nem contam para comparações. O relatório da importação lista-os. |
| **Filmes com o mesmo título e anos diferentes** (dois "Dune", dois "O Rei Leão") | A aplicação identifica os filmes sempre pelo `tmdb_id`, nunca pelo título, por isso não há confusão. Os cards e a ficha mostram o ano para o utilizador os distinguir. |

---

## Importação e exportação

**A importação pode correr várias vezes sem duplicar nada.** Os utilizadores são reconhecidos
pelo nome, as playlists pelo id do ficheiro (`pl-01`...) e as notas pelo par (utilizador, filme).
A importação **só cria o que falta**: nunca altera nem apaga dados que já existem, por isso as
mudanças feitas na aplicação (uma nota alterada, um filme retirado) sobrevivem a uma nova
importação.

Outras escolhas da importação:

- as notas mantêm a data que vem no ficheiro;
- não contacta a TMDB: guarda só os `tmdb_id`, e os dados dos filmes chegam quando forem vistos;
- o formato do ficheiro é validado antes de gravar, e tudo corre numa só transação: um ficheiro
  com erros (por exemplo, uma nota 20) não deixa nada a meio.

**A exportação** (`python -m movieuniverse exportar`, código em `src/movieuniverse/exportar.py`)
é o inverso da importação e usa o mesmo formato do seed, por isso o ficheiro pode ser importado
noutra instalação. As playlists do seed mantêm o seu id; as criadas na aplicação recebem, na
primeira exportação, um id próprio (`app-` seguido de 8 caracteres). Assim, importar o ficheiro
de volta reconhece-as e também não duplica nada.

---

## Jogo "mais alto ou mais baixo"

O jogo era opcional e **não foi implementado nesta entrega**. Dei prioridade a ter as partes
obrigatórias completas, testadas e documentadas. Como a nota combinada é uma função pura, um jogo
futuro poderia usá-la diretamente, sem copiar a lógica, como o enunciado pede.

---

## Limitações conhecidas

- **Sem palavra-passe**, qualquer pessoa pode agir como outro utilizador (ver acima).
- **Inflacionar votos:** criar muitos utilizadores para dar notas a um filme é possível. O efeito
  é limitado pela regra da nota combinada (cada voto vale o mesmo que um da TMDB), mas não é
  impedido.
- **SQLite:** chega bem para uma aplicação local, mas não foi pensado para muitos utilizadores
  a gravar ao mesmo tempo.
- **Dados da TMDB até 24 horas desatualizados**, por causa da cache.
