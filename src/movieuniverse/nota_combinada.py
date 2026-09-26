"""Nota combinada: junta a nota da TMDB e as notas dos utilizadores da aplicação.

Função PURA: recebe médias e números de votos e devolve a nota e uma explicação.
Não depende da interface, da base de dados nem da rede, por isso é fácil de testar e de
reutilizar (a comparação de playlists e o jogo usam esta mesma função).

A regra (ver DECISIONS.md, secção "Nota combinada") é uma MÉDIA BAYESIANA:

                     v × R  +  m × C
    nota combinada = ───────────────
                         v  +  m

    v = votos reais (TMDB + utilizadores da app)
    R = média ponderada dos votos reais
    m = VOTOS_IMAGINARIOS: quantos votos são precisos para confiar numa média
    C = NOTA_NEUTRA: a nota que assumimos quando ainda não sabemos nada

Com poucos votos, os m votos "imaginários" dominam e a nota fica perto de C.
Com muitos votos, quase não pesam e a nota fica perto da média real.
"""
from pydantic import BaseModel, Field, computed_field

# Com 100 votos, a margem de erro típica de uma média já é de cerca de ±0,2
# (desvio-padrão das notas ~1,8 / √100). Ver DECISIONS.md.
VOTOS_IMAGINARIOS = 100

# Uma nota "mediana", ligeiramente acima do meio da escala: é para onde puxamos um filme
# sobre o qual ainda há pouca informação.
NOTA_NEUTRA = 6.5


def _pt(valor: float, casas: int = 1) -> str:
    """8.374 -> "8,4" (vírgula decimal, como em português)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _percentagem(fracao: float) -> str:
    """0.13 -> "13%"; perto dos extremos usa uma casa decimal: 0.9967 -> "99,7%"."""
    casas = 1 if fracao < 0.01 or fracao > 0.99 else 0
    return f"{_pt(fracao * 100, casas)}%"


def _milhares(numero: int) -> str:
    """30000 -> "30 000"."""
    return f"{numero:,}".replace(",", " ")


class NotaCombinada(BaseModel):
    """O resultado do cálculo (≈ um record imutável em C#)."""

    model_config = {"frozen": True}

    valor: float | None = Field(description="Nota de 0 a 10; null se não houver votos nenhuns")
    num_votos: int = Field(description="Votos reais em que se baseia (TMDB + utilizadores)")
    votos_tmdb: int
    votos_app: int
    peso_media_real: float = Field(description="Quanto a média real pesa no resultado (0 a 1)")
    explicacao: str

    @computed_field
    @property
    def texto(self) -> str:
        """Pronto a mostrar: "8,4 · 30 003 votos" ou "informação insuficiente"."""
        if self.valor is None:
            return "informação insuficiente"
        palavra = "voto" if self.num_votos == 1 else "votos"
        return f"{_pt(self.valor)} · {_milhares(self.num_votos)} {palavra}"


def calcular_nota_combinada(
    media_tmdb: float,
    votos_tmdb: int,
    media_app: float | None,
    votos_app: int,
    votos_imaginarios: int = VOTOS_IMAGINARIOS,
    nota_neutra: float = NOTA_NEUTRA,
) -> NotaCombinada:
    """Calcula a nota combinada de um filme.

    media_tmdb / votos_tmdb: a média (0 a 10) e o número de votos da TMDB
    media_app / votos_app:   a média (1 a 10) e o número de notas dos utilizadores da app
                             (media_app é ignorada se votos_app for 0)
    """
    if votos_tmdb < 0 or votos_app < 0:
        raise ValueError("O número de votos não pode ser negativo.")
    if not 0 <= media_tmdb <= 10 or (votos_app and not 0 <= (media_app or 0) <= 10):
        raise ValueError("As médias têm de estar entre 0 e 10.")

    total = votos_tmdb + votos_app
    if total == 0:
        return NotaCombinada(
            valor=None,
            num_votos=0,
            votos_tmdb=0,
            votos_app=0,
            peso_media_real=0.0,
            explicacao=(
                "Informação insuficiente: o filme não tem votos na TMDB nem notas de "
                "utilizadores da aplicação, por isso não tem nota combinada."
            ),
        )

    # Média real: cada voto conta o mesmo, venha da TMDB ou da aplicação.
    soma_app = (media_app or 0) * votos_app
    media_real = (media_tmdb * votos_tmdb + soma_app) / total

    peso = total / (total + votos_imaginarios)
    valor = peso * media_real + (1 - peso) * nota_neutra  # = (v·R + m·C) / (v + m)

    partes = [f"{_milhares(votos_tmdb)} da TMDB (média {_pt(media_tmdb)})"]
    if votos_app:
        partes.append(f"{votos_app} de utilizadores da aplicação (média {_pt(media_app)})")
    explicacao = (
        f"Baseada em {_milhares(total)} votos: {' e '.join(partes)}. "
        f"A média real ({_pt(media_real, 2)}) pesa {_percentagem(peso)} e a nota neutra "
        f"({_pt(nota_neutra)}) pesa {_percentagem(1 - peso)}, porque {votos_imaginarios} votos 'imaginários' com a nota neutra "
        f"representam o que ainda não sabemos sobre o filme."
    )

    return NotaCombinada(
        valor=round(valor, 2),
        num_votos=total,
        votos_tmdb=votos_tmdb,
        votos_app=votos_app,
        peso_media_real=round(peso, 4),
        explicacao=explicacao,
    )
