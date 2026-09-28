// Frontend do MovieUniverse Hub: uma single page app sem frameworks.
// Cada ecrã tem um endereço depois do # (ex.: #/filme/603, #/comparar?a=1&b=2); quando o #
// muda, o evento "hashchange" desenha o ecrã certo dentro do <main id="conteudo">.

import { api } from "./api.js";
import { avisar, confirmar } from "./avisos.js";
import { abrirMenu, fecharMenu, htmlEstrela } from "./estrela.js";
import {
    aoMudarSessao, atualizarPlaylist, entrar, iniciarSessao, recarregarPlaylists, sair, sessao,
} from "./sessao.js";
import {
    contar, esc, formatarData, formatarDuracao, formatarMedia, htmlAvatar, htmlPoster, htmlSemCartaz, mesmoNome,
} from "./util.js";

const conteudo = document.getElementById("conteudo");
const campoPesquisa = document.getElementById("campo-pesquisa");
const areaUtilizador = document.getElementById("area-utilizador");

const PAGINA_MAXIMA = 500; // a TMDB não devolve páginas acima da 500
const SUGESTOES = ["Matrix", "Interstellar", "Dune", "Toy Story", "Batman"];

/** O título do separador do navegador: "A Origem · MovieUniverse Hub". */
function mudarTitulo(texto) {
    document.title = texto ? `${texto} · MovieUniverse Hub` : "MovieUniverse Hub";
}

function mostrarMensagem(texto, classe = "") {
    conteudo.innerHTML = `<p class="estado ${classe}">${esc(texto)}</p>`;
}

function mostrarErro(texto) {
    conteudo.innerHTML = `
        <div class="estado erro">
            <p>${esc(texto)}</p>
            <button type="button" class="botao-secundario" data-acao="recarregar">Tentar outra vez</button>
        </div>`;
}

/** O que aparece enquanto a API responde: esqueletos com a forma do ecrã que aí vem. */
function htmlCarregando(caminho) {
    if (caminho === "/pesquisa" || caminho.startsWith("/playlist/")) {
        const card = `
            <div>
                <div class="esqueleto" style="aspect-ratio: 2 / 3"></div>
                <div class="esqueleto esqueleto-texto"></div>
                <div class="esqueleto esqueleto-texto curto"></div>
            </div>`;
        return `<div class="esqueleto esqueleto-titulo"></div><div class="grelha">${card.repeat(12)}</div>`;
    }
    return `<div class="orbita" role="progressbar" aria-label="A carregar"></div>`;
}

// --- Topo: entrar / sair ---------------------------------------------------------

function desenharAreaUtilizador() {
    if (sessao.utilizador) {
        areaUtilizador.innerHTML = `
            <span class="utilizador">
                ${htmlAvatar(sessao.utilizador.nome)}
                <span class="utilizador-nome">${esc(sessao.utilizador.nome)}</span>
            </span>
            <button type="button" class="botao-secundario botao-sair" data-acao="sair">Sair</button>`;
    } else {
        areaUtilizador.innerHTML = `
            <form id="form-entrar" class="form-entrar">
                <input name="nome" placeholder="O teu nome" maxlength="50" required aria-label="O teu nome">
                <button type="submit">Entrar</button>
            </form>`;
    }
}

/** Quando alguém tenta usar a ★ ou dar nota sem ter entrado: leva-o ao campo do nome. */
function pedirParaEntrar() {
    const campo = areaUtilizador.querySelector("input[name=nome]");
    campo?.focus();
    campo?.classList.add("chamar-atencao");
    setTimeout(() => campo?.classList.remove("chamar-atencao"), 1200);
    avisar("Entra com o teu nome (no topo) para usares a ★ e dares notas.");
}

// --- Cards de filmes ---------------------------------------------------------------

function htmlCard(filme, { extra = "", posicao = null, info = null } = {}) {
    return `
        <article class="card">
            <a class="card-link" href="#/filme/${filme.tmdb_id}">
                <div class="card-cartaz">
                    ${htmlPoster(filme, "poster", { decorativo: true })}
                    ${posicao ? `<span class="posicao">${posicao}</span>` : ""}
                </div>
                <span class="card-titulo">${esc(filme.titulo)}</span>
                <span class="card-info">${info ?? `${filme.ano ?? "ano desconhecido"} · ${esc(filme.nota_tmdb_texto)}`}</span>
            </a>
            ${htmlEstrela(filme.tmdb_id)}
            ${extra}
        </article>`;
}

// --- Cartões de playlist com a pilha de cartazes ---------------------------------------
// Os cartazes de cada playlist vêm de /api/playlists/{id}. Ficam guardados por id + filmes,
// e os pedidos vão dois de cada vez (a TMDB limita os pedidos por segundo).

