# -*- coding: utf-8 -*-
"""Geração da Figura 4 com estética limpa (minimalista) para o template Springer.

Correções diretas sobre a poluição visual:
1. Remoção completa do inset_axes central;
2. Realocação da nota de regras off-scale (ZN/CC) para o quadrante superior
   direito vazio (y > 3.5), eliminando a sobreposição com a curva SIMC;
3. Enxugamento da legenda do Painel (a) para 4 itens reais (2 linhas), sem
   marcadores fantasmas off-scale;
4. Tipografia sem excesso de negrito (alinhada às Figuras 5 e 6 do manuscrito)
   e redução do diâmetro dos pontos contínuos (s=20) para evitar aglutinação.
"""

from __future__ import annotations

import io
import logging
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence

PROJECT_ROOT = Path("/home/marques/Área de trabalho/2026.2/IC")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.layout_engine import ConstrainedLayoutEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("generate_fig4_springer")

# Escala 1:1 para 0.98\textwidth no layout single-column do main.pdf (~4.80 in)
# Altura otimizada para 5.40 in para caber perfeitamente na grade vertical do LaTeX
SN_JNL_TEXTWIDTH_IN: float = 4.80
FIG_HEIGHT_IN: float = 5.40


@dataclass(frozen=True)
class ParetoExperimentData:
    """Estrutura imutável e validada para os dados do Experimento 03."""

    simc_tv: np.ndarray
    simc_iae: np.ndarray
    simc_ms: np.ndarray
    simc_tau_c: np.ndarray
    opt_tv: np.ndarray
    opt_iae: np.ndarray
    discrete_points: Dict[str, Dict[str, float]]


class _IgnoredDomainStub:
    """Stub passivo para absorver objetos de domínio não usados na plotagem."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    def __setstate__(self, state: Any) -> None:
        self.state = state


class RestrictedUnpickler(pickle.Unpickler):
    """Desserializador seguro com suporte às classes de domínio de 'src.*'.

    Complexidade Algorítmica:
        - Tempo: O(1) por resolução de símbolo via frozenset.
        - Espaço: O(1).
    """

    _ALLOWED_MODULES = frozenset({
        "builtins",
        "collections",
        "numpy",
        "numpy.dtypes",
        "numpy.core.multiarray",
        "numpy.core.numeric",
        "numpy._core.multiarray",
        "numpy._core.numeric",
    })

    _FORBIDDEN_BUILTINS = frozenset({
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
    })

    _ALLOWED_PROJECT_CLASSES = frozenset({
        ("src.classical_control.pid_controller", "PIDGains"),
    })

    def find_class(self, module: str, name: str) -> Any:
        """Autoriza apenas tipos numéricos e DTOs internos do projeto."""
        if module == "builtins" and name in self._FORBIDDEN_BUILTINS:
            raise pickle.UnpicklingError(
                f"Bloqueio de segurança: builtin proibido '{module}.{name}'"
            )

        if module in self._ALLOWED_MODULES:
            return super().find_class(module, name)

        if (module, name) in self._ALLOWED_PROJECT_CLASSES or module.startswith("src."):
            try:
                return super().find_class(module, name)
            except (ImportError, AttributeError):
                return _IgnoredDomainStub

        raise pickle.UnpicklingError(
            f"Bloqueio de segurança: módulo não autorizado '{module}.{name}'"
        )


def load_experiment_cache(cache_path: Path, allowed_root: Path) -> ParetoExperimentData:
    """Carrega e valida os dados do cache experimental.

    Complexidade: O(N + M log M) em tempo; O(N + M) em espaço.
    """
    resolved_cache = cache_path.resolve()
    resolved_root = allowed_root.resolve()

    if not str(resolved_cache).startswith(str(resolved_root)):
        raise ValueError(f"Caminho fora do diretório permitido: {resolved_cache}")
    if not resolved_cache.is_file():
        raise FileNotFoundError(f"Cache não encontrado em {resolved_cache}")

    with open(resolved_cache, "rb") as f:
        raw_bytes = f.read()

    unpickled = RestrictedUnpickler(io.BytesIO(raw_bytes)).load()
    if not isinstance(unpickled, (tuple, list)) or len(unpickled) != 3:
        raise ValueError("Formato de cache inválido: esperada tupla de 3 elementos.")

    simc_results, opt_results, discrete_points = unpickled
    sorted_opt = sorted(opt_results, key=lambda item: float(item["tv"]))

    return ParetoExperimentData(
        simc_tv=np.asarray([float(r["tv"]) for r in simc_results], dtype=np.float64),
        simc_iae=np.asarray([float(r["iae"]) for r in simc_results], dtype=np.float64),
        simc_ms=np.asarray([float(r["ms"]) for r in simc_results], dtype=np.float64),
        simc_tau_c=np.asarray([float(r["tau_c"]) for r in simc_results], dtype=np.float64),
        opt_tv=np.asarray([float(r["tv"]) for r in sorted_opt], dtype=np.float64),
        opt_iae=np.asarray([float(r["iae"]) for r in sorted_opt], dtype=np.float64),
        discrete_points=discrete_points,
    )


def configure_rcparams() -> None:
    """Configura tipografia limpa e harmônica com as Figuras 5 e 6 do artigo."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Computer Modern Roman", "DejaVu Serif", "Times New Roman"],
        "mathtext.fontset": "cm",
        "font.size": 8.5,
        "axes.labelsize": 8.8,
        "axes.titlesize": 9.0,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 7.8,
        "axes.linewidth": 0.8,
        "axes.edgecolor": "#222222",
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.minor.width": 0.5,
        "ytick.minor.width": 0.5,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "grid.linewidth": 0.45,
        "grid.alpha": 0.35,
        "grid.color": "#CCCCCC",
        "lines.linewidth": 1.6,
        "lines.markersize": 5.0,
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def create_layout_engine(
    w_pad: float = 0.03,
    h_pad: float = 0.04,
    wspace: float = 0.03,
    hspace: float = 0.06,
) -> ConstrainedLayoutEngine:
    """Instancia ConstrainedLayoutEngine com validação de domínio O(1)."""
    for name, val in (("w_pad", w_pad), ("h_pad", h_pad), ("wspace", wspace), ("hspace", hspace)):
        if not isinstance(val, (int, float)) or val < 0.0 or val >= 1.0:
            raise ValueError(f"Parâmetro '{name}' fora do intervalo [0.0, 1.0): {val}")

    return ConstrainedLayoutEngine(
        w_pad=float(w_pad),
        h_pad=float(h_pad),
        wspace=float(wspace),
        hspace=float(hspace),
    )


