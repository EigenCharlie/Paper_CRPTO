"""Generate the IJDS primary-allocation chronology and outcome-join figure.

This is a code-native editorial figure: it contains no empirical computation
and introduces no evidence beyond the active protocol chronology.  The output
is written in both vector PDF and 300-DPI PNG form so that the same source can
be used by the print and HTML builds.

Usage
-----
    uv run python scripts/generate_ijds_information_boundary_figure.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "reports" / "crpto" / "figures"
STEM = "crpto_ijds_information_boundary"

INK = "#17212B"
MUTED = "#536273"
BLUE = "#2468A2"
BLUE_DARK = "#184B78"
BLUE_LIGHT = "#EAF3FA"
TEAL = "#1B817A"
TEAL_LIGHT = "#E9F6F3"
AMBER = "#A56216"
AMBER_LIGHT = "#FFF4DF"
RED = "#A33B3B"
RED_LIGHT = "#FBECEC"
GRAY_LIGHT = "#F2F4F6"
WHITE = "#FFFFFF"


def _rounded_box(
    ax: plt.Axes,
    *,
    xy: tuple[float, float],
    width: float,
    height: float,
    facecolor: str,
    edgecolor: str,
    title: str,
    body: str,
    title_color: str = INK,
    body_color: str = MUTED,
    linewidth: float = 1.2,
) -> None:
    """Draw a rounded stage box with stable typography."""

    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=linewidth,
        edgecolor=edgecolor,
        facecolor=facecolor,
        transform=ax.transAxes,
        clip_on=False,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height * 0.69,
        title,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9.2,
        fontweight="bold",
        color=title_color,
        zorder=3,
    )
    ax.text(
        x + width / 2,
        y + height * 0.33,
        body,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.8,
        linespacing=1.28,
        color=body_color,
        zorder=3,
    )


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = BLUE_DARK,
    linewidth: float = 1.6,
    mutation_scale: float = 13,
    connectionstyle: str = "arc3",
    zorder: float = 4,
) -> None:
    """Draw a construction-order arrow in axes coordinates."""

    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            transform=ax.transAxes,
            arrowstyle="-|>",
            mutation_scale=mutation_scale,
            linewidth=linewidth,
            color=color,
            connectionstyle=connectionstyle,
            shrinkA=1.5,
            shrinkB=1.5,
            zorder=zorder,
        )
    )


def build_figure() -> plt.Figure:
    """Build the chronology figure."""

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": WHITE,
            "text.color": INK,
        }
    )

    fig, ax = plt.subplots(figsize=(7.2, 5.35))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    ax.text(
        0.5,
        0.965,
        "Primary allocation chronology and keyed outcome join",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=12.0,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.5,
        0.919,
        "TARGET-EVALUATION-OUTCOME-FREE PRIMARY CONSTRUCTION",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.4,
        fontweight="bold",
        color=BLUE_DARK,
        bbox={
            "boxstyle": "round,pad=0.28",
            "facecolor": BLUE_LIGHT,
            "edgecolor": "none",
        },
    )

    box_width = 0.275
    box_height = 0.145
    x_positions = (0.035, 0.3625, 0.69)
    upper_y = 0.735
    lower_y = 0.405

    _rounded_box(
        ax,
        xy=(x_positions[0], upper_y),
        width=box_width,
        height=box_height,
        facecolor=BLUE_LIGHT,
        edgecolor=BLUE,
        title="1  PD development",
        body="2007-06–2010-12\nmodel fit",
    )
    _rounded_box(
        ax,
        xy=(x_positions[1], upper_y),
        width=box_width,
        height=box_height,
        facecolor=BLUE_LIGHT,
        edgecolor=BLUE,
        title="2  Calibrator + taxonomy",
        body="2011\nPlatt map + fixed score strata",
    )
    _rounded_box(
        ax,
        xy=(x_positions[2], upper_y),
        width=box_width,
        height=box_height,
        facecolor=BLUE_LIGHT,
        edgecolor=BLUE,
        title="3  Residual recipes",
        body="2012-01–2013-01\n8 overlapping complete windows",
    )
    _arrow(
        ax,
        (x_positions[0] + box_width, upper_y + box_height / 2),
        (x_positions[1], upper_y + box_height / 2),
    )
    _arrow(
        ax,
        (x_positions[1] + box_width, upper_y + box_height / 2),
        (x_positions[2], upper_y + box_height / 2),
    )

    _arrow(
        ax,
        (x_positions[2] + box_width / 2, upper_y),
        (x_positions[2] + box_width / 2, lower_y + box_height),
        zorder=1,
    )

    gate = FancyBboxPatch(
        (0.045, 0.605),
        0.91,
        0.083,
        boxstyle="round,pad=0.012,rounding_size=0.014",
        linewidth=1.0,
        edgecolor=AMBER,
        facecolor=AMBER_LIGHT,
        transform=ax.transAxes,
        clip_on=False,
        zorder=2,
    )
    ax.add_patch(gate)
    ax.text(
        0.5,
        0.646,
        "FIT-LABEL GATE  •  cutoff 2016-03-31",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.7,
        fontweight="bold",
        color=AMBER,
        zorder=3,
    )
    ax.text(
        0.5,
        0.619,
        "Unavailable labels are excluded only from the relevant fit—never from the OOT candidate universe.",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.5,
        color=INK,
        zorder=3,
    )

    _rounded_box(
        ax,
        xy=(x_positions[2], lower_y),
        width=box_width,
        height=box_height,
        facecolor=GRAY_LIGHT,
        edgecolor=MUTED,
        title="4  Policy development",
        body="2013-02–2013-12\noutcomes never read",
    )
    _rounded_box(
        ax,
        xy=(x_positions[1], lower_y),
        width=box_width,
        height=box_height,
        facecolor=TEAL_LIGHT,
        edgecolor=TEAL,
        title="5  Monthly OOT menus",
        body="primary 2016-04–2017-06\nextension 2017-07–09 (diagnostic)",
    )
    _rounded_box(
        ax,
        xy=(x_positions[0], lower_y),
        width=box_width,
        height=box_height,
        facecolor=TEAL_LIGHT,
        edgecolor=TEAL,
        title="6  Physical freeze",
        body="scores • sets • caps • allocations\nhashed before endpoint access",
    )
    _arrow(
        ax,
        (x_positions[2], lower_y + box_height / 2),
        (x_positions[1] + box_width, lower_y + box_height / 2),
        color=TEAL,
    )
    _arrow(
        ax,
        (x_positions[1], lower_y + box_height / 2),
        (x_positions[0] + box_width, lower_y + box_height / 2),
        color=TEAL,
    )

    firewall_y = 0.328
    ax.plot(
        [0.045, 0.955],
        [firewall_y, firewall_y],
        transform=ax.transAxes,
        color=RED,
        linewidth=1.25,
        linestyle=(0, (4, 3)),
        zorder=1,
    )
    ax.text(
        0.12,
        firewall_y,
        " OUTCOME FIREWALL ",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.3,
        fontweight="bold",
        color=RED,
        backgroundcolor=WHITE,
        zorder=5,
    )
    ax.text(
        0.80,
        firewall_y,
        "freeze identity verified before access",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.0,
        color=RED,
        backgroundcolor=WHITE,
        zorder=5,
    )

    join_x = 0.205
    join_y = 0.145
    join_width = 0.59
    join_height = 0.12
    _rounded_box(
        ax,
        xy=(join_x, join_y),
        width=join_width,
        height=join_height,
        facecolor=RED_LIGHT,
        edgecolor=RED,
        title="7  One keyed endpoint join",
        body=(
            "resolved endpoints evaluate frozen decisions; all 12,076 unresolved\n"
            "primary candidates remain in the sharp outcome bounds"
        ),
        title_color=RED,
        body_color=INK,
        linewidth=1.4,
    )
    _arrow(
        ax,
        (x_positions[0] + box_width / 2, lower_y),
        (join_x + join_width / 2, join_y + join_height),
        color=RED,
        linewidth=1.8,
    )

    ax.text(
        0.5,
        0.064,
        "Arrows show construction order, not statistical transport.  The join creates neither exchangeability",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.4,
        color=MUTED,
    )
    ax.text(
        0.5,
        0.035,
        "nor prospective validity; it only evaluates decisions that were already frozen.",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.4,
        color=MUTED,
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.99, bottom=0.01)
    return fig


def main() -> None:
    """Write deterministic publication outputs."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    figure = build_figure()
    png_path = OUTPUT_DIR / f"{STEM}.png"
    pdf_path = OUTPUT_DIR / f"{STEM}.pdf"
    figure.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.04,
        facecolor=WHITE,
    )
    figure.savefig(
        pdf_path,
        bbox_inches="tight",
        pad_inches=0.04,
        facecolor=WHITE,
        metadata={"CreationDate": None, "ModDate": None},
    )
    plt.close(figure)
    print(png_path.relative_to(ROOT).as_posix())
    print(pdf_path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
