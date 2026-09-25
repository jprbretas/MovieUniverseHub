// A estrela ★ dos cards e da ficha: abre um pequeno menu para pôr o filme nas playlists
// do utilizador (ou tirá-lo), e para criar uma playlist nova ali mesmo.
//   ☆ vazia -> o filme não está em nenhuma das minhas playlists
//   ★ cheia -> está em pelo menos uma

import { api } from "./api.js";
import { atualizarPlaylist, playlistsCom, sessao } from "./sessao.js";
import { esc } from "./util.js";

const menu = document.getElementById("menu-estrela");
let filmeDoMenu = null; // tmdb_id do filme cujo menu está aberto

export function htmlEstrela(tmdbId) {
    const ativa = playlistsCom(tmdbId).length > 0;
    return `<button type="button" class="estrela ${ativa ? "ativa" : ""}" data-tmdb="${tmdbId}"
                title="Guardar nas playlists" aria-label="Guardar nas playlists">${ativa ? "★" : "☆"}</button>`;
}

/** Atualiza todas as estrelas deste filme que estão no ecrã. */
function atualizarEstrelas(tmdbId) {
    const ativa = playlistsCom(tmdbId).length > 0;
    document.querySelectorAll(`.estrela[data-tmdb="${tmdbId}"]`).forEach((botao) => {
        botao.classList.toggle("ativa", ativa);
        botao.textContent = ativa ? "★" : "☆";
    });
}

export function abrirMenu(botao) {
    filmeDoMenu = Number(botao.dataset.tmdb);
    desenharMenu();

    // Posiciona o menu por baixo da estrela, sem sair do ecrã.
    const r = botao.getBoundingClientRect();
    const largura = 260;
    const esquerda = Math.min(r.right - largura, document.documentElement.clientWidth - largura - 8);
    menu.style.top = `${r.bottom + window.scrollY + 6}px`;
    menu.style.left = `${Math.max(8, esquerda) + window.scrollX}px`;
    menu.hidden = false;
}

export function fecharMenu() {
    menu.hidden = true;
    filmeDoMenu = null;
}

function desenharMenu() {
    const linhas = sessao.playlists.map((p) => `
        <label class="menu-linha">
            <input type="checkbox" data-playlist="${p.id}" ${p.tmdb_ids.includes(filmeDoMenu) ? "checked" : ""}>
            ${esc(p.nome)}
        </label>`).join("");

    menu.innerHTML = `
        <p class="menu-titulo">Guardar nas playlists</p>
        ${linhas || `<p class="menu-vazio">Ainda não tens playlists.</p>`}
        <form class="menu-nova">
            <input name="nome" placeholder="Nova playlist…" maxlength="100" required aria-label="Nome da nova playlist">
            <button type="submit">Criar</button>
        </form>
        <p class="menu-erro" hidden></p>`;
}

function mostrarErro(mensagem) {
    const paragrafo = menu.querySelector(".menu-erro");
    paragrafo.textContent = mensagem;
    paragrafo.hidden = false;
}

// Marcar/desmarcar uma playlist -> PUT ou DELETE na API.
menu.addEventListener("change", async (evento) => {
    const caixa = evento.target.closest("input[type=checkbox]");
    if (!caixa) return;
    const playlistId = Number(caixa.dataset.playlist);
    const tmdbId = filmeDoMenu;

    caixa.disabled = true;
    try {
        const resumo = caixa.checked
            ? await api.adicionarFilme(playlistId, tmdbId)
            : await api.removerFilme(playlistId, tmdbId);
        atualizarPlaylist(resumo);
        atualizarEstrelas(tmdbId);
    } catch (erro) {
        caixa.checked = !caixa.checked; // desfaz a marcação que falhou
        mostrarErro(erro.message);
    } finally {
        caixa.disabled = false;
    }
});

// "Nova playlist…" -> cria a playlist e já põe o filme lá dentro.
menu.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const nome = evento.target.nome.value.trim();
    const tmdbId = filmeDoMenu;
    if (!nome) return;
    try {
        const nova = await api.criarPlaylist(sessao.utilizador.id, nome);
        atualizarPlaylist(await api.adicionarFilme(nova.id, tmdbId));
        atualizarEstrelas(tmdbId);
        desenharMenu();
    } catch (erro) {
        mostrarErro(erro.message);
    }
});

// Fecha o menu ao clicar fora dele ou ao carregar em Escape.
document.addEventListener("click", (evento) => {
    if (!menu.hidden && !menu.contains(evento.target) && !evento.target.closest(".estrela")) fecharMenu();
});
document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") fecharMenu();
});