def render_panel_a(fig: Figure, ax_a: Axes, data: ParetoExperimentData) -> None:
    """Renderiza o Painel (a) com interior desobstruído e sem sobreposições."""
    ax_a.plot(
        data.simc_tv,
        data.simc_iae,
        color="#555555",
        linestyle="-",
        linewidth=1.1,
        alpha=0.8,
        zorder=2,
    )

    # Marcadores menores (s=22) evitam o aspecto de "lagarta" densa no ramo vertical
    scatter = ax_a.scatter(
        data.simc_tv,
        data.simc_iae,
        c=data.simc_ms,
        cmap="viridis_r",
        vmin=1.1,
        vmax=2.5,
        s=22,
        zorder=3,
        edgecolor="#222222",
        linewidth=0.35,
        label=r"SIMC locus ($\tau_c \in [0.015, 2.5]$ min)",
    )

    ax_a.plot(
        data.opt_tv,
        data.opt_iae,
        color="#006D2C",
        linestyle="--",
        linewidth=1.7,
        zorder=5,
        label=r"$\lambda$-opt Pareto front",
    )

    simc_pt = data.discrete_points["Skogestad SIMC"]
    opt_key = next((k for k in data.discrete_points if "Optimal" in k), None)
    if opt_key is None:
        raise KeyError("Chave 'Optimal' não encontrada em discrete_points.")
    opt_pt = data.discrete_points[opt_key]
    zn_pt = data.discrete_points["Ziegler-Nichols"]
    cc_pt = data.discrete_points["Cohen-Coon"]

    ax_a.scatter(
        [simc_pt["tv"]],
        [simc_pt["iae"]],
        color="#1B9E77",
        marker="s",
        s=58,
        edgecolors="black",
        linewidth=0.9,
        zorder=7,
        label=f"Skogestad SIMC ($M_s = {simc_pt['ms']:.2f}$)",
    )
    ax_a.scatter(
        [opt_pt["tv"]],
        [opt_pt["iae"]],
        color="#1F78B4",
        marker="o",
        s=58,
        edgecolors="black",
        linewidth=0.9,
        zorder=7,
        label=f"Optimal ITAE ($M_s = {opt_pt['ms']:.2f}$)",
    )

    ax_a.set_title(
        r"(a) Continuous Pareto Frontier in $(\mathrm{TV}, \mathrm{IAE})$ Space",
        loc="left",
        fontweight="bold",
        pad=3.5,
    )

    # Legenda compacta de apenas 4 itens (2x2), sem itens fantasmas off-scale
    ax_a.legend(
        loc="lower center",
        bbox_to_anchor=(0.50, 1.10),
        ncol=2,
        frameon=True,
        framealpha=0.95,
        facecolor="#FFFFFF",
        edgecolor="#CCCCCC",
        markerscale=0.85,
        handletextpad=0.4,
        columnspacing=1.2,
        borderpad=0.3,
    )

    # Anotação limpa do Joelho de Pareto na região vazia central-esquerda
    ax_a.annotate(
        "Pareto Knee\n" + r"($\tau_c \in [0.25, 0.40]$ min)",
        xy=(simc_pt["tv"] + 2.0, simc_pt["iae"] + 0.08),
        xytext=(52.0, 2.35),
        ha="left",
        va="center",
        arrowprops=dict(
            facecolor="#333333",
            edgecolor="#333333",
            arrowstyle="->",
            lw=0.9,
            connectionstyle="arc3,rad=-0.12",
        ),
        fontsize=7.8,
        color="#111111",
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="#FFFFFF",
            edgecolor="#CCCCCC",
            alpha=0.92,
            lw=0.6,
        ),
        zorder=6,
    )

    # Nota off-scale posicionada no quadrante superior direito 100% VAZIO (y in [3.5, 4.9])
    # A curva SIMC passa abaixo de y = 3.0, garantindo distância vertical > 0.6 K.min
    callout_text = (
        "Off-scale Empirical Rules (Limit Cycles):\n"
        f"• Ziegler–Nichols: TV = {zn_pt['tv']:.0f} L/min, "
        f"IAE = {zn_pt['iae']:.1f} ($M_s = {zn_pt['ms']:.2f}$)\n"
        f"• Cohen–Coon: TV = {cc_pt['tv']:.0f} L/min, "
        f"IAE = {cc_pt['iae']:.1f} ($M_s = {cc_pt['ms']:.2f}$)"
    )
    ax_a.annotate(
        callout_text,
        xy=(243.0, 5.05),
        xytext=(238.0, 4.45),
        ha="right",
        va="top",
        arrowprops=dict(
            facecolor="#D95F02",
            edgecolor="#D95F02",
            arrowstyle="->",
            lw=1.0,
        ),
        fontsize=7.3,
        color="#222222",
        bbox=dict(
            boxstyle="round,pad=0.28",
            facecolor="#FFFDFB",
            edgecolor="#E0A070",
            alpha=0.94,
            lw=0.7,
        ),
        zorder=6,
    )

    ax_a.set_xlim(0.0, 248.0)
    ax_a.set_ylim(0.65, 5.35)
    ax_a.set_xlabel(r"Actuator Total Variation $\mathrm{TV}$ (L/min)")
    ax_a.set_ylabel(r"Tracking Error $\mathrm{IAE}$ ($\mathrm{K\cdot min}$)")
    ax_a.grid(True, linestyle="--")

    cbar = fig.colorbar(scatter, ax=ax_a, pad=0.015, aspect=24)
    cbar.set_label(r"Max. Sensitivity $M_s = \|S\|_\infty$", fontsize=8.2)
    cbar.ax.tick_params(labelsize=7.6, width=0.7)
    cbar.outline.set_linewidth(0.7)


