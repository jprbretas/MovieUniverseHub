// Pequenas funções usadas por vários ecrãs.

/**
 * Escapa texto antes de o pôr dentro de HTML, para evitar XSS: todo o texto que vem da API
 * passa por esc() antes de entrar no innerHTML.
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

/**
 * O cartaz do filme, ou um "cartaz" só com o título quando a TMDB não tem imagem.
 * `decorativo`: sem texto alternativo, para quando o título já aparece ao lado (ex.: nos cards).
 */
export function htmlPoster(filme, classe = "poster", { decorativo = false } = {}) {
    const alt = decorativo ? "" : `Cartaz de ${esc(filme.titulo)}`;
    return filme.poster_url
        ? `<img class="${classe}" src="${esc(filme.poster_url)}" alt="${alt}" data-titulo="${esc(filme.titulo)}" loading="lazy">`
        : htmlSemCartaz(filme.titulo, classe);
}

export function htmlSemCartaz(titulo, classe = "poster", aviso = "sem cartaz") {
    return `<div class="${classe} sem-cartaz"><span class="sem-cartaz-aviso">${esc(aviso)}</span><span>${esc(titulo)}</span></div>`;
}

/** Círculo com a inicial do nome; a cor depende do nome, por isso é sempre a mesma para cada pessoa. */
export function htmlAvatar(nome, classe = "") {
    const cores = ["var(--roxo)", "var(--ciano)", "var(--ok)", "var(--ambar)"];
    const texto = String(nome).trim().toLowerCase();
    const soma = [...texto].reduce((total, letra) => total + letra.codePointAt(0), 0);
    const inicial = [...texto][0] ?? "?";
    return `<span class="avatar ${classe}" style="--cor: ${cores[soma % cores.length]}" aria-hidden="true">${esc(inicial)}</span>`;
}

/** "3 filmes" / "1 filme" */
export function contar(numero, singular, plural = `${singular}s`) {
    return `${numero} ${numero === 1 ? singular : plural}`;
}
