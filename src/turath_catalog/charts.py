"""README charts, drawn from a release with matplotlib (optional dependency: pip install 'turath-catalog[charts]')."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#b9b8b2", "#e7e6e2"
SERIES = "#2a78d6"


def _plt():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:  # pragma: no cover
        raise SystemExit("charts need matplotlib: pip install 'turath-catalog[charts]'") from e
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK2,
            "xtick.color": INK2,
            "ytick.color": INK2,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
        }
    )
    return plt


def _title(ax, title: str, sub: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold", pad=22)
    ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", metadata={"Software": None})
    import matplotlib.pyplot as plt

    plt.close(fig)
    return path


def by_century(t: dict):
    A = {a["author_id"]: a for a in t["authors"]}
    c = Counter()
    for w in t["works"]:
        a = A.get(w["author_id"] or "")
        c[a["century_ah"] if a and a["century_ah"] else 0] += 1
    return [c.get(i, 0) for i in range(1, 16)], c.get(0, 0)


def chart_century(t: dict, out: Path) -> Path:
    plt = _plt()
    counts, unknown = by_century(t)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    xs = list(range(1, 16))
    ax.bar(xs, counts, color=SERIES, width=0.72, zorder=2)
    ax.bar([16.4], [unknown], color=MUTED, width=0.72, zorder=2)
    ax.set_xticks(xs + [16.4], [str(x) for x in xs] + ["?"])
    ax.set_xlabel("Hijri century of the author's death  (? = not known)")
    ax.yaxis.grid(True, color=GRID, zorder=0)
    ax.tick_params(length=0)
    for i in sorted(range(15), key=lambda i: -counts[i])[:3]:
        ax.text(xs[i], counts[i], f"{counts[i]:,}", ha="center", va="bottom", fontsize=9, color=INK2)
    _title(ax, "Works by century", f"{len(t['works']):,} works; century from the author's death year or the catalog record")
    return _save(fig, out / "works-by-century.png")


def chart_category(t: dict, out: Path) -> Path:
    plt = _plt()
    cats = sorted(t["categories"], key=lambda c: c["n_works"])
    fig, ax = plt.subplots(figsize=(8, 9.5))
    ys = range(len(cats))
    ax.barh(list(ys), [c["n_works"] for c in cats], color=SERIES, height=0.7, zorder=2)
    ax.set_yticks(list(ys), [c["category_en"] for c in cats], fontsize=9)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    ax.tick_params(length=0)
    ax.set_ylim(-0.6, len(cats) - 0.4)
    for i in (len(cats) - 1, len(cats) - 2, len(cats) - 3):
        ax.text(cats[i]["n_works"], i, f" {cats[i]['n_works']:,}", va="center", fontsize=9, color=INK2)
    _title(ax, "Works by category", "the 40 subject categories of al-Maktaba al-Shamila")
    return _save(fig, out / "works-by-category.png")


def chart_editions(t: dict, out: Path) -> Path:
    plt = _plt()
    c = Counter(min(w["n_editions"], 5) for w in t["works"])
    labels = ["1", "2", "3", "4", "5+"]
    vals = [c.get(i, 0) for i in range(1, 6)]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(range(5), vals, color=SERIES, width=0.62, zorder=2)
    ax.set_yscale("log")
    ax.set_xticks(range(5), labels)
    ax.set_xlabel("editions of the work in the dataset")
    ax.set_ylabel("works (log scale)")
    ax.yaxis.grid(True, color=GRID, zorder=0, which="major")
    ax.tick_params(length=0)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=9, color=INK2)
    multi = sum(vals[1:])
    _title(ax, "Editions per work", f"{multi:,} works come in two or more editions, each described separately")
    return _save(fig, out / "editions-per-work.png")


def completeness(t: dict) -> list[tuple[str, float]]:
    e, a, w = t["editions"], t["authors"], t["works"]
    p = lambda n, d: 100 * n / d if d else 0
    dated = [x for x in a if x["death_ah"]]
    return [
        ("edition: publisher", p(sum(1 for x in e if x["publisher_ar"]), len(e))),
        ("edition: year (AH or CE)", p(sum(1 for x in e if x["year_ah"] or x["year_ce"]), len(e))),
        ("edition: editor", p(sum(1 for x in e if x["editors_ar"]), len(e))),
        ("edition: printed pages", p(sum(1 for x in e if x["pages"]), len(e))),
        ("edition: place", p(sum(1 for x in e if x["place_ar"]), len(e))),
        ("author: death year", p(len(dated), len(a))),
        ("dated author: Wikidata item", p(sum(1 for x in dated if x["wikidata_qid"]), len(dated))),
        ("work: Shamela book", p(sum(1 for x in w if "shamela:" in (x["ext_ids"] or "")), len(w))),
        ("work: OpenITI URI", p(sum(1 for x in w if x["openiti_uri"]), len(w))),
    ]


def chart_completeness(t: dict, out: Path) -> Path:
    plt = _plt()
    rows = completeness(t)[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.barh(range(len(rows)), [v for _, v in rows], color=SERIES, height=0.62, zorder=2)
    ax.set_yticks(range(len(rows)), [k for k, _ in rows])
    ax.set_xlim(0, 100)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    ax.tick_params(length=0)
    for i, (_, v) in enumerate(rows):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9, color=INK2)
    _title(ax, "How complete the records are", "share of rows with a value; every value carries its source")
    return _save(fig, out / "completeness.png")


def card(t: dict, out: Path) -> Path:
    """1200x750 landing card (WebP): the century chart and three headline numbers."""
    plt = _plt()
    counts, _ = by_century(t)
    fig = plt.figure(figsize=(8, 5), dpi=150)
    fig.text(0.05, 0.9, "turath-catalog", fontsize=22, fontweight="bold", color=INK)
    fig.text(0.05, 0.84, "Classical Arabic works and their printed editions — open data, CC BY 4.0", fontsize=10.5, color=INK2)
    nums = [(len(t["works"]), "works"), (len(t["editions"]), "editions"), (sum(1 for a in t["authors"] if a["death_ah"]), "dated authors")]
    for i, (n, label) in enumerate(nums):
        fig.text(0.05 + i * 0.3, 0.7, f"{n:,}", fontsize=24, fontweight="bold", color=SERIES)
        fig.text(0.05 + i * 0.3, 0.655, label, fontsize=10, color=INK2)
    ax = fig.add_axes((0.07, 0.1, 0.88, 0.45))
    ax.bar(range(1, 16), counts, color=SERIES, width=0.72, zorder=2)
    ax.set_xticks(range(1, 16))
    ax.yaxis.grid(True, color=GRID, zorder=0)
    ax.tick_params(length=0)
    ax.set_xlabel("works by Hijri century of the author's death", color=INK2)
    png = out / "card.png"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=150, facecolor=SURFACE, metadata={"Software": None})
    plt.close(fig)
    from PIL import Image

    webp = out / "card.webp"
    Image.open(png).convert("RGB").resize((1200, 750)).save(webp, "WEBP", quality=88, method=6)
    png.unlink()
    return webp


def draw_all(t: dict, out: Path) -> list[Path]:
    return [chart_century(t, out), chart_category(t, out), chart_editions(t, out), chart_completeness(t, out), card(t, out)]