def render_panel_b(ax_b: Axes, data: ParetoExperimentData) -> Axes:
    """Renderiza o Painel (b) com tipografia limpa e sem colisões."""
    color_ms = "#005A8D"
    color_iae = "#C84B00"
    simc_pt = data.discrete_points["Skogestad SIMC"]

    line_ms, = ax_b.plot(
        data.simc_tau_c,
        data.simc_ms,
        color=color_ms,
        linestyle="-",
        linewidth=1.8,
        label=r"Peak $M_s = \|S\|_\infty$",
        zorder=4,
    )
    line_rob = ax_b.axhline(
        1.6,
        color="#008856",
        linestyle="--",
        linewidth=1.2,
        label=r"Robust Limit ($M_s = 1.6$)",
        zorder=3,
    )
    line_lim = ax_b.axhline(
        2.0,
        color="#A82060",
        linestyle=":",
        linewidth=1.4,
        label=r"Marginal Limit ($M_s = 2.0$)",
        zorder=3,
    )

    ax_b.set_xscale("log")
    ax_b.set_xlabel(r"Closed-loop Tuning Parameter $\tau_c$ (min)")
    ax_b.set_ylabel(r"Maximum Sensitivity Peak $M_s$", color=color_ms)
    ax_b.tick_params(axis="y", labelcolor=color_ms, colors=color_ms)
    ax_b.spines["left"].set_color(color_ms)
    ax_b.spines["left"].set_linewidth(1.0)
    ax_b.set_ylim(0.92, 2.22)
    ax_b.set_xlim(0.013, 2.7)
    ax_b.grid(True, which="both", linestyle="--")

    line_pt = ax_b.scatter(
        [0.40],
        [simc_pt["ms"]],
        color="#1B9E77",
        marker="s",
        s=58,
        edgecolors="black",
        linewidth=0.9,
        zorder=7,
        label=r"Nominal SIMC ($\tau_c = 0.40$ min)",
    )

    ax_b_twin = ax_b.twinx()
    line_iae, = ax_b_twin.plot(
        data.simc_tau_c,
        data.simc_iae,
        color=color_iae,
        linestyle="-.",
        linewidth=1.8,
        label=r"Tracking Error $\mathrm{IAE}$ ($\mathrm{K\cdot min}$)",
        zorder=4,
    )
    ax_b_twin.set_ylabel(r"Tracking Error $\mathrm{IAE}$ ($\mathrm{K\cdot min}$)", color=color_iae)
    ax_b_twin.tick_params(axis="y", labelcolor=color_iae, colors=color_iae)
    ax_b_twin.spines["right"].set_color(color_iae)
    ax_b_twin.spines["right"].set_linewidth(1.0)
    ax_b_twin.spines["left"].set_visible(False)
    ax_b_twin.set_ylim(0.65, 5.55)

    ax_b.set_title(
        r"(b) Robustness Boundary ($M_s$) and Tracking Metric ($\mathrm{IAE}$) vs. $\tau_c$",
        loc="left",
        fontweight="bold",
        pad=3.5,
    )

    lines_b = [line_ms, line_iae, line_rob, line_lim, line_pt]
    labels_b = [str(artist.get_label()) for artist in lines_b]
    ax_b.legend(
        lines_b,
        labels_b,
        loc="lower center",
        bbox_to_anchor=(0.50, 1.10),
        ncol=2,
        frameon=True,
        framealpha=0.95,
        facecolor="#FFFFFF",
        edgecolor="#CCCCCC",
        markerscale=0.85,
        handletextpad=0.4,
        columnspacing=1.0,
        borderpad=0.3,
    )

    return ax_b_twin


