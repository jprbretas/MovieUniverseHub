// Frontend do MovieUniverse Hub: uma "single page app" simples, sem frameworks.
//
// Navegação: cada ecrã tem um endereço depois do #, por exemplo:
//   #/                          início
//   #/pesquisa?titulo=Dune      resultados da pesquisa
//   #/filme/603                 ficha do filme
//   #/sobre                     ecrã "Sobre"
// Quando o # muda, o navegador dispara o evento "hashchange" e desenhamos o ecrã certo
// dentro do <main id="conteudo">. Os botões Voltar/Avançar do navegador funcionam sozinhos.
// (≈ as rotas do Blazor com @page "/filme/{id}", mas feitas à mão.)

import { api } from "./api.js";

const conteudo = document.getElementById("conteudo");
const formPesquisa = document.getElementById("form-pesquisa");
const campoPesquisa = document.getElementById("campo-pesquisa");

const PAGINA_MAXIMA = 500; // a TMDB não devolve páginas acima da 500

// --- Utilitários ---------------------------------------------------------------

/**
 * Escapa texto antes de o pôr dentro de HTML (≈ o que o Razor faz sozinho com @variavel).
 * Sem isto, um título vindo da TMDB com "<script>" seria executado no navegador (XSS).
 * Regra: TODO o texto que vem da API passa por esc() antes de entrar no innerHTML.
 */
function esc(texto) {
    const trocas = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(texto ?? "").replace(/[&<>"']/g, (c) => trocas[c]);
}

function formatarDuracao(minutos) {
    if (!minutos) return "duração desconhecida";
    const horas = Math.floor(minutos / 60);
    const resto = minutos % 60;
    return horas ? `${horas} h ${String(resto).padStart(2, "0")} min` : `${resto} min`;
}

function htmlPoster(filme, classe = "poster") {
    return filme.poster_url
        ? `<img class="${classe}" src="${esc(filme.poster_url)}" alt="Cartaz de ${esc(filme.titulo)}" loading="lazy">`
        : `<div class="${classe} sem-cartaz">sem cartaz</div>`;
}

function mostrarMensagem(texto, classe = "") {
    conteudo.innerHTML = `<p class="estado ${classe}">${esc(texto)}</p>`;
}

// --- Ecrãs ---------------------------------------------------------------------
// Cada função recebe `ehAtual()`: se o utilizador já navegou para outro sítio enquanto
// esperávamos pela API, não desenhamos nada (evita um ecrã antigo "por cima" do novo).

function ecraInicio() {
    campoPesquisa.value = "";
    conteudo.innerHTML = `
        <section class="boas-vindas">
            <h1>Descobre filmes</h1>
            <p>Pesquisa um título na caixa acima para começar.</p>
        </section>`;
    campoPesquisa.focus();
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

    const cards = resultado.filmes.map((filme) => `
        <a class="card" href="#/filme/${filme.tmdb_id}">
            ${htmlPoster(filme)}
            <span class="card-titulo">${esc(filme.titulo)}</span>
            <span class="card-info">${filme.ano ?? "ano desconhecido"} · ${esc(filme.nota_tmdb_texto)}</span>
        </a>`).join("");

    conteudo.innerHTML = `
        <h1 class="titulo-ecra">Resultados para "${esc(titulo)}"
            <small>${resultado.total_resultados} filmes</small></h1>
        <div class="grelha">${cards}</div>
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
    const filme = await api.filme(tmdbId);
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
                <h1>${esc(filme.titulo)} ${filme.ano ? `<small>(${filme.ano})</small>` : ""}</h1>
                ${tituloOriginal}
                <p class="meta">${formatarDuracao(filme.duracao_min)}</p>
                <div class="etiquetas">${generos}</div>

                <div class="notas">
                    <div class="nota">
                        <span class="nota-rotulo">Nota TMDB</span>
                        <span class="nota-valor">${esc(filme.nota_tmdb_texto)}</span>
                    </div>
                </div>

                <h2>Sinopse</h2>
                <p>${esc(filme.sinopse) || "Sem sinopse disponível."}</p>
            </div>
        </article>`;
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

// --- Navegação (router) --------------------------------------------------------

let navegacaoAtual = 0;

async function navegar() {
    const numero = ++navegacaoAtual;
    const ehAtual = () => numero === navegacaoAtual;

    // "#/pesquisa?titulo=Dune" -> caminho "/pesquisa", query "titulo=Dune"
    const [caminho, query = ""] = (location.hash.slice(1) || "/").split("?");
    window.scrollTo(0, 0);
    mostrarMensagem("A carregar…");

    try {
        if (caminho === "/") {
            ecraInicio();
        } else if (caminho === "/pesquisa") {
            await ecraPesquisa(new URLSearchParams(query), ehAtual);
        } else if (/^\/filme\/\d+$/.test(caminho)) {
            await ecraFilme(Number(caminho.split("/")[2]), ehAtual);
        } else if (caminho === "/sobre") {
            await ecraSobre(ehAtual);
        } else {
            conteudo.innerHTML = `<p class="estado">Página não encontrada. <a href="#/">Voltar ao início</a></p>`;
        }
    } catch (erro) {
        if (ehAtual()) mostrarMensagem(erro.message, "erro");
    }
}

// --- Eventos -------------------------------------------------------------------

formPesquisa.addEventListener("submit", (evento) => {
    evento.preventDefault(); // impede o <form> de recarregar a página
    const titulo = campoPesquisa.value.trim();
    if (titulo) location.hash = `#/pesquisa?${new URLSearchParams({ titulo, pagina: 1 })}`;
});

// Um só "ouvinte" para os botões desenhados dinamicamente (delegação de eventos).
conteudo.addEventListener("click", (evento) => {
    if (evento.target.closest("[data-acao=voltar]")) {
        if (history.length > 1) history.back();
        else location.hash = "#/";
    }
});

window.addEventListener("hashchange", navegar);
navegar();
