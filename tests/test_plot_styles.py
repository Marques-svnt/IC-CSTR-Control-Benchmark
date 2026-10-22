"""Unit tests for IEEE plot styling utilities."""

import matplotlib as mpl

from src.evaluation.plot_styles import (
    IEEE_DOUBLE_COL_WIDTH_INCHES,
    IEEE_PALETTE,
    IEEE_SINGLE_COL_WIDTH_INCHES,
    get_figure_dimensions,
    setup_ieee_style,
)


def test_setup_ieee_style() -> None:
    """Verifies that IEEE style sets TrueType fonts and serif family."""
    setup_ieee_style(single_column=True)
    assert mpl.rcParams["pdf.fonttype"] == 42
    assert mpl.rcParams["font.family"] == ["serif"]
    assert "Times New Roman" in mpl.rcParams["font.serif"]


def test_get_figure_dimensions() -> None:
    """Verifies standard IEEE single and double column figure dimensions."""
    w1, h1 = get_figure_dimensions(columns=1, aspect_ratio=0.75)
    assert w1 == IEEE_SINGLE_COL_WIDTH_INCHES
    assert abs(h1 - IEEE_SINGLE_COL_WIDTH_INCHES * 0.75) < 1e-4

    w2, h2 = get_figure_dimensions(columns=2, height_override=4.5)
    assert w2 == IEEE_DOUBLE_COL_WIDTH_INCHES
    assert h2 == 4.5


def test_palette_contains_standard_controllers() -> None:
    """Ensures color palette contains key benchmark controllers."""
    assert "Ziegler-Nichols" in IEEE_PALETTE
    assert "Cohen-Coon" in IEEE_PALETTE
    assert "Skogestad SIMC" in IEEE_PALETTE
    assert "Optimal ITAE (Ms<=1.6)" in IEEE_PALETTE


def test_all_benchmark_controllers_use_okabe_ito() -> None:
    """Every controller of the IC-T04 campaign has a distinct Okabe-Ito color/style pair."""
    from src.evaluation.plot_styles import (
        BENCHMARK_CONTROLLERS,
        IEEE_LINESTYLES,
        OKABE_ITO,
    )

    pairs = set()
    for name in BENCHMARK_CONTROLLERS:
        assert IEEE_PALETTE[name] in OKABE_ITO.values()
        pairs.add((IEEE_PALETTE[name], IEEE_LINESTYLES[name]))
    assert len(pairs) == len(BENCHMARK_CONTROLLERS)


def test_tueplots_rcparams_applied() -> None:
    """setup_ieee_style layers tueplots axes settings (no silent fallback)."""
    from tueplots import axes

    setup_ieee_style(single_column=True)
    assert mpl.rcParams["axes.axisbelow"] == axes.lines()["axes.axisbelow"]
    assert mpl.rcParams["xtick.direction"] == "in"
