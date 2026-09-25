// Quem está a usar a aplicação (o utilizador que "entrou") e as playlists dele.
//
// Não há palavra-passe (ver DECISIONS.md): entrar é dizer o nome. O navegador guarda o
// utilizador no localStorage para não ter de voltar a entrar ao recarregar a página
// (≈ guardar algo no ProtectedLocalStorage/sessionStorage no Blazor).

import { api } from "./api.js";

const CHAVE = "movieuniverse.utilizador";

export const sessao = {
    utilizador: null, // { id, nome } ou null
    playlists: [],    // playlists do utilizador: [{ id, nome, dono, tmdb_ids, criada_em }]
};

// Quem quiser saber quando alguém entra ou sai regista aqui uma função (≈ um evento C#).
const ouvintes = [];
export function aoMudarSessao(funcao) {
    ouvintes.push(funcao);
}
function avisar() {
    ouvintes.forEach((funcao) => funcao());
}

// O localStorage pode falhar (ex.: navegação privada); nesse caso só não fica guardado.
function lerGuardado() {
    try {
        return JSON.parse(localStorage.getItem(CHAVE));
    } catch {
        return null;
    }
}
function guardar(utilizador) {
    try {
        if (utilizador) localStorage.setItem(CHAVE, JSON.stringify(utilizador));
        else localStorage.removeItem(CHAVE);
    } catch {
        /* ignorar */
    }
}

/** Chamada uma vez ao abrir a página: recupera quem tinha entrado da última vez. */
export async function iniciarSessao() {
    const guardado = lerGuardado();
    if (!guardado) return;
    sessao.utilizador = guardado;
    try {
        await recarregarPlaylists();
    } catch (erro) {
        // 404: o utilizador já não existe (ex.: a base de dados foi apagada) -> sair.
        if (erro.status === 404) sair({ avisarOuvintes: false });
    }
}

export async function entrar(nome) {
    sessao.utilizador = await api.entrar(nome);
    guardar(sessao.utilizador);
    await recarregarPlaylists();
    avisar();
}

export function sair({ avisarOuvintes = true } = {}) {
    sessao.utilizador = null;
    sessao.playlists = [];
    guardar(null);
    if (avisarOuvintes) avisar();
}

export async function recarregarPlaylists() {
    sessao.playlists = sessao.utilizador ? await api.playlistsDe(sessao.utilizador.id) : [];
}

/** Substitui (ou acrescenta) uma playlist na lista local depois de a API a alterar. */
export function atualizarPlaylist(resumo) {
    const indice = sessao.playlists.findIndex((p) => p.id === resumo.id);
    if (indice >= 0) sessao.playlists[indice] = resumo;
    else sessao.playlists.push(resumo);
}

/** Em quais das minhas playlists está este filme? (decide se a ★ aparece cheia) */
export function playlistsCom(tmdbId) {
    return sessao.playlists.filter((p) => p.tmdb_ids.includes(tmdbId));
}