const cartazesDasPlaylists = new Map();

function filmesDaPlaylist(resumo) {
    const chave = `${resumo.id}:${resumo.tmdb_ids.join(",")}`;
    if (!cartazesDasPlaylists.has(chave)) {
        const pedido = api.playlist(resumo.id)
            .then((playlist) => playlist.filmes.map((item) => item.filme).filter(Boolean))
            .catch((erro) => {
                cartazesDasPlaylists.delete(chave);
                throw erro;
            });
        cartazesDasPlaylists.set(chave, pedido);
    }
    return cartazesDasPlaylists.get(chave);
}

async function emFila(tarefas, emSimultaneo = 2) {
    const fila = [...tarefas];
    const trabalhador = async () => {
        while (fila.length) await fila.shift()().catch(() => {});
    };
    await Promise.all(Array.from({ length: emSimultaneo }, trabalhador));
}

/** `vazia`: o texto para quando não há cartazes (playlist vazia, ou a TMDB não respondeu). */
function htmlPilha(filmes, vazia = "Ainda sem filmes") {
    if (!filmes.length) return `<div class="pilha-vazia">${vazia}</div>`;
    return filmes.slice(0, 5).map((f) => htmlPoster(f, "poster", { decorativo: true })).join("");
}

function htmlCartaoPlaylist(playlist, { comDono = true } = {}) {
    const n = playlist.tmdb_ids.length;
    const pilha = n
        ? `<div class="esqueleto"></div>`.repeat(Math.min(n, 4))
        : `<div class="pilha-vazia">Ainda sem filmes</div>`;
    const detalhe = comDono
        ? `${htmlAvatar(playlist.dono, "avatar-pequeno")} ${esc(playlist.dono)} · ${contar(n, "filme")}`
        : `${contar(n, "filme")} · criada em ${formatarData(playlist.criada_em)}`;
    return `
        <a class="cartao-playlist" href="#/playlist/${playlist.id}">
            <div class="pilha" data-pilha="${playlist.id}" aria-hidden="true">${pilha}</div>
            <div>
                <span class="cartao-playlist-nome">${esc(playlist.nome)}</span>
                <div class="cartao-playlist-dono card-info">${detalhe}</div>
            </div>
        </a>`;
}

/** Enche as pilhas que estão no ecrã, à medida que os cartazes chegam. */
function preencherPilhas(playlists, ehAtual) {
    const tarefas = playlists.filter((p) => p.tmdb_ids.length).map((p) => async () => {
        const filmes = await filmesDaPlaylist(p).catch(() => []); // ex.: sem token da TMDB
        const pilha = ehAtual() && document.querySelector(`[data-pilha="${p.id}"]`);
        if (pilha) pilha.innerHTML = htmlPilha(filmes, "Cartazes indisponíveis");
    });
    return emFila(tarefas);
}

// --- Ecrãs -----------------------------------------------------------------------
// Cada ecrã recebe `ehAtual()`: se o utilizador já navegou para outro sítio enquanto a API
// respondia, não desenha nada (evita um ecrã antigo por cima do novo).

async function ecraInicio(ehAtual) {
    campoPesquisa.value = "";
    const todas = await api.todasAsPlaylists().catch(() => []);
    if (!ehAtual()) return;

    if (!sessao.utilizador) {
        desenharBoasVindas(todas);
        await Promise.all([preencherPilhas(todas, ehAtual), preencherLeque(todas, ehAtual)]);
        return;
    }

    const minhas = sessao.playlists;
    const outras = todas.filter((p) => !mesmoNome(p.dono, sessao.utilizador.nome));

    conteudo.innerHTML = `
        <section>
            <h1 class="saudacao">Olá, <span class="destaque">${esc(sessao.utilizador.nome)}</span></h1>
            <p class="saudacao-texto">${minhas.length
                ? `Tens ${contar(minhas.length, "playlist")}. Junta-lhes filmes com a ★ em qualquer cartaz.`
                : "Cria a tua primeira playlist aqui, ou usa a ★ num filme."}</p>
        </section>
        <section class="secao">
            <div class="secao-cabecalho"><h2 class="secao-titulo">As tuas playlists</h2></div>
            <div class="grelha-playlists">
                ${minhas.map((p) => htmlCartaoPlaylist(p, { comDono: false })).join("")}
                <div class="cartao-playlist cartao-nova">
                    <span class="cartao-nova-icone" aria-hidden="true">+</span>
                    <form id="form-nova-playlist" class="nova-playlist">
                        <input name="nome" placeholder="Nome da nova playlist" maxlength="100" required
                               aria-label="Nome da nova playlist">
                        <button type="submit">Criar playlist</button>
                    </form>
                </div>
            </div>
        </section>
        ${htmlSecaoComunidade(outras)}`;

    await preencherPilhas([...minhas, ...outras], ehAtual);
}

