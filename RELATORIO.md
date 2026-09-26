# Relatório dos casos de teste

Resultado de cada caso de teste, numa frase. Os casos vêm do enunciado (secções 1 a 6 e Anexo B)
e das regras que a própria aplicação garante.

## Resumo

| | |
|---|---|
| **Testes automáticos** | 110, todos a passar (`pytest`) |
| **Casos de teste neste relatório** | 55, todos cumpridos |
| **Não implementado** | o jogo "mais alto ou mais baixo" (opcional) |

## Como foi testado

- **Testes automáticos (pytest).** Correm sem internet e sem tocar na base de dados real: a TMDB
  é substituída por uma TMDB "falsa", que devolve respostas reais gravadas em
  `tests/fixtures/tmdb/`, e cada teste usa uma base de dados nova em memória. A coluna "Prova"
  indica o ficheiro e o teste. Para os correr: `pytest -v`.
- **No navegador**, com os dados do seed importados, para o que depende do ecrã (cards, ficha,
  ★, comparação). A demonstração do README percorre estes casos em 5 minutos.
- **Instalação numa pasta limpa**, seguindo o README do início ao fim.

Na coluna "Prova", `importar` quer dizer o ficheiro `tests/test_importar.py`, e assim para os
outros. Para correr um só teste: `pytest tests/test_importar.py::test_correr_duas_vezes_nao_duplica`.

---

## Fase 1: Catálogo

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 1 | Pesquisar filmes por título | A pesquisa devolve a lista de filmes da TMDB (20 por página), com título, ano, cartaz e nota. | `api_filmes`: `test_pesquisa_devolve_filmes_com_nomes_em_portugues` · navegador |
| 2 | Ficha do filme | A ficha mostra sinopse, géneros, duração e cartaz. | `api_filmes`: `test_detalhe_devolve_a_ficha_do_filme` · navegador |
| 3 | Nota da TMDB com o número de votos | A nota aparece sempre com os votos, no formato do enunciado ("7,8 · 12 340 votos"). | `tmdb_modelos`: `test_formatar_nota_tmdb` |
| 4 | Filme sem votos | Um filme com 0 votos mostra "sem votos" e nunca "0". | `tmdb_modelos`: `test_formatar_nota_tmdb`, `test_pesquisa_real_tem_filmes_sem_votos_e_sem_ano` |
| 5 | Sinopse em falta em português | Quando a TMDB não tem sinopse em pt-PT, a ficha mostra a inglesa. | `tmdb_cliente`: `test_detalhe_sem_sinopse_em_pt_usa_a_inglesa` |
| 6 | Filme que não existe | Pedir um id que não existe na TMDB dá `404` com uma mensagem clara. | `api_filmes`: `test_filme_inexistente_da_404` |
| 7 | TMDB em baixo | Sem ligação à TMDB, a API responde `503` em vez de rebentar. | `api_filmes`: `test_tmdb_em_baixo_da_503` |
| 8 | Pesquisa sem título ou id de filme inválido | A API recusa o pedido com `422`. | `api_filmes`: `test_pedidos_invalidos_dao_422` |
| 9 | Cache: pedir o mesmo filme duas vezes | O segundo pedido vem da cache e não chega à TMDB. | `catalogo`: `test_segundo_pedido_do_mesmo_filme_vem_da_cache` |
| 10 | Cache com mais de 24 horas | Uma resposta antiga volta a ser pedida à TMDB. | `catalogo`: `test_cache_expirada_volta_a_pedir_a_tmdb` |
| 11 | TMDB em baixo com cópia antiga na cache | A aplicação continua a mostrar o filme, com a cópia antiga. | `catalogo`: `test_tmdb_em_baixo_devolve_a_copia_antiga` |
| 12 | Pesquisas iguais escritas de forma diferente | " Matrix " e "matrix" usam a mesma entrada da cache. | `catalogo`: `test_pesquisas_iguais_com_maiusculas_e_espacos_usam_a_mesma_cache` |
| 13 | Dois pedidos ao mesmo filme ao mesmo tempo | Os dois gravam na cache sem erro (a ficha pede o filme e as notas em paralelo). | `catalogo`: `test_outro_pedido_a_gravar_o_mesmo_filme_ao_mesmo_tempo_nao_da_erro` |

