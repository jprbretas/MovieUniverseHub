"""Script de exploração da API da TMDB (usado no início do projeto).

Faz as duas chamadas de que a aplicação vai precisar e mostra o resultado:
  1. GET /search/movie?query=...  -> lista de filmes que correspondem ao título
  2. GET /movie/{id}              -> detalhe de um filme

Também guarda o JSON completo de cada resposta em tests/fixtures/tmdb/, para o
podermos abrir no VS Code e, mais tarde, usar como dados nos testes (sem internet).

Uso (na raiz do projeto, com o .venv ativo):
    python scripts/explorar_tmdb.py                     # pesquisa "Matrix"
    python scripts/explorar_tmdb.py "Inception"         # outra pesquisa
    python scripts/explorar_tmdb.py "Matrix" --id 603   # escolhe o filme do detalhe
    python scripts/explorar_tmdb.py "Matrix" --lingua en-US

O token é lido do .env (via config.py) e NUNCA é mostrado.
"""
import argparse
import json
import sys
from pathlib import Path

import httpx2

from movieuniverse.config import RAIZ_PROJETO, get_settings

URL_BASE = "https://api.themoviedb.org/3"
URL_IMAGENS = "https://image.tmdb.org/t/p/w500"  # w500 = largura de 500 px
PASTA_FIXTURES = RAIZ_PROJETO / "tests" / "fixtures" / "tmdb"


def criar_cliente(token: str) -> httpx2.Client:
    """Cliente HTTP já configurado (≈ HttpClient com BaseAddress e DefaultRequestHeaders)."""
    return httpx2.Client(
        base_url=URL_BASE,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=10.0,
    )


def guardar_json(dados: dict, nome_ficheiro: str) -> Path:
    PASTA_FIXTURES.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_FIXTURES / nome_ficheiro
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


def formatar_nota(media: float, votos: int) -> str:
    return "sem votos" if votos == 0 else f"{media:.1f} · {votos} votos"


def explorar(cliente: httpx2.Client, titulo: str, tmdb_id: int | None, lingua: str) -> None:
    # 1) Pesquisa por título -------------------------------------------------
    resposta = cliente.get("/search/movie", params={"query": titulo, "language": lingua})
    resposta.raise_for_status()  # lança exceção se o status for 4xx/5xx
    pesquisa = resposta.json()   # ≈ JsonSerializer.Deserialize<Dictionary<...>>
    caminho = guardar_json(pesquisa, f"pesquisa_{titulo.lower().replace(' ', '_')}.json")

    filmes = pesquisa["results"]
    print(f'\n=== PESQUISA "{titulo}" ({lingua}) ===')
    print(f"{pesquisa['total_results']} resultados, página {pesquisa['page']} de {pesquisa['total_pages']}")
    print(f"JSON completo: {caminho.relative_to(RAIZ_PROJETO)}\n")
    print(f"{'id':>8}  {'ano':4}  {'nota':22}  {'poster':6}  título")
    for f in filmes[:10]:
        ano = (f.get("release_date") or "")[:4] or "????"
        poster = "sim" if f.get("poster_path") else "NÃO"
        nota = formatar_nota(f["vote_average"], f["vote_count"])
        print(f"{f['id']:>8}  {ano:4}  {nota:22}  {poster:6}  {f['title']}")

    if not filmes and tmdb_id is None:
        print("\nNenhum resultado; nada para mostrar no detalhe.")
        return

    # 2) Detalhe de um filme -------------------------------------------------
    tmdb_id = tmdb_id or filmes[0]["id"]
    resposta = cliente.get(f"/movie/{tmdb_id}", params={"language": lingua})
    resposta.raise_for_status()
    filme = resposta.json()
    caminho = guardar_json(filme, f"filme_{tmdb_id}.json")

    generos = ", ".join(g["name"] for g in filme["genres"]) or "(sem géneros)"
    poster = f"{URL_IMAGENS}{filme['poster_path']}" if filme.get("poster_path") else "(sem poster)"
    sinopse = filme.get("overview") or "(sinopse vazia nesta língua)"

    print(f"\n=== DETALHE /movie/{tmdb_id} ===")
    print(f"JSON completo: {caminho.relative_to(RAIZ_PROJETO)}\n")
    print(f"Título:    {filme['title']}  (original: {filme['original_title']})")
    print(f"Estreia:   {filme.get('release_date') or '(desconhecida)'}")
    print(f"Duração:   {filme.get('runtime') or '?'} min")
    print(f"Géneros:   {generos}")
    print(f"Nota TMDB: {formatar_nota(filme['vote_average'], filme['vote_count'])}")
    print(f"Poster:    {poster}")
    print(f"Sinopse:   {sinopse[:300]}{'…' if len(sinopse) > 300 else ''}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Explora a API da TMDB.")
    parser.add_argument("titulo", nargs="?", default="Matrix", help="título a pesquisar")
    parser.add_argument("--id", type=int, help="tmdb_id do filme para o detalhe (por omissão: 1.º resultado)")
    parser.add_argument("--lingua", default="pt-PT", help="língua das respostas (ex.: pt-PT, pt-BR, en-US)")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.tmdb_configurada:
        print("Falta o TMDB_API_TOKEN no .env (ver .env.example).")
        return 1

    try:
        with criar_cliente(settings.tmdb_api_token.get_secret_value()) as cliente:
            explorar(cliente, args.titulo, args.id, args.lingua)
    except httpx2.HTTPStatusError as erro:
        codigo = erro.response.status_code
        if codigo == 401:
            print("401: a TMDB recusou o token. Confirma no .env que é o 'API Read Access Token'.")
        elif codigo == 404:
            print("404: esse tmdb_id não existe.")
        elif codigo == 429:
            print("429: demasiados pedidos seguidos. Espera uns segundos e tenta de novo.")
        else:
            print(f"Erro HTTP {codigo}: {erro.response.text[:200]}")
        return 1
    except httpx2.RequestError as erro:
        print(f"Sem ligação à TMDB: {erro}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