function desenharBoasVindas(todas) {
    const sugestoes = SUGESTOES.map((titulo) =>
        `<a class="chip" href="#/pesquisa?${new URLSearchParams({ titulo, pagina: 1 })}">${esc(titulo)}</a>`).join("");

    conteudo.innerHTML = `
        <section class="hero">
            <div>
                <h1>O teu universo de filmes, <span class="destaque">em playlists</span>.</h1>
                <p class="hero-texto">Pesquisa qualquer filme da TMDB, guarda-o com a ★, dá a tua nota
                    e descobre qual playlist tem o melhor rating.</p>
                <form class="pesquisa form-pesquisa hero-pesquisa" role="search">
                    <button type="submit" class="pesquisa-botao" aria-label="Pesquisar">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
                    </button>
                    <input type="search" name="titulo" required maxlength="200" autocomplete="off"
                           placeholder="Que filme procuras?" aria-label="Título do filme">
                </form>
                <div class="sugestoes"><span>Experimenta:</span>${sugestoes}</div>
            </div>
            <div class="leque" aria-hidden="true"></div>
        </section>

        <ol class="passos">
            <li class="passo"><span class="passo-numero">1</span>
                <div><strong>Pesquisa</strong><p>Encontra filmes pelo título, com a nota e os votos da TMDB.</p></div></li>
            <li class="passo"><span class="passo-numero">2</span>
                <div><strong>Guarda com a ★</strong><p>Entra com o teu nome, junta filmes às tuas playlists e dá notas de 1 a 10.</p></div></li>
            <li class="passo"><span class="passo-numero">3</span>
                <div><strong>Compara</strong><p>A nota combinada junta a TMDB e a app para dizer que playlist ganha.</p></div></li>
        </ol>

        ${htmlSecaoComunidade(todas)}`;
}

function htmlSecaoComunidade(playlists) {
    if (!playlists.length) return "";
    return `
        <section class="secao">
            <div class="secao-cabecalho">
                <h2 class="secao-titulo">Playlists da comunidade</h2>
                <a href="#/comparar">Comparar playlists →</a>
            </div>
            <div class="grelha-playlists">${playlists.map((p) => htmlCartaoPlaylist(p)).join("")}</div>
        </section>`;
}

/** O leque de cartazes ao lado do título, com os cartazes das primeiras playlists. */
async function preencherLeque(playlists, ehAtual) {
    const cartazes = [];
    for (const p of playlists.filter((p) => p.tmdb_ids.length)) {
        const filmes = await filmesDaPlaylist(p).catch(() => []);
        for (const f of filmes) {
            if (f.poster_url && !cartazes.some((c) => c.tmdb_id === f.tmdb_id)) cartazes.push(f);
        }
        if (cartazes.length >= 5) break;
    }
    const leque = ehAtual() && conteudo.querySelector(".leque");
    if (leque) leque.innerHTML = cartazes.slice(0, 5).map((f, i) =>
        `<img src="${esc(f.poster_url)}" alt="" style="--i: ${i - 2}; animation-delay: ${i * 80}ms">`).join("");
}

async function ecraPesquisa(params, ehAtual) {
    const titulo = (params.get("titulo") || "").trim();
    const pagina = Number(params.get("pagina")) || 1;
    campoPesquisa.value = titulo;
    if (!titulo) return ecraInicio(ehAtual);

    const resultado = await api.pesquisar(titulo, pagina);
    if (!ehAtual()) return;

    if (resultado.filmes.length === 0) {
        const sugestoes = SUGESTOES.map((t) =>
            `<a class="chip" href="#/pesquisa?${new URLSearchParams({ titulo: t, pagina: 1 })}">${esc(t)}</a>`).join("");
        conteudo.innerHTML = `
            <div class="estado">
                <p>Nenhum filme encontrado para "${esc(titulo)}".</p>
                <div class="sugestoes" style="justify-content: center">${sugestoes}</div>
            </div>`;
        return;
    }

    mudarTitulo(`Pesquisa: ${titulo}`);
    conteudo.innerHTML = `
        <h1 class="titulo-ecra">Resultados para "${esc(titulo)}"
            <small>${contar(resultado.total_resultados, "filme")}</small></h1>
        <div class="grelha">${resultado.filmes.map((f) => htmlCard(f)).join("")}</div>
        ${htmlPaginacao(titulo, resultado.pagina, Math.min(resultado.total_paginas, PAGINA_MAXIMA))}`;
}