## Fase 2: Playlists e notas

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 14 | Entrar só com o nome | Entrar duas vezes com o mesmo nome ("ana" e " Ana ") devolve o mesmo utilizador. | `api_playlists`: `test_entrar_duas_vezes_com_o_mesmo_nome_devolve_o_mesmo_utilizador` · `entidades`: `test_nome_de_utilizador_e_unico_sem_distinguir_maiusculas` |
| 15 | Nome vazio | Um nome só com espaços é recusado com `422`. | `api_playlists`: `test_nome_vazio_e_recusado` |
| 16 | Utilizador que não existe | Pedir as playlists de um id que não existe dá `404`. | `api_playlists`: `test_utilizador_inexistente_da_404` |
| 17 | Criar playlist com nome | A playlist é criada com o nome indicado e aparece nas playlists do utilizador. | `api_playlists`: todos os testes de playlists criam uma · navegador |
| 18 | Adicionar com a ★ | O filme entra no fim da playlist, e repetir o pedido não o duplica. | `api_playlists`: `test_adicionar_o_mesmo_filme_duas_vezes_nao_duplica` |
| 19 | Tirar com a ★ | O filme sai da playlist. | `api_playlists`: `test_remover_filme_da_playlist` |
| 20 | Mesmo filme duas vezes na mesma playlist | A própria base de dados recusa a repetição. | `entidades`: `test_mesmo_filme_duas_vezes_na_mesma_playlist_e_rejeitado` |
| 21 | Adicionar um filme que não existe | O filme não entra e a API responde `404`. | `api_playlists`: `test_filme_inexistente_nao_entra_na_playlist` |
| 22 | Playlists guardadas na base de dados | A playlist guarda os `tmdb_id` e devolve os filmes pela ordem. | `entidades`: `test_playlist_devolve_filmes_pela_ordem` · `api_playlists`: `test_detalhe_da_playlist_traz_os_dados_dos_filmes` |
| 23 | Playlists em destaque na página inicial | Depois de entrar, o Início mostra as playlists do utilizador, com o número de filmes. | navegador |
| 24 | Apagar playlist | A playlist deixa de aparecer, mas fica guardada como apagada. | `api_playlists`: `test_playlist_apagada_desaparece`, `test_listar_playlists_mostra_as_de_todos_menos_as_apagadas` |
| 25 | Dar nota de 1 a 10 e alterá-la | Dar nota duas vezes ao mesmo filme altera a nota, e fica só uma. | `api_playlists`: `test_dar_nota_e_alterar_depois_fica_uma_so_nota` |
| 26 | Uma nota por utilizador e por filme | A base de dados recusa uma segunda nota do mesmo utilizador ao mesmo filme. | `entidades`: `test_so_uma_nota_por_utilizador_e_filme` |
| 27 | Nota fora de 1 a 10 | Notas 0 e 11 são recusadas pela API (`422`) e pela base de dados. | `api_playlists`: `test_nota_fora_de_1_a_10_e_recusada` · `entidades`: `test_estrelas_fora_de_1_a_10_sao_rejeitadas` |
| 28 | Média das notas dos utilizadores | A ficha mostra a média e o número de notas dos utilizadores da aplicação. | `api_playlists`: `test_media_das_notas_dos_utilizadores` |

## Dados de exemplo (seed)

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 29 | Comando de importação | `importar-seed` cria 3 utilizadores, 10 playlists e 20 notas, e as notas mantêm a data do ficheiro. | `importar`: `test_importa_utilizadores_playlists_e_notas`, `test_notas_mantem_a_data_do_seed` · pasta limpa |
| 30 | Importar duas vezes | A segunda importação não cria nada e não duplica dados. | `importar`: `test_correr_duas_vezes_nao_duplica` · pasta limpa |
| 31 | Playlists apagadas no seed | São importadas como apagadas e não aparecem na aplicação. | `importar`: `test_playlists_apagadas_sao_importadas_mas_nao_aparecem` |
| 32 | Filme repetido na mesma playlist | Fica só a 1.ª ocorrência e a repetição aparece como aviso. | `importar`: `test_filme_repetido_fica_so_na_primeira_ocorrencia` |
| 33 | Filmes só em playlists apagadas | O relatório da importação lista-os (289, 348, 550 e 807). | `importar`: `test_filmes_so_em_playlists_apagadas_sao_assinalados` |
| 34 | Filmes com o mesmo título e anos diferentes | Os dois "Dune" e os dois "O Rei Leão" são filmes distintos (pelo `tmdb_id`) e distinguem-se pelo ano no ecrã. | navegador |
| 35 | Reimportar depois de mudar dados na aplicação | Uma nota alterada e um filme retirado continuam como o utilizador os deixou. | `importar`: `test_reimportar_nao_desfaz_alteracoes_feitas_na_app` |
| 36 | Ficheiro com formato errado | A importação é recusada e nada fica gravado. | `importar`: `test_ficheiro_com_formato_errado_nao_importa_nada` |