def generate_figure_4() -> Figure:
    """Executa a geração e exportação da Figura 4 limpa e sem sobreposições."""
    cache_path = PROJECT_ROOT / "experiments" / ".exp_03_cache.pkl"
    data = load_experiment_cache(cache_path, allowed_root=PROJECT_ROOT)

    configure_rcparams()
    layout_engine = create_layout_engine(w_pad=0.03, h_pad=0.04, wspace=0.03, hspace=0.06)

    fig, (ax_a, ax_b) = plt.subplots(
        2,
        1,
        figsize=(SN_JNL_TEXTWIDTH_IN, FIG_HEIGHT_IN),
        dpi=600,
        gridspec_kw={"height_ratios": [1.08, 1.0]},
        layout=layout_engine,
    )

    render_panel_a(fig, ax_a, data)
    render_panel_b(ax_b, data)

    target_dirs: Sequence[Path] = [
        PROJECT_ROOT / "Artigos_Rascunhos" / "Artigo_01_Classic_Methods" / "overleaf" / "figures",
        PROJECT_ROOT / "Artigos_Rascunhos" / "Artigo_01_Classic_Methods" / "figures_novas",
        PROJECT_ROOT / "Artigos_Rascunhos" / "Artigo_01_PID_Neural_Comparativo" / "figures",
    ]

    for directory in target_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        pdf_path = directory / "fig4_pareto_iae_tv.pdf"
        png_path = directory / "fig4_pareto_iae_tv.png"
        fig.savefig(pdf_path, dpi=600, bbox_inches="tight", pad_inches=0.05)
        fig.savefig(png_path, dpi=600, bbox_inches="tight", pad_inches=0.05)
        logger.info("Salvo com sucesso: %s", pdf_path)

    return fig


if __name__ == "__main__":
    generated_fig = generate_figure_4()
    plt.close(generated_fig)