function htmlPaginacao(titulo, pagina, totalPaginas) {
    if (totalPaginas <= 1) return "";
    const link = (p, texto) =>
        `<a class="botao botao-secundario" href="#/pesquisa?${new URLSearchParams({ titulo, pagina: p })}">${texto}</a>`;
    return `
        <nav class="paginacao" aria-label="Páginas de resultados">
            ${pagina > 1 ? link(pagina - 1, "← Anterior") : "<span></span>"}
            <span>Página ${pagina} de ${totalPaginas}</span>
            ${pagina < totalPaginas ? link(pagina + 1, "Próxima →") : "<span></span>"}
        </nav>`;
}

async function ecraFilme(tmdbId, ehAtual) {
    // A ficha e as notas dos utilizadores, em paralelo.
    const [filme, notas] = await Promise.all([api.filme(tmdbId), api.notasDoFilme(tmdbId)]);
    if (!ehAtual()) return;

    // Imagem de fundo do topo; sem ela, o próprio cartaz desfocado.
    const fundo = filme.fundo_url ?? filme.poster_url;
    const topo = `
        <div class="ficha-topo ${filme.fundo_url ? "" : "desfocado"}" aria-hidden="true">
            ${fundo ? `<img src="${esc(fundo)}" alt="">` : ""}
        </div>`;
    const tituloOriginal = filme.titulo_original && filme.titulo_original !== filme.titulo
        ? `<p class="titulo-original">${esc(filme.titulo_original)}</p>`
        : "";
    const generos = filme.generos.length
        ? filme.generos.map((g) => `<span class="etiqueta">${esc(g.nome)}</span>`).join("")
        : `<span class="etiqueta">sem géneros</span>`;

    mudarTitulo(filme.titulo);
    conteudo.innerHTML = `
        ${topo}
        <article class="ficha">
            <button type="button" class="voltar" data-acao="voltar">← Voltar</button>
            <div class="ficha-lado">${htmlPoster(filme, "poster-grande")}</div>
            <div class="ficha-texto">
                <p class="meta">
                    ${filme.ano ? `<span>${filme.ano}</span>` : ""}
                    <span>${formatarDuracao(filme.duracao_min)}</span>
                </p>
                <h1>${esc(filme.titulo)}</h1>
                ${tituloOriginal}
                <div class="etiquetas">${generos}</div>
                <div class="acoes-ficha">${htmlEstrela(filme.tmdb_id, { comTexto: true })}</div>

                <section id="notas-filme" data-tmdb="${filme.tmdb_id}" data-nota-tmdb="${esc(filme.nota_tmdb_texto)}">
                    ${htmlNotas(filme.nota_tmdb_texto, notas)}
                </section>

                <section class="sinopse">
                    <h2>Sinopse</h2>
                    <p>${esc(filme.sinopse) || "Sem sinopse disponível."}</p>
                </section>
            </div>
        </article>`;
}

/** "8,4 · 40 258 votos" -> ["8,4", "40 258 votos"]; "sem votos" -> ["—", "sem votos"]. */
function partirNota(texto) {
    const [valor, votos] = texto.split(" · ");
    return votos ? [valor, votos] : ["—", texto];
}

/** Os três quadros de notas, a explicação da nota combinada e a escala "A tua nota". */
function htmlNotas(notaTmdbTexto, notas) {
    const combinada = notas.nota_combinada;
    const [valorTmdb, votosTmdb] = partirNota(notaTmdbTexto);
    const [, votosCombinada] = partirNota(combinada.texto);
    const percentagem = combinada.valor === null ? 0 : combinada.valor * 10;

    const avaliadores = notas.notas.map((n) => `
        <span class="avaliador" title="${esc(n.utilizador)} deu ${n.estrelas}">
            ${htmlAvatar(n.utilizador, "avatar-pequeno")}<b>${n.estrelas}</b>
        </span>`).join("");

    return `
        <div class="painel-notas">
            <div class="nota nota-combinada">
                <div class="anel" style="--p: ${percentagem}">${combinada.valor === null ? "—" : formatarMedia(combinada.valor)}</div>
                <div>
                    <span class="nota-rotulo">Nota combinada</span>
                    <div class="nota-votos">${esc(votosCombinada)}</div>
                </div>
            </div>
            <div class="nota">
                <span class="nota-rotulo">Nota TMDB</span>
                <span class="nota-valor">${esc(valorTmdb)}</span>
                <span class="nota-votos">${esc(votosTmdb)}</span>
            </div>
            <div class="nota">
                <span class="nota-rotulo">Utilizadores da app</span>
                <span class="nota-valor">${notas.num_notas ? formatarMedia(notas.media) : "—"}</span>
                <span class="nota-votos">${notas.num_notas ? contar(notas.num_notas, "nota") : "sem notas"}</span>
                ${avaliadores ? `<div class="avaliadores">${avaliadores}</div>` : ""}
            </div>
        </div>
        <details class="explicacao-nota" open>
            <summary>Como é calculada a nota combinada?</summary>
            <p>${esc(combinada.explicacao)}</p>
        </details>
        ${htmlAMinhaNota(notas)}`;
}

