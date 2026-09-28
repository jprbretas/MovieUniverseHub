// Avisos curtos no canto do ecrã e a caixa de confirmação (substituem o alert() e o confirm()).

const zona = document.getElementById("avisos");
const dialogo = document.getElementById("dialogo");

export function avisar(texto, tipo = "ok") {
    const aviso = document.createElement("div");
    aviso.className = `aviso ${tipo}`;
    aviso.textContent = texto;
    zona.append(aviso);
    setTimeout(() => {
        aviso.classList.add("a-sair");
        setTimeout(() => aviso.remove(), 300);
    }, tipo === "erro" ? 5000 : 3000);
}

/** Mostra a pergunta e resolve com true se o utilizador confirmar (Escape ou Cancelar = false). */
export function confirmar(pergunta, textoBotao = "Confirmar") {
    document.getElementById("dialogo-texto").textContent = pergunta;
    document.getElementById("dialogo-confirmar").textContent = textoBotao;
    dialogo.returnValue = "";
    dialogo.showModal();
    return new Promise((resolver) => {
        dialogo.addEventListener("close", () => resolver(dialogo.returnValue === "sim"), { once: true });
    });
}