## Fase 3: Nota combinada e comparação

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 37 | 8,9 com 12 votos contra 8,4 com 30 000 votos | O primeiro fica com 6,76 e o segundo com 8,39, por isso o de 30 000 votos fica acima. | `nota_combinada`: `test_8_9_com_12_votos_fica_abaixo_de_8_4_com_30000_votos` |
| 38 | Três utilizadores a dar 10 | O filme de 12 votos só sobe para 6,84 e a ordem não muda. | `nota_combinada`: `test_tres_utilizadores_a_dar_10_nao_mudam_a_ordem` |
| 39 | Poucos votos contra muitos votos | Com poucos votos a nota fica perto de 6,5; com muitos, fica perto da média real. | `nota_combinada`: `test_com_poucos_votos_a_nota_aproxima_se_da_nota_neutra`, `test_com_muitos_votos_a_nota_fica_perto_da_media_real` |
| 40 | Sem votos na TMDB nem na aplicação | Não há nota combinada e a ficha diz "informação insuficiente". | `nota_combinada`: `test_filme_sem_votos_nao_tem_nota_combinada` |
| 41 | Filme sem votos na TMDB, mas com notas na aplicação | Tem nota combinada, calculada só com as notas dos utilizadores. | `nota_combinada`: `test_filme_so_com_notas_da_aplicacao_tambem_tem_nota` |
| 42 | Nota sempre entre 0 e 10 | Mesmo nos extremos (médias 0 e 10), a nota fica dentro da escala. | `nota_combinada`: `test_a_nota_fica_sempre_entre_0_e_10` |
| 43 | Ficha mostra a nota combinada | Aparece ao lado da nota da TMDB, com o número de votos em que se baseia e a explicação. | `api_playlists`: `test_notas_do_filme_trazem_a_nota_combinada` · `nota_combinada`: `test_texto_e_explicacao_indicam_os_votos` · navegador |
| 44 | Comparar duas playlists | Ganha a que tem a maior média de nota combinada dos filmes. | `comparacao`: `test_ganha_a_playlist_com_a_maior_media_de_nota_combinada` · `api_playlists`: `test_comparar_duas_playlists_pela_api` |
| 45 | Filmes sem nota na comparação | Ficam de fora da média, mas são contados e indicados. | `comparacao`: `test_filmes_sem_votos_ficam_de_fora_da_media_mas_sao_contados` |
| 46 | Médias iguais | O resultado é empate. | `comparacao`: `test_medias_iguais_dao_empate` |
| 47 | Playlist sem nenhum filme com nota | Não há vencedora e o resultado diz "informação insuficiente". | `comparacao`: `test_playlist_sem_filmes_com_nota_nao_tem_vencedora` |
| 48 | Outras comparações | Mostra o número de filmes, o melhor filme de cada uma, os filmes em comum e os que só estão numa. | `comparacao`: `test_extras_em_comum_so_numa_e_melhor_filme` · navegador |
| 49 | Comparar uma playlist com ela própria | É recusado com `422` e uma mensagem clara. | `api_playlists`: `test_comparar_a_mesma_playlist_e_recusado` |

## Exportação

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 50 | Exportar depois de importar o seed | O ficheiro exportado tem os mesmos utilizadores, playlists e notas do seed (sem o filme repetido). | `exportar`: `test_exportar_depois_do_seed_devolve_os_mesmos_dados` |
| 51 | Importar a exportação | Na mesma base de dados não duplica nada, e numa base nova reproduz os dados. | `exportar`: `test_importar_a_exportacao_na_mesma_base_nao_duplica_nada`, `test_levar_a_exportacao_para_outra_base_de_dados_reproduz_os_dados` |

## Segurança e requisitos técnicos

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 52 | Nota 20 (ou -5, 9,5, texto) enviada diretamente à API | É recusada com `422`; se o código da aplicação fosse contornado, a base de dados recusava-a na mesma, e um seed com nota 20 não importa nada. | `seguranca`: `test_nota_fora_de_1_a_10_ou_que_nao_e_inteiro_e_recusada_pela_api`, `test_nota_20_e_recusada_pela_base_de_dados_mesmo_contornando_a_api`, `test_seed_com_nota_20_e_recusado_sem_importar_nada` |
| 53 | SQL injection no nome e na pesquisa | O texto com SQL é guardado como texto e nenhuma tabela é afetada. | `seguranca`: `test_sql_injection_no_nome_e_guardado_como_texto`, `test_sql_injection_na_pesquisa_nao_afeta_a_base_de_dados` |
| 54 | Token da TMDB | O token nunca é devolvido pela API: o `/api/health` diz só se está configurado. | `health`: `test_health_nunca_expoe_o_token` |
| 55 | Instalação numa pasta limpa | Seguindo o README num clone novo (sem `.venv` nem base de dados), a instalação, os 110 testes, a importação, a exportação e o arranque funcionaram; a base de dados foi criada sozinha e o `.env`, a base de dados e a exportação ficaram fora do Git. | pasta limpa · `health`: `test_pagina_inicial_e_servida` |

---

## O que não foi feito

- **O jogo "mais alto ou mais baixo"** (opcional) não foi implementado. A decisão está no
  [DECISIONS.md](DECISIONS.md#jogo-mais-alto-ou-mais-baixo).
- **Login com palavra-passe** (opcional): os utilizadores identificam-se só pelo nome, como o
  enunciado permite.