function htmlAMinhaNota(notas) {
    if (!sessao.utilizador) {
        return `
            <div class="a-minha-nota">
                <p class="texto-suave">Entra com o teu nome para dares a tua nota.</p>
                <button type="button" class="botao-secundario" data-acao="pedir-entrar">Entrar</button>
            </div>`;
    }

    const minha = notas.notas.find((n) => mesmoNome(n.utilizador, sessao.utilizador.nome));
    const botoes = Array.from({ length: 10 }, (_, i) => i + 1).map((valor) => `
        <button type="button" class="botao-nota ${minha && valor <= minha.estrelas ? "cheia" : ""}"
                style="--i: ${valor - 1}" data-nota="${valor}" aria-label="Dar nota ${valor}"
                aria-pressed="${minha?.estrelas === valor}">${valor}</button>`).join("");
    return `
        <div class="a-minha-nota">
            <span class="nota-rotulo">A tua nota</span>
            <div class="escala" role="group" aria-label="A tua nota, de 1 a 10">${botoes}</div>
            <span class="escala-valor">${minha ? `${minha.estrelas}<small>/10</small>` : ""}</span>
            ${minha ? `<button type="button" class="botao-secundario" data-acao="retirar-nota">Retirar nota</button>` : ""}
        </div>`;
}

/** Depois de dar ou retirar uma nota, volta a desenhar só a secção das notas. */
async function redesenharNotas() {
    const secao = document.getElementById("notas-filme");
    if (!secao) return;
    const notas = await api.notasDoFilme(Number(secao.dataset.tmdb));
    secao.innerHTML = htmlNotas(secao.dataset.notaTmdb, notas);
}

