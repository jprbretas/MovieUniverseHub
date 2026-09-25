// Chamadas à nossa API REST (≈ um serviço com HttpClient num projeto Blazor).
// Todas devolvem uma Promise (≈ Task em C#): quem chama usa `await`.

async function pedirJSON(url) {
    let resposta;
    try {
        resposta = await fetch(url);
    } catch {
        throw new Error("Não foi possível contactar o servidor. A aplicação está a correr?");
    }

    const dados = await resposta.json().catch(() => null);
    if (!resposta.ok) {
        // A nossa API devolve {"detail": "mensagem"} nos erros 404/500/503.
        // No 422 (validação) o "detail" é uma lista técnica; mostramos uma frase simples.
        const mensagem = typeof dados?.detail === "string" ? dados.detail : "Pedido inválido.";
        throw new Error(mensagem);
    }
    return dados;
}

export const api = {
    pesquisar: (titulo, pagina = 1) =>
        pedirJSON(`/api/filmes?${new URLSearchParams({ titulo, pagina })}`),
    filme: (tmdbId) => pedirJSON(`/api/filmes/${tmdbId}`),
    estado: () => pedirJSON("/api/health"),
};
