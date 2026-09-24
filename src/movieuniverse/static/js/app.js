// Frontend: por agora só pergunta ao backend se está tudo bem.
// fetch() faz um pedido HTTP ao nosso próprio servidor (≈ HttpClient.GetAsync em C#).

async function verificarEstado() {
    const estadoApi = document.getElementById("estado-api");
    const estadoTmdb = document.getElementById("estado-tmdb");

    try {
        const resposta = await fetch("/api/health");
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const dados = await resposta.json();

        estadoApi.textContent = "online";
        estadoApi.className = "ok";

        estadoTmdb.textContent = dados.tmdb_configurada ? "configurado" : "em falta (ver .env)";
        estadoTmdb.className = dados.tmdb_configurada ? "ok" : "erro";
    } catch (erro) {
        estadoApi.textContent = `sem resposta (${erro.message})`;
        estadoApi.className = "erro";
        estadoTmdb.textContent = "desconhecido";
    }
}

verificarEstado();