async function ecraPlaylist(playlistId, ehAtual) {
    const playlist = await api.playlist(playlistId);
    if (!ehAtual()) return;

    const souDono = sessao.utilizador && mesmoNome(playlist.dono, sessao.utilizador.nome);
    const cards = playlist.filmes.map((item, indice) => {
        const tirar = souDono
            ? `<button type="button" class="tirar" data-acao="tirar-filme" data-tmdb="${item.tmdb_id}"
                       title="Tirar da playlist" aria-label="Tirar da playlist">✕</button>`
            : "";
        if (item.filme) return htmlCard(item.filme, { extra: tirar, posicao: indice + 1 });
        return `
            <article class="card indisponivel">
                <div class="card-cartaz">
                    ${htmlSemCartaz(`Filme #${item.tmdb_id}`, "poster", "indisponível de momento")}
                    <span class="posicao">${indice + 1}</span>
                </div>
                ${tirar}
            </article>`;
    }).join("");

    const fundo = playlist.filmes.map((item) => item.filme?.poster_url).filter(Boolean).slice(0, 6)
        .map((url) => `<img src="${esc(url)}" alt="">`).join("");

    mudarTitulo(playlist.nome);
    conteudo.innerHTML = `
        <section class="playlist-topo">
            <div class="playlist-topo-fundo" aria-hidden="true">${fundo}</div>
            <div class="cabecalho-playlist" data-playlist="${playlist.id}">
                <div>
                    <p class="sobretitulo">Playlist</p>
                    <h1>${esc(playlist.nome)}</h1>
                    <div class="dono">
                        ${htmlAvatar(playlist.dono)}
                        <span>de <strong>${esc(playlist.dono)}</strong> · ${contar(playlist.filmes.length, "filme")}
                            · criada em ${formatarData(playlist.criada_em)}</span>
                    </div>
                </div>
                <div class="acoes-playlist">
                    <a class="botao" href="#/comparar?a=${playlist.id}">Comparar com…</a>
                    ${souDono ? `<button type="button" class="botao-perigo" data-acao="apagar-playlist">Apagar playlist</button>` : ""}
                </div>
            </div>
        </section>
        ${cards ? `<div class="grelha">${cards}</div>`
                : `<p class="estado">Esta playlist ainda não tem filmes. Pesquisa um filme e usa a ★ para o adicionar.</p>`}`;
}

async function ecraComparar(params, ehAtual) {
    const todas = await api.todasAsPlaylists();
    if (!ehAtual()) return;

    if (todas.length < 2) {
        return mostrarMensagem("São precisas pelo menos duas playlists para comparar.");
    }

    // Pré-seleção: o que vem no endereço; senão, a 1.ª playlist minha e a 1.ª de outra pessoa.
    const minhas = sessao.utilizador ? todas.filter((p) => mesmoNome(p.dono, sessao.utilizador.nome)) : [];
    const idA = Number(params.get("a")) || (minhas[0] ?? todas[0]).id;
    const idB = Number(params.get("b")) || (todas.find((p) => p.id !== idA && !minhas.includes(p)) ?? todas.find((p) => p.id !== idA)).id;

    const opcoes = (selecionada) => todas.map((p) => `
        <option value="${p.id}" ${p.id === selecionada ? "selected" : ""}>
            ${esc(p.nome)} (de ${esc(p.dono)}, ${contar(p.tmdb_ids.length, "filme")})
        </option>`).join("");

    conteudo.innerHTML = `
        <h1 class="titulo-ecra">Comparar playlists</h1>
        <form id="form-comparar" class="form-comparar">
            <select name="a" aria-label="Primeira playlist">${opcoes(idA)}</select>
            <span class="versus" aria-hidden="true">VS</span>
            <select name="b" aria-label="Segunda playlist">${opcoes(idB)}</select>
            <button type="submit">Comparar</button>
        </form>
        <div id="resultado-comparacao"></div>`;

    const resultadoDiv = document.getElementById("resultado-comparacao");

    // Só compara quando as duas vêm no endereço (depois de clicar em "Comparar").
    if (!params.get("a") || !params.get("b")) {
        resultadoDiv.innerHTML = `<p class="estado">Escolhe duas playlists e carrega em <strong>Comparar</strong>.
            Ganha a que tiver a melhor média de nota combinada.</p>`;
        return;
    }
    if (idA === idB) {
        resultadoDiv.innerHTML = `<p class="estado erro">Escolhe duas playlists diferentes.</p>`;
        return;
    }

    resultadoDiv.innerHTML = `
        <div class="orbita" role="progressbar" aria-label="A comparar"></div>
        <p class="estado">A comparar… (a primeira vez pode demorar, porque os filmes vêm da TMDB)</p>`;
    const comparacao = await api.comparar(idA, idB);
    if (!ehAtual()) return;
    resultadoDiv.innerHTML = htmlComparacao(comparacao);
}

function htmlListaFilmes(filmes, vazio) {
    if (!filmes.length) return `<p class="card-info">${vazio}</p>`;
    return `<ul class="lista-filmes">${filmes.map((f) => `
        <li class="filme-linha">
            <a href="#/filme/${f.tmdb_id}">
                ${htmlPoster(f, "poster", { decorativo: true })}
                <span class="filme-linha-texto">${esc(f.titulo)}
                    <span class="card-info">${f.ano ? `${f.ano} · ` : ""}${esc(f.nota_combinada.texto)}</span></span>
            </a>
        </li>`).join("")}</ul>`;
}

function htmlLado(lado, venceu, emComum) {
    const semNota = lado.num_filmes - lado.num_filmes_com_nota;
    const cartazes = [...lado.so_nesta, ...emComum];
    return `
        <section class="lado ${venceu ? "vencedora" : ""}">
            ${venceu ? `<span class="selo">Melhor rating</span>` : ""}
            <div class="pilha" aria-hidden="true">${htmlPilha(cartazes)}</div>
            <div>
                <h2><a href="#/playlist/${lado.playlist_id}">${esc(lado.nome)}</a></h2>
                <div class="dono card-info">${htmlAvatar(lado.dono, "avatar-pequeno")} de ${esc(lado.dono)}
                    · ${contar(lado.num_filmes, "filme")}</div>
            </div>
            <div>
                <span class="nota-rotulo">Média da nota combinada</span>
                <div class="media-grande">
                    <span class="nota-valor">${lado.media === null ? "—" : formatarMedia(lado.media, 2)}</span>
                    ${lado.media === null ? `<span class="nota-votos">sem informação</span>` : `<span class="nota-votos">/ 10</span>`}
                </div>
                <div class="medidor" aria-hidden="true"><span style="width: ${(lado.media ?? 0) * 10}%"></span></div>
            </div>
            ${semNota ? `<p class="card-info">${contar(semNota, "filme")} sem nota ${semNota === 1 ? "ficou" : "ficaram"} de fora da média.</p>` : ""}
            <h3>Melhor filme</h3>
            ${lado.melhor_filme ? htmlListaFilmes([lado.melhor_filme], "") : `<p class="card-info">—</p>`}
            <h3>Só nesta playlist</h3>
            ${htmlListaFilmes(lado.so_nesta, "Nenhum: todos os filmes estão também na outra.")}
        </section>`;
}

function htmlComparacao(c) {
    const diferenca = c.diferenca ? `<span class="diferenca">${formatarMedia(c.diferenca, 2)}<br>de diferença</span>` : "";
    const emComum = c.em_comum.map((f) => htmlCard(f, {
        info: `${f.ano ?? "ano desconhecido"} · ${esc(f.nota_combinada.texto)}`,
    })).join("");
    return `
        <p class="explicacao-comparacao">${esc(c.explicacao)}</p>
        <div class="arena">
            ${htmlLado(c.a, c.vencedora === "a", c.em_comum)}
            <div class="arena-meio"><span class="versus">VS</span>${diferenca}</div>
            ${htmlLado(c.b, c.vencedora === "b", c.em_comum)}
        </div>
        <section class="secao">
            <div class="secao-cabecalho">
                <h2 class="secao-titulo">Filmes em comum <small>${c.em_comum.length}</small></h2>
            </div>
            ${emComum ? `<div class="fila-cartazes">${emComum}</div>` : `<p class="card-info">Nenhum filme em comum.</p>`}
        </section>`;
}

async function ecraSobre(ehAtual) {
    let estado;
    try {
        const saude = await api.estado();
        estado = `
            <p><span class="estado-api">API online</span></p>
            <p>Token da TMDB: ${saude.tmdb_configurada ? "configurado." : "<strong>EM FALTA</strong> (ver o .env)."}</p>`;
    } catch (erro) {
        estado = `<p><span class="estado-api mal">${esc(erro.message)}</span></p>`;
    }
    if (!ehAtual()) return;

    conteudo.innerHTML = `
        <article class="sobre">
            <h1>Sobre</h1>
            <div class="caixa">
                <h2>O MovieUniverse Hub</h2>
                <p>Permite pesquisar filmes, criar playlists pessoais, dar notas e comparar playlists
                   usando uma nota combinada entre a TMDB e os utilizadores.</p>
                <h2>A nota combinada</h2>
                <p>Junta a média da TMDB e a média das notas da aplicação, pesadas pelo número de votos
                   de cada uma. Os filmes com poucos votos são puxados para uma nota neutra (6,5), por
                   isso um filme com um único 10 não passa à frente de um clássico com milhares de votos.</p>
            </div>
            <div class="caixa">
                <h2>Estado</h2>
                ${estado}
                <p><a href="/docs">Documentação da API (Swagger) →</a></p>
                <h2>Dados e atribuição</h2>
                <p>Os dados e as imagens dos filmes vêm da
                   <a href="https://www.themoviedb.org/" target="_blank" rel="noopener">The Movie Database (TMDB)</a>.
                   Este produto usa a API da TMDB, mas não é endossado nem certificado pela TMDB.</p>
            </div>
        </article>`;
}

// --- Navegação (router) ----------------------------------------------------------

let navegacaoAtual = 0;

function marcarMenu(caminho) {
    document.querySelectorAll(".menu a").forEach((link) => {
        if (link.dataset.rota === caminho) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
    });
}

async function navegar() {
    const numero = ++navegacaoAtual;
    const ehAtual = () => numero === navegacaoAtual;

    // "#/pesquisa?titulo=Dune" -> caminho "/pesquisa", query "titulo=Dune"
    const [caminho, query = ""] = (location.hash.slice(1) || "/").split("?");
    fecharMenu();
    marcarMenu(caminho);
    mudarTitulo({ "/comparar": "Comparar playlists", "/sobre": "Sobre" }[caminho]);
    window.scrollTo(0, 0);
    conteudo.innerHTML = htmlCarregando(caminho);

    try {
        if (caminho === "/") {
            await ecraInicio(ehAtual);
        } else if (caminho === "/pesquisa") {
            await ecraPesquisa(new URLSearchParams(query), ehAtual);
        } else if (/^\/filme\/\d+$/.test(caminho)) {
            await ecraFilme(Number(caminho.split("/")[2]), ehAtual);
        } else if (/^\/playlist\/\d+$/.test(caminho)) {
            await ecraPlaylist(Number(caminho.split("/")[2]), ehAtual);
        } else if (caminho === "/comparar") {
            await ecraComparar(new URLSearchParams(query), ehAtual);
        } else if (caminho === "/sobre") {
            await ecraSobre(ehAtual);
        } else {
            conteudo.innerHTML = `<p class="estado">Página não encontrada. <a href="#/">Voltar ao início</a></p>`;
        }
    } catch (erro) {
        if (ehAtual()) mostrarErro(erro.message);
    }
}

// --- Eventos ---------------------------------------------------------------------
// Os botões são recriados com innerHTML a cada ecrã, por isso há um só ouvinte no documento
// que vê em que botão se clicou (pelo data-acao).

document.addEventListener("submit", async (evento) => {
    const form = evento.target;
    if (form.classList.contains("form-pesquisa")) {
        evento.preventDefault(); // impede o <form> de recarregar a página
        const titulo = form.titulo.value.trim();
        if (titulo) location.hash = `#/pesquisa?${new URLSearchParams({ titulo, pagina: 1 })}`;
        form.titulo.blur();
    } else if (form.id === "form-entrar") {
        evento.preventDefault();
        try {
            await entrar(form.nome.value);
            avisar(`Olá, ${sessao.utilizador.nome}!`);
        } catch (erro) {
            avisar(erro.message, "erro");
        }
    } else if (form.id === "form-comparar") {
        evento.preventDefault();
        location.hash = `#/comparar?${new URLSearchParams({ a: form.a.value, b: form.b.value })}`;
    } else if (form.id === "form-nova-playlist") {
        evento.preventDefault();
        try {
            const nova = await api.criarPlaylist(sessao.utilizador.id, form.nome.value);
            atualizarPlaylist(nova);
            avisar(`Playlist "${nova.nome}" criada`);
            await navegar();
        } catch (erro) {
            avisar(erro.message, "erro");
        }
    }
});

