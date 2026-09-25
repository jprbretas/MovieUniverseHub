// Frontend do MovieUniverse Hub: uma "single page app" simples, sem frameworks.
//
// Navegação: cada ecrã tem um endereço depois do #, por exemplo:
//   #/                          início (as minhas playlists)
//   #/pesquisa?titulo=Dune      resultados da pesquisa
//   #/filme/603                 ficha do filme (com as notas)
//   #/playlist/4                uma playlist
//   #/sobre                     ecrã "Sobre"
// Quando o # muda, o navegador dispara o evento "hashchange" e desenhamos o ecrã certo
// dentro do <main id="conteudo">. Os botões Voltar/Avançar do navegador funcionam sozinhos.
// (≈ as rotas do Blazor com @page "/filme/{id}", mas feitas à mão.)
//
// Ficheiros:
//   api.js     chamadas à API REST
//   sessao.js  quem entrou e as suas playlists
//   estrela.js a ★ e o menu "Guardar nas playlists"
//   util.js    esc(), formatações, cartaz
//   app.js     (este) navegação, ecrãs e eventos

import { api } from "./api.js";
import { abrirMenu, fecharMenu, htmlEstrela } from "./estrela.js";
import {
    aoMudarSessao, atualizarPlaylist, entrar, iniciarSessao, recarregarPlaylists, sair, sessao,
} from "./sessao.js";
import { esc, formatarData, formatarDuracao, formatarMedia, htmlPoster, mesmoNome } from "./util.js";

const conteudo = document.getElementById("conteudo");
const formPesquisa = document.getElementById("form-pesquisa");
const campoPesquisa = document.getElementById("campo-pesquisa");
const areaUtilizador = document.getElementById("area-utilizador");

const PAGINA_MAXIMA = 500; // a TMDB não devolve páginas acima da 500

function mostrarMensagem(texto, classe = "") {
    conteudo.innerHTML = `<p class="estado ${classe}">${esc(texto)}</p>`;
}

// --- Topo: entrar / sair ---------------------------------------------------------

