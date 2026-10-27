#!/usr/bin/env python3
"""Export bilingual accuracy charts. Requires Matplotlib 3.10.7 only to regenerate.

Published values: Liu et al. (2016), Table 1, doi:10.1093/bioinformatics/btv604.
Reconstruction: macro-mean accuracy in the frozen 13 October training audit.
The ordinary website build copies these SVGs without requiring Matplotlib.
"""
from html import escape
import json
import os
from pathlib import Path
import re

os.environ.setdefault("MPLCONFIGDIR", "/tmp/enhancers-chart-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "replication/ienhancer_2l/checkpoints/2026-10-13-svm-training/training_audit.json"
ASSETS = ROOT / "website/assets"
PUBLISHED = (76.89, 61.93)
COLORS = ("#7390a1", "#008580")
INK, MUTED, PAPER, GRID = "#18343d", "#52656b", "#f6f5f0", "#cfdadb"


def render(language, local, mobile=False):
    es = language == "es"
    title = "Exactitud de clasificación" if es else "Classification accuracy"
    legend = ("Publicado", "Nuestra reconstrucción") if es else ("Published", "Our reconstruction")
    tasks = (("Etapa I\nDetección de potenciadores", "Etapa II\nFuertes frente a débiles") if es else
             ("Layer I\nEnhancer detection", "Layer II\nStrong versus weak"))
    description = (
        "Etapa I: publicado 76.89%, reconstrucción 76.21%. Etapa II: publicado 61.93%, "
        "reconstrucción 60.98%. Publicación: validación dejando uno fuera. Reconstrucción: "
        "media de cinco particiones externas por grupos. La etapa II evalúa potenciadores conocidos."
        if es else
        "Layer I: published 76.89%, reconstruction 76.21%. Layer II: published 61.93%, "
        "reconstruction 60.98%. Published: leave-one-out validation. Reconstruction: mean of "
        "five grouped outer folds. Layer II evaluates known enhancers."
    )
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "svg.fonttype": "none",
                         "svg.hashsalt": "ienhancer-accuracy", "text.color": INK})
    fig = plt.figure(figsize=(5.2, 8.2) if mobile else (11.4, 6.4), facecolor=PAPER)
    fig.text(0.06, 0.95, title, fontsize=17 if mobile else 23, weight="bold",
             color=COLORS[1], va="top")
    axes = ([fig.add_axes((0.16, 0.57, 0.79, 0.28)), fig.add_axes((0.16, 0.18, 0.79, 0.28))]
            if mobile else [fig.add_axes((0.11, 0.29, 0.85, 0.51))])
    for index, ax in enumerate(axes):
        ax.set_facecolor(PAPER)
        ax.set_ylim(0, 100)
        ax.set_yticks(range(0, 101, 20))
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.tick_params(axis="both", length=0, pad=10, labelsize=12 if mobile else 17,
                       labelcolor=MUTED)
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=GRID, linewidth=0.7)
        for side in ("left", "top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        indices = [index] if mobile else [0, 1]
        centers = [0] if mobile else [0, 1]
        width = 0.31
        for series, values in enumerate((PUBLISHED, local)):
            positions = [x + (series - 0.5) * width for x in centers]
            bars = ax.bar(positions, [values[i] for i in indices], width=width,
                          color=COLORS[series], linewidth=0)
            ax.bar_label(bars, labels=[f"{values[i]:.2f}%" for i in indices], padding=8,
                         fontsize=16 if mobile else 20, weight="bold", color=INK)
        ax.set_xlim(-0.55, 0.55 if mobile else 1.55)
        ax.set_xticks(centers, [tasks[i] for i in indices], color=INK,
                      fontsize=13 if mobile else 18)
    fig.legend([Patch(facecolor=color) for color in COLORS], legend,
               loc="lower center", bbox_to_anchor=(0.52, 0.035 if mobile else 0.045),
               ncol=1 if mobile else 2, frameon=False, fontsize=13 if mobile else 18,
               labelcolor=MUTED, handlelength=0.8, handleheight=0.8, handletextpad=0.4,
               columnspacing=1.8)
    name = f"ienhancer-2l-accuracy-{language}{'-mobile' if mobile else ''}.svg"
    target = ASSETS / name
    fig.savefig(target, format="svg", metadata={"Date": None, "Title": title,
                "Description": description, "Creator": "EnhancersResearch / Matplotlib 3.10.7"})
    plt.close(fig)
    svg = target.read_text()
    svg = re.sub(r"<svg\b([^>]*)>", lambda match:
                 '<svg' + match[1] + ' role="img" aria-labelledby="chart-title chart-desc">\n'
                 f'<title id="chart-title">{escape(title)}</title>\n'
                 f'<desc id="chart-desc">{escape(description)}</desc>', svg, count=1)
    target.write_text(svg)
    print(target.relative_to(ROOT))


def main():
    audit = json.loads(AUDIT.read_text())
    local = tuple(audit["layers"][layer]["macro_mean"]["accuracy"] * 100
                  for layer in ("layer1", "layer2"))
    for language in ("en", "es"):
        for mobile in (False, True):
            render(language, local, mobile)


if __name__ == "__main__":
    main()