document.addEventListener("click", async (evento) => {
    if (evento.target.closest(".saltar")) {
        evento.preventDefault(); // o # do link não é uma rota: só muda o foco para o conteúdo
        conteudo.focus();
        return;
    }

    const estrela = evento.target.closest(".estrela");
    if (estrela) {
        if (sessao.utilizador) abrirMenu(estrela);
        else pedirParaEntrar();
        return;
    }

    const botao = evento.target.closest("[data-acao], [data-nota]");
    if (!botao) return;

    try {
        if (botao.dataset.nota) {
            const tmdbId = Number(document.getElementById("notas-filme").dataset.tmdb);
            await api.darNota(sessao.utilizador.id, tmdbId, Number(botao.dataset.nota));
            await redesenharNotas();
            avisar(`Nota ${botao.dataset.nota} guardada`);
        } else if (botao.dataset.acao === "retirar-nota") {
            const tmdbId = Number(document.getElementById("notas-filme").dataset.tmdb);
            await api.retirarNota(sessao.utilizador.id, tmdbId);
            await redesenharNotas();
            avisar("Nota retirada");
        } else if (botao.dataset.acao === "voltar") {
            if (history.length > 1) history.back();
            else location.hash = "#/";
        } else if (botao.dataset.acao === "sair") {
            sair();
        } else if (botao.dataset.acao === "pedir-entrar") {
            pedirParaEntrar();
        } else if (botao.dataset.acao === "recarregar") {
            await navegar();
        } else if (botao.dataset.acao === "tirar-filme") {
            const playlistId = Number(document.querySelector(".cabecalho-playlist").dataset.playlist);
            atualizarPlaylist(await api.removerFilme(playlistId, Number(botao.dataset.tmdb)));
            avisar("Filme tirado da playlist");
            await navegar();
        } else if (botao.dataset.acao === "apagar-playlist") {
            const cabecalho = document.querySelector(".cabecalho-playlist");
            const nome = cabecalho.querySelector("h1").textContent;
            if (!(await confirmar(`Apagar a playlist "${nome}"?`, "Apagar"))) return;
            await api.apagarPlaylist(Number(cabecalho.dataset.playlist));
            await recarregarPlaylists();
            avisar(`Playlist "${nome}" apagada`);
            location.hash = "#/";
        }
    } catch (erro) {
        avisar(erro.message, "erro");
    }
});

// "/" em qualquer sítio (fora de um campo) vai para a pesquisa, como em muitos sites.
document.addEventListener("keydown", (evento) => {
    const aEscrever = evento.target.closest("input, textarea, select, [contenteditable]");
    if (evento.key === "/" && !aEscrever && !evento.ctrlKey && !evento.metaKey && !evento.altKey) {
        evento.preventDefault();
        campoPesquisa.focus();
    }
});

// Cartaz que não carrega (ex.: sem internet): troca-o pelo cartaz só com o título.
document.addEventListener("error", (evento) => {
    const imagem = evento.target;
    if (imagem.tagName !== "IMG" || !imagem.dataset.titulo) return;
    imagem.outerHTML = htmlSemCartaz(imagem.dataset.titulo, imagem.className);
}, true);

// Entrar ou sair: redesenha o topo e o ecrã atual (a ★ e as notas mudam).
aoMudarSessao(() => {
    desenharAreaUtilizador();
    navegar();
});

window.addEventListener("hashchange", navegar);

// Arranque: recupera quem tinha entrado, desenha o topo e o primeiro ecrã.
await iniciarSessao();
desenharAreaUtilizador();
navegar();