function desenharAreaUtilizador() {
    if (sessao.utilizador) {
        areaUtilizador.innerHTML = `
            <span>Olá, <strong>${esc(sessao.utilizador.nome)}</strong></span>
            <button type="button" class="botao-secundario" data-acao="sair">Sair</button>`;
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
}

// --- Cards de filmes (usados na pesquisa e nas playlists) ------------------------

function htmlCard(filme, extra = "") {
    return `
        <div class="card">
            <a class="card-link" href="#/filme/${filme.tmdb_id}">
                ${htmlPoster(filme)}
                <span class="card-titulo">${esc(filme.titulo)}</span>
                <span class="card-info">${filme.ano ?? "ano desconhecido"} · ${esc(filme.nota_tmdb_texto)}</span>
            </a>
            ${htmlEstrela(filme.tmdb_id)}
            ${extra}
        </div>`;
}

// --- Ecrãs -----------------------------------------------------------------------
// Cada função recebe `ehAtual()`: se o utilizador já navegou para outro sítio enquanto
// esperávamos pela API, não desenhamos nada (evita um ecrã antigo "por cima" do novo).

function ecraInicio() {
    campoPesquisa.value = "";
    if (!sessao.utilizador) {
        conteudo.innerHTML = `
            <section class="boas-vindas">
                <h1>Descobre filmes</h1>
                <p>Pesquisa um título na caixa acima para começar.</p>
                <p>Entra com o teu nome (no topo, à direita) para criares playlists e dares notas.</p>
            </section>`;
        return;
    }

    const cartoes = sessao.playlists.map((p) => `
        <a class="cartao-playlist" href="#/playlist/${p.id}">
            <span class="cartao-playlist-nome">${esc(p.nome)}</span>
            <span class="card-info">${p.tmdb_ids.length} ${p.tmdb_ids.length === 1 ? "filme" : "filmes"}
                · criada em ${formatarData(p.criada_em)}</span>
        </a>`).join("");

    conteudo.innerHTML = `
        <h1 class="titulo-ecra">As tuas playlists</h1>
        ${cartoes ? `<div class="grelha-playlists">${cartoes}</div>`
                  : `<p class="estado">Ainda não tens playlists. Cria uma abaixo, ou usa a ☆ num filme.</p>`}
        <form id="form-nova-playlist" class="nova-playlist">
            <input name="nome" placeholder="Nome da nova playlist" maxlength="100" required aria-label="Nome da nova playlist">
            <button type="submit">Criar playlist</button>
        </form>`;
}

async function ecraPesquisa(params, ehAtual) {
    const titulo = (params.get("titulo") || "").trim();
    const pagina = Number(params.get("pagina")) || 1;
    campoPesquisa.value = titulo;
    if (!titulo) return ecraInicio();

    const resultado = await api.pesquisar(titulo, pagina);
    if (!ehAtual()) return;

    if (resultado.filmes.length === 0) {
        return mostrarMensagem(`Nenhum filme encontrado para "${titulo}".`);
    }

    conteudo.innerHTML = `
        <h1 class="titulo-ecra">Resultados para "${esc(titulo)}"
            <small>${resultado.total_resultados} filmes</small></h1>
        <div class="grelha">${resultado.filmes.map((f) => htmlCard(f)).join("")}</div>
        ${htmlPaginacao(titulo, resultado.pagina, Math.min(resultado.total_paginas, PAGINA_MAXIMA))}`;
}

function htmlPaginacao(titulo, pagina, totalPaginas) {
    if (totalPaginas <= 1) return "";
    const link = (p, texto) =>
        `<a class="botao" href="#/pesquisa?${new URLSearchParams({ titulo, pagina: p })}">${texto}</a>`;
    return `
        <nav class="paginacao" aria-label="Páginas de resultados">
            ${pagina > 1 ? link(pagina - 1, "← Anterior") : "<span></span>"}
            <span>Página ${pagina} de ${totalPaginas}</span>
            ${pagina < totalPaginas ? link(pagina + 1, "Próxima →") : "<span></span>"}
        </nav>`;
}

async function ecraFilme(tmdbId, ehAtual) {
    // As duas chamadas em paralelo (≈ Task.WhenAll): a ficha e as notas dos utilizadores.
    const [filme, notas] = await Promise.all([api.filme(tmdbId), api.notasDoFilme(tmdbId)]);
    if (!ehAtual()) return;

    const tituloOriginal = filme.titulo_original && filme.titulo_original !== filme.titulo
        ? `<p class="titulo-original">${esc(filme.titulo_original)}</p>`
        : "";
    const generos = filme.generos.length
        ? filme.generos.map((g) => `<span class="etiqueta">${esc(g.nome)}</span>`).join("")
        : `<span class="etiqueta">sem géneros</span>`;

    conteudo.innerHTML = `
        <button type="button" class="voltar" data-acao="voltar">← Voltar</button>
        <article class="ficha">
            ${htmlPoster(filme, "poster-grande")}
            <div class="ficha-texto">
                <div class="ficha-cabecalho">
                    <h1>${esc(filme.titulo)} ${filme.ano ? `<small>(${filme.ano})</small>` : ""}</h1>
                    ${htmlEstrela(filme.tmdb_id)}
                </div>
                ${tituloOriginal}
                <p class="meta">${formatarDuracao(filme.duracao_min)}</p>
                <div class="etiquetas">${generos}</div>

                <section id="notas-filme" data-tmdb="${filme.tmdb_id}" data-nota-tmdb="${esc(filme.nota_tmdb_texto)}">
                    ${htmlNotas(filme.nota_tmdb_texto, notas)}
                </section>

                <h2>Sinopse</h2>
                <p>${esc(filme.sinopse) || "Sem sinopse disponível."}</p>
            </div>
        </article>`;
}

/** As caixas de notas (TMDB e utilizadores) e os botões "A tua nota". */
function htmlNotas(notaTmdbTexto, notas) {
    const textoUtilizadores = notas.num_notas
        ? `${formatarMedia(notas.media)} · ${notas.num_notas} ${notas.num_notas === 1 ? "nota" : "notas"}`
        : "sem notas";

    let aMinha;
    if (!sessao.utilizador) {
        aMinha = `<p class="card-info">Entra com o teu nome para dares a tua nota.</p>`;
    } else {
        const minha = notas.notas.find((n) => mesmoNome(n.utilizador, sessao.utilizador.nome));
        const botoes = Array.from({ length: 10 }, (_, i) => i + 1).map((valor) => `
            <button type="button" class="botao-nota ${minha?.estrelas === valor ? "selecionada" : ""}"
                    data-nota="${valor}" aria-label="Dar nota ${valor}">${valor}</button>`).join("");
        aMinha = `
            <div class="a-minha-nota">
                <span class="nota-rotulo">A tua nota</span>
                <div class="botoes-nota">${botoes}</div>
                ${minha ? `<button type="button" class="botao-secundario" data-acao="retirar-nota">Retirar nota</button>` : ""}
            </div>`;
    }

    return `
        <div class="notas">
            <div class="nota">
                <span class="nota-rotulo">Nota TMDB</span>
                <span class="nota-valor">${esc(notaTmdbTexto)}</span>
            </div>
            <div class="nota">
                <span class="nota-rotulo">Utilizadores da app</span>
                <span class="nota-valor">${textoUtilizadores}</span>
            </div>
        </div>
        ${aMinha}`;
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
    const cards = playlist.filmes.map((item) => {
        const tirar = souDono
            ? `<button type="button" class="tirar" data-acao="tirar-filme" data-tmdb="${item.tmdb_id}"
                       title="Tirar da playlist" aria-label="Tirar da playlist">✕</button>`
            : "";
        return item.filme
            ? htmlCard(item.filme, tirar)
            : `<div class="card indisponivel">Filme #${item.tmdb_id}<br>(indisponível de momento)${tirar}</div>`;
    }).join("");

    conteudo.innerHTML = `
        <div class="cabecalho-playlist" data-playlist="${playlist.id}">
            <div>
                <h1 class="titulo-ecra">${esc(playlist.nome)}</h1>
                <p class="card-info">de ${esc(playlist.dono)} · ${playlist.filmes.length}
                    ${playlist.filmes.length === 1 ? "filme" : "filmes"}</p>
            </div>
            ${souDono ? `<button type="button" class="botao-perigo" data-acao="apagar-playlist">Apagar playlist</button>` : ""}
        </div>
        ${cards ? `<div class="grelha">${cards}</div>`
                : `<p class="estado">Esta playlist ainda não tem filmes. Pesquisa um filme e usa a ☆ para o adicionar.</p>`}`;
}

async function ecraSobre(ehAtual) {
    let estado;
    try {
        const saude = await api.estado();
        estado = `API online · token da TMDB ${saude.tmdb_configurada ? "configurado" : "EM FALTA (ver o .env)"}`;
    } catch (erro) {
        estado = erro.message;
    }
    if (!ehAtual()) return;

    conteudo.innerHTML = `
        <article class="sobre">
            <h1>Sobre</h1>
            <p>O MovieUniverse Hub permite pesquisar filmes, criar playlists pessoais, dar notas
               e comparar playlists usando uma nota combinada entre a TMDB e os utilizadores.</p>

            <h2>Dados e atribuição</h2>
            <p>Os dados e as imagens dos filmes vêm da
               <a href="https://www.themoviedb.org/" target="_blank" rel="noopener">The Movie Database (TMDB)</a>.
               Este produto usa a API da TMDB, mas não é endossado nem certificado pela TMDB.</p>

            <h2>Estado</h2>
            <p>${esc(estado)}</p>
            <p><a href="/docs">Documentação da API (Swagger)</a></p>
        </article>`;
}

// --- Navegação (router) ----------------------------------------------------------

let navegacaoAtual = 0;

async function navegar() {
    const numero = ++navegacaoAtual;
    const ehAtual = () => numero === navegacaoAtual;

    // "#/pesquisa?titulo=Dune" -> caminho "/pesquisa", query "titulo=Dune"
    const [caminho, query = ""] = (location.hash.slice(1) || "/").split("?");
    fecharMenu();
    window.scrollTo(0, 0);
    mostrarMensagem("A carregar…");

    try {
        if (caminho === "/") {
            ecraInicio();
        } else if (caminho === "/pesquisa") {
            await ecraPesquisa(new URLSearchParams(query), ehAtual);
        } else if (/^\/filme\/\d+$/.test(caminho)) {
            await ecraFilme(Number(caminho.split("/")[2]), ehAtual);
        } else if (/^\/playlist\/\d+$/.test(caminho)) {
            await ecraPlaylist(Number(caminho.split("/")[2]), ehAtual);
        } else if (caminho === "/sobre") {
            await ecraSobre(ehAtual);
        } else {
            conteudo.innerHTML = `<p class="estado">Página não encontrada. <a href="#/">Voltar ao início</a></p>`;
        }
    } catch (erro) {
        if (ehAtual()) mostrarMensagem(erro.message, "erro");
    }
}

// --- Eventos ---------------------------------------------------------------------
// Os botões são desenhados e redesenhados com innerHTML, por isso usamos "delegação":
// um só ouvinte no documento que vê em que botão se clicou (pelo data-acao).

formPesquisa.addEventListener("submit", (evento) => {
    evento.preventDefault(); // impede o <form> de recarregar a página
    const titulo = campoPesquisa.value.trim();
    if (titulo) location.hash = `#/pesquisa?${new URLSearchParams({ titulo, pagina: 1 })}`;
});

document.addEventListener("submit", async (evento) => {
    const form = evento.target;
    if (form.id === "form-entrar") {
        evento.preventDefault();
        try {
            await entrar(form.nome.value);
        } catch (erro) {
            alert(erro.message);
        }
    } else if (form.id === "form-nova-playlist") {
        evento.preventDefault();
        try {
            atualizarPlaylist(await api.criarPlaylist(sessao.utilizador.id, form.nome.value));
            ecraInicio();
        } catch (erro) {
            alert(erro.message);
        }
    }
});

document.addEventListener("click", async (evento) => {
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
        } else if (botao.dataset.acao === "retirar-nota") {
            const tmdbId = Number(document.getElementById("notas-filme").dataset.tmdb);
            await api.retirarNota(sessao.utilizador.id, tmdbId);
            await redesenharNotas();
        } else if (botao.dataset.acao === "voltar") {
            if (history.length > 1) history.back();
            else location.hash = "#/";
        } else if (botao.dataset.acao === "sair") {
            sair();
        } else if (botao.dataset.acao === "tirar-filme") {
            const playlistId = Number(document.querySelector(".cabecalho-playlist").dataset.playlist);
            atualizarPlaylist(await api.removerFilme(playlistId, Number(botao.dataset.tmdb)));
            await navegar();
        } else if (botao.dataset.acao === "apagar-playlist") {
            const playlistId = Number(document.querySelector(".cabecalho-playlist").dataset.playlist);
            if (!confirm("Apagar esta playlist?")) return;
            await api.apagarPlaylist(playlistId);
            await recarregarPlaylists();
            location.hash = "#/";
        }
    } catch (erro) {
        alert(erro.message);
    }
});

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
