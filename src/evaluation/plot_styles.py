# -*- coding: utf-8 -*-
"""Utilitário de estilização gráfica para publicações IEEE Transactions em Matplotlib.

Configura tipografia, dimensões, tamanhos de fonte, estilos de linha e paletas de cores
para conformidade estrita com os padrões editoriais do IEEE para figuras de coluna única
(3.5 polegadas / single-column) e coluna dupla (7.16 polegadas / double-column),
garantindo incorporação vetorial de fontes TrueType (Type 42) aceitas pelo IEEE Xplore.
"""

# %% [1. Importações e Configuração de Logging]
import logging
from typing import Dict, Tuple

import matplotlib as mpl

# Configuração de logger específico para o módulo de estilos
logger = logging.getLogger(__name__)

# %% [2. Constantes de Dimensões IEEE Transactions]
# Larguras de referência oficiais da folha de estilo IEEEtran (em polegadas)
IEEE_SINGLE_COL_WIDTH_INCHES: float = 3.50  # Largura para figura em 1 coluna (3.50 in)
IEEE_DOUBLE_COL_WIDTH_INCHES: float = 7.16  # Largura para figura em 2 colunas (7.16 in)

# %% [3. Paleta de Cores e Estilos de Linha (Okabe-Ito, segura para daltonismo)]
OKABE_ITO: Dict[str, str] = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermilion": "#D55E00",
    "reddish_purple": "#CC79A7",
}

OPT_ITAE = "Optimal ITAE ($M_s \\leq 1.6$)"
OPT_ITAE_2DOF = "2-DOF Optimal ITAE"

# Canonical controller names of the IC-T04 benchmark campaign
BENCHMARK_CONTROLLERS: Tuple[str, ...] = (
    "Ziegler-Nichols",
    "Cohen-Coon",
    "Tyreus-Luyben",
    "AMIGO",
    "2-DOF AMIGO",
    "Skogestad SIMC",
    OPT_ITAE,
    OPT_ITAE_2DOF,
    "NMPC-Oracle",
    "NMPC-MHE",
)

_STYLE: Dict[str, Tuple[str, str, str]] = {
    # name: (Okabe-Ito color, linestyle, marker)
    "Ziegler-Nichols": (OKABE_ITO["vermilion"], "--", "x"),
    "Cohen-Coon": (OKABE_ITO["reddish_purple"], "-.", "^"),
    "Tyreus-Luyben": (OKABE_ITO["orange"], ":", "v"),
    "AMIGO": (OKABE_ITO["sky_blue"], "-", "D"),
    "2-DOF AMIGO": (OKABE_ITO["sky_blue"], "--", "d"),
    "Skogestad SIMC": (OKABE_ITO["bluish_green"], "-", "s"),
    OPT_ITAE: (OKABE_ITO["blue"], "-", "o"),
    OPT_ITAE_2DOF: (OKABE_ITO["blue"], "--", "P"),
    "NMPC-Oracle": (OKABE_ITO["black"], "-", "*"),
    "NMPC-MHE": (OKABE_ITO["black"], "--", "h"),
}
# Legacy aliases still used by older figure scripts
for _alias in ("Optimal ITAE (Ms<=1.6)", "Optimal ITAE ($M_s \\le 1.6$)", "Optimal ITAE"):
    _STYLE[_alias] = _STYLE[OPT_ITAE]

IEEE_PALETTE: Dict[str, str] = {k: v[0] for k, v in _STYLE.items()}
IEEE_PALETTE.update({"Setpoint": "#555555", "Constraint": "#999999", "Pareto": "#252525"})
IEEE_LINESTYLES: Dict[str, str] = {k: v[1] for k, v in _STYLE.items()}
IEEE_LINESTYLES.update({"Setpoint": ":", "Constraint": "-."})
IEEE_MARKERS: Dict[str, str] = {k: v[2] for k, v in _STYLE.items()}

