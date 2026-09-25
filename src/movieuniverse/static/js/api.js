// Chamadas à nossa API REST (≈ um serviço com HttpClient num projeto Blazor).
// Todas devolvem uma Promise (≈ Task em C#): quem chama usa `await`.

async function pedirJSON(url, { method = "GET", corpo } = {}) {
    const opcoes = { method };
    if (corpo !== undefined) {
        opcoes.headers = { "Content-Type": "application/json" };
        opcoes.body = JSON.stringify(corpo);
    }

    let resposta;
    try {
        resposta = await fetch(url, opcoes);
    } catch {
        throw new Error("Não foi possível contactar o servidor. A aplicação está a correr?");
    }

    if (resposta.status === 204) return null; // "No Content": sucesso sem corpo (ex.: DELETE)

    const dados = await resposta.json().catch(() => null);
    if (!resposta.ok) {
        // A nossa API devolve {"detail": "mensagem"} nos erros 404/500/503.
        // No 422 (validação) o "detail" é uma lista técnica; mostramos uma frase simples.
        const mensagem = typeof dados?.detail === "string" ? dados.detail : "Pedido inválido.";
        const erro = new Error(mensagem);
        erro.status = resposta.status; // para quem chama poder distinguir, por ex., um 404
        throw erro;
    }
    return dados;
}

export const api = {
    // Filmes
    pesquisar: (titulo, pagina = 1) =>
        pedirJSON(`/api/filmes?${new URLSearchParams({ titulo, pagina })}`),
    filme: (tmdbId) => pedirJSON(`/api/filmes/${tmdbId}`),
    notasDoFilme: (tmdbId) => pedirJSON(`/api/filmes/${tmdbId}/notas`),

    // Utilizadores
    entrar: (nome) => pedirJSON("/api/utilizadores", { method: "POST", corpo: { nome } }),
    playlistsDe: (utilizadorId) => pedirJSON(`/api/utilizadores/${utilizadorId}/playlists`),
    criarPlaylist: (utilizadorId, nome) =>
        pedirJSON(`/api/utilizadores/${utilizadorId}/playlists`, { method: "POST", corpo: { nome } }),
    darNota: (utilizadorId, tmdbId, estrelas) =>
        pedirJSON(`/api/utilizadores/${utilizadorId}/notas/${tmdbId}`, { method: "PUT", corpo: { estrelas } }),
    retirarNota: (utilizadorId, tmdbId) =>
        pedirJSON(`/api/utilizadores/${utilizadorId}/notas/${tmdbId}`, { method: "DELETE" }),

    // Playlists
    playlist: (playlistId) => pedirJSON(`/api/playlists/${playlistId}`),
    apagarPlaylist: (playlistId) => pedirJSON(`/api/playlists/${playlistId}`, { method: "DELETE" }),
    adicionarFilme: (playlistId, tmdbId) =>
        pedirJSON(`/api/playlists/${playlistId}/filmes/${tmdbId}`, { method: "PUT" }),
    removerFilme: (playlistId, tmdbId) =>
        pedirJSON(`/api/playlists/${playlistId}/filmes/${tmdbId}`, { method: "DELETE" }),

    // Sistema
    estado: () => pedirJSON("/api/health"),
};
