// Pequenas funções usadas por vários ecrãs.

/**
 * Escapa texto antes de o pôr dentro de HTML (≈ o que o Razor faz sozinho com @variavel).
 * Sem isto, um título vindo da TMDB com "<script>" seria executado no navegador (XSS).
 * Regra: TODO o texto que vem da API passa por esc() antes de entrar no innerHTML.
 */
export function esc(texto) {
    const trocas = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(texto ?? "").replace(/[&<>"']/g, (c) => trocas[c]);
}

export function formatarDuracao(minutos) {
    if (!minutos) return "duração desconhecida";
    const horas = Math.floor(minutos / 60);
    const resto = minutos % 60;
    return horas ? `${horas} h ${String(resto).padStart(2, "0")} min` : `${resto} min`;
}

/** 7.666 -> "7,7" (formato português; uma casa decimal por omissão). */
export function formatarMedia(valor, casas = 1) {
    return valor.toLocaleString("pt-PT", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function formatarData(textoIso) {
    return new Date(textoIso).toLocaleDateString("pt-PT");
}

/** Compara nomes de utilizador sem distinguir maiúsculas (como a base de dados faz). */
export function mesmoNome(a, b) {
    return String(a).toLowerCase() === String(b).toLowerCase();
}

export function htmlPoster(filme, classe = "poster") {
    return filme.poster_url
        ? `<img class="${classe}" src="${esc(filme.poster_url)}" alt="Cartaz de ${esc(filme.titulo)}" loading="lazy">`
        : `<div class="${classe} sem-cartaz">sem cartaz</div>`;
}