# %% [4. Configuração Global de rcParams do Matplotlib]
def setup_ieee_style(single_column: bool = False) -> None:
    """Configura os parâmetros globais do Matplotlib (rcParams) no padrão IEEE Transactions.

    Garante que:
    1. As fontes sejam embutidas como TrueType Tipo 42 (obrigatório para IEEE Xplore).
    2. A tipografia utilize famílias serifadas (Times New Roman / Computer Modern).
    3. As fontes mantenham legibilidade estrita nas dimensões finais impressas.
    4. As grades sejam sutis e não obstruam as curvas de resposta temporal.

    Args:
        single_column: Se True, reduz ligeiramente o tamanho das fontes para caber
                       em figuras compactas de 3.5 polegadas sem truncamento.
    """
    logger.info(
        "Aplicando estilo de publicação IEEE Transactions (single_column=%s)", single_column
    )

    # Definição de hierarquia tipográfica proporcional à largura da figura
    base_font_size = 8.0 if single_column else 8.5
    label_font_size = 8.5 if single_column else 9.0
    title_font_size = 9.0 if single_column else 9.5

    mpl.rcParams.update(get_tueplots_rcparams())
    params = {
        # Backend e embutimento vetorial de fontes compatível com IEEE Xplore
        "pdf.fonttype": 42,
        "ps.fonttype": 42,

        # Família serifada idêntica à do LaTeX do artigo
        "font.family": "serif",
        "font.serif": [
            "Times New Roman",
            "Times",
            "DejaVu Serif",
            "Computer Modern Roman",
            "serif",
        ],
        "font.size": base_font_size,

        # Títulos e rótulos de eixos
        "axes.titlesize": title_font_size,
        "axes.labelsize": label_font_size,
        "axes.titleweight": "bold",
        "axes.labelweight": "normal",
        "axes.linewidth": 0.8,

        # Marcações de eixos (Ticks) apontando para dentro
        "xtick.labelsize": base_font_size,
        "ytick.labelsize": base_font_size,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.minor.size": 1.5,
        "ytick.minor.size": 1.5,
        "xtick.top": True,
        "ytick.right": True,

        # Caixas de legenda discretas e translúcidas
        "legend.fontsize": base_font_size - 0.5,
        "legend.frameon": True,
        "legend.framealpha": 0.92,
        "legend.edgecolor": "#CCCCCC",
        "legend.fancybox": False,

        # Linhas de grade sutis para facilitar a leitura de valores
        "grid.linestyle": ":",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.6,
        "grid.color": "#AAAAAA",

        # Espessura de traço e resolução de exportação (300 DPI mínimo editorial)
        "lines.linewidth": 1.2,
        "lines.markersize": 5.0,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
    }

    mpl.rcParams.update(params)

# %% [5. Cálculo Didático de Dimensões de Figuras]
def get_figure_dimensions(
    columns: int = 1,
    aspect_ratio: float = 0.75,
    height_override: float = 0.0,
) -> Tuple[float, float]:
    """Calcula dimensões exatas (largura e altura em polegadas) para o layout IEEEtran.

    Passo a passo didático:
    1. Identifica se a figura ocupará 1 coluna (3.5 in) ou 2 colunas (7.16 in).
    2. Se uma altura explícita for informada via height_override, utiliza-a diretamente.
    3. Caso contrário, multiplica a largura pela razão de aspecto (padrão 4:3 -> 0.75).

    Args:
        columns: 1 para coluna simples (3.50 in) ou 2 para coluna dupla (7.16 in).
        aspect_ratio: Razão altura/largura (padrão 0.75 para proporção áurea/4:3).
        height_override: Se > 0.0, força altura fixa em polegadas.

    Returns:
        Tupla com (largura_em_polegadas, altura_em_polegadas).
    """
    width = IEEE_SINGLE_COL_WIDTH_INCHES if columns == 1 else IEEE_DOUBLE_COL_WIDTH_INCHES
    height = height_override if height_override > 0.0 else width * aspect_ratio
    return (float(width), float(height))


# %% [6. Integração com tueplots e Anti-Colisão de Rótulos via adjustText]
def get_tueplots_rcparams() -> dict:
    """Axes, line-width, grid and tick settings from `tueplots.axes` (vector-safe fonts).

    tueplots ships no IEEE/Springer figure-size bundle, so sizes come from
    `get_figure_dimensions`; only the typographic/axes conventions are taken from tueplots.

    Returns:
        Dictionary compatible with `mpl.rcParams.update()`.
    """
    from tueplots import axes

    cfg: dict = {}
    cfg.update(axes.lines())
    cfg.update(axes.grid())
    cfg.update(axes.tick_direction(x="in", y="in"))
    cfg.update({"pdf.fonttype": 42, "ps.fonttype": 42, "text.usetex": False})
    return cfg


def apply_repulsive_annotations(
    ax,
    points_and_labels: list[tuple[float, float, str]],
    fontsize: float = 7.2,
    color: str = "#222222",
) -> list:
    """Posiciona anotações de texto com repulsão automática sem colisão via `adjustText`.

    Args:
        ax: Eixo Matplotlib (`matplotlib.axes.Axes`) onde os rótulos serão inseridos.
        points_and_labels: Lista de tuplas `(x, y, texto)`.
        fontsize: Tamanho da fonte em pontos (mínimo recomendado 7.0 pt).
        color: Cor hexadecimal do texto.

    Returns:
        Lista de objetos `matplotlib.text.Text` ajustados sem sobreposição.
    """
    from adjustText import adjust_text

    texts = [
        ax.text(float(x), float(y), str(label), fontsize=fontsize, color=color)
        for x, y, label in points_and_labels
    ]
    if texts:
        adjust_text(
            texts,
            ax=ax,
            arrowprops={"arrowstyle": "-", "color": "#666666", "lw": 0.6},
            expand=(1.2, 1.2),
        )
    return texts

