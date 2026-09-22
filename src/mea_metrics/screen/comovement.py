"""Plan C optional: culture × Δ-metric PCA / correlation co-movement (n=4, descriptive)."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[3]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mea_metrics.screen.__main__ import ALL_RECORDINGS, pick_primary_injury
from mea_metrics.screen.bars import WINDOW_METRICS, partition_regions

# Coherent Δ-set for PCA (true post−baseline culture summaries).
PCA_DELTA_METRICS: Sequence[str] = (
    "rate_hz",
    "burst_count",
    "sttc_mean_unit",
    "sttc_degree",
    "sttc_rate_resid_unit",
    "sttc_mean_window",
    "sttc_rate_resid_window",
    "rate_hz_delta",
    "burst_count_delta",
    "sttc_mean_unit_delta",
    "sttc_degree_delta",
)

# Culture-level recovery / ratio fields (not mixed into PCA by default).
CULTURE_RATIO_FIELDS: Sequence[str] = (
    "burst_rate_ratio_post0",
    "burst_rate_ratio_post_mid",
    "burst_rate_ratio_post_last",
    "rate_ratio_post0",
    "rate_ratio_post_mid",
    "rate_ratio_post_last",
)
CULTURE_TAU_FIELDS: Sequence[str] = ("tau_rec_burst_s", "tau_rec_rate_s")

FIELD_KIND = {
    **{m: "delta" for m in PCA_DELTA_METRICS},
    **{m: "ratio" for m in CULTURE_RATIO_FIELDS},
    **{m: "tau_s" for m in CULTURE_TAU_FIELDS},
}


def _resolve_injury(df: pd.DataFrame, recording: str) -> tuple[float, float, str]:
    """Prefer injury columns already on novel; else matref + pick_primary_injury."""
    if {"injury_start_s", "injury_end_s"}.issubset(df.columns):
        start = float(df["injury_start_s"].iloc[0])
        end = float(df["injury_end_s"].iloc[0])
        label = str(df["injury_label"].iloc[0]) if "injury_label" in df.columns else "?"
        return start, end, label
    try:
        from mea_metrics.matref import load_reference

        ref = load_reference(recording)
        if ref.injuries is None or ref.injuries.n < 1:
            raise RuntimeError("no injuries")
        _, start, end, label = pick_primary_injury(ref.injuries)
        return float(start), float(end), str(label)
    except Exception as exc:  # noqa: BLE001 — descriptive fallback path
        raise RuntimeError(
            f"{recording}: need injury_start_s/end_s on novel or matref data ({exc})"
        ) from exc


def _unit_post_minus_baseline(
    df: pd.DataFrame,
    metric: str,
    baseline: np.ndarray,
    post: np.ndarray,
) -> float:
    """Median-across-units of (unit post median − unit baseline median)."""
    if metric not in df.columns or baseline.size == 0 or post.size == 0:
        return float("nan")
    base = df[df["region_index"].isin(baseline)].groupby("unit_id")[metric].median()
    post_s = df[df["region_index"].isin(post)].groupby("unit_id")[metric].median()
    both = base.index.intersection(post_s.index)
    if len(both) == 0:
        return float("nan")
    return float(np.nanmedian((post_s.loc[both] - base.loc[both]).to_numpy(dtype=float)))


def _window_post_minus_baseline(
    df: pd.DataFrame,
    metric: str,
    baseline: np.ndarray,
    post: np.ndarray,
) -> float:
    """Mean over post regions minus mean over baseline regions (window metrics)."""
    if metric not in df.columns or baseline.size == 0 or post.size == 0:
        return float("nan")
    base_v = (
        df[df["region_index"].isin(baseline)].groupby("region_index")[metric].first().to_numpy(dtype=float)
    )
    post_v = (
        df[df["region_index"].isin(post)].groupby("region_index")[metric].first().to_numpy(dtype=float)
    )
    if base_v.size == 0 or post_v.size == 0:
        return float("nan")
    return float(np.nanmean(post_v) - np.nanmean(base_v))


def _novel_delta_culture_mean(df: pd.DataFrame, col: str) -> float:
    """Culture mean of unit-level *_delta (one value per unit)."""
    if col not in df.columns:
        return float("nan")
    if "unit_id" in df.columns:
        s = df.groupby("unit_id")[col].first()
    else:
        s = df[col]
    return float(np.nanmean(s.to_numpy(dtype=float)))


def culture_delta_row(recording: str, library_dir: Path) -> dict:
    novel_path = library_dir / f"{recording}_novel.parquet"
    metrics_path = library_dir / f"{recording}_metrics.parquet"
    if not novel_path.is_file():
        raise FileNotFoundError(novel_path)
    df = pd.read_parquet(novel_path)
    if metrics_path.is_file():
        metrics = pd.read_parquet(metrics_path)
        extra = [c for c in metrics.columns if c not in df.columns]
        keys = [k for k in ("unit_id", "region_index") if k in df.columns and k in metrics.columns]
        if keys and extra:
            df = df.merge(metrics[keys + extra], on=keys, how="left")

    inj_start, inj_end, inj_label = _resolve_injury(df, recording)
    baseline, during, post = partition_regions(df, inj_start, inj_end)

    row: dict = {
        "recording": recording,
        "injury_label": inj_label,
        "injury_start_s": inj_start,
        "injury_end_s": inj_end,
        "n_baseline_regions": int(baseline.size),
        "n_during_regions": int(during.size),
        "n_post_regions": int(post.size),
    }

    # Prefer novel *_delta culture means; recompute other Δ via screen split.
    for m in PCA_DELTA_METRICS:
        if m.endswith("_delta"):
            row[m] = _novel_delta_culture_mean(df, m)
        elif m in WINDOW_METRICS or m.endswith("_window"):
            row[m] = _window_post_minus_baseline(df, m, baseline, post)
        else:
            row[m] = _unit_post_minus_baseline(df, m, baseline, post)

    for c in list(CULTURE_RATIO_FIELDS) + list(CULTURE_TAU_FIELDS):
        if c in df.columns:
            row[c] = float(df[c].iloc[0]) if pd.notna(df[c].iloc[0]) else float("nan")
        else:
            row[c] = float("nan")

    return row


def build_culture_delta_matrix(
    recordings: Iterable[str] = ALL_RECORDINGS,
    *,
    library_dir: Path | str = "reports/library",
) -> pd.DataFrame:
    lib = Path(library_dir)
    rows = [culture_delta_row(rec, lib) for rec in recordings]
    return pd.DataFrame(rows).set_index("recording")


def _pca_ready(matrix: pd.DataFrame, cols: Sequence[str]) -> tuple[pd.DataFrame, list[str]]:
    sub = matrix.reindex(columns=list(cols)).apply(pd.to_numeric, errors="coerce")
    keep: list[str] = []
    for c in sub.columns:
        v = sub[c].to_numpy(dtype=float)
        if np.all(~np.isfinite(v)):
            continue
        finite = v[np.isfinite(v)]
        if finite.size < 2:
            continue
        if float(np.nanstd(finite)) < 1e-12:
            continue
        keep.append(c)
    return sub[keep], keep


def run_pca(X: pd.DataFrame) -> dict:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    arr = X.to_numpy(dtype=float)
    # Impute remaining NaNs with column mean (descriptive only).
    col_means = np.nanmean(arr, axis=0)
    inds = np.where(~np.isfinite(arr))
    arr = arr.copy()
    arr[inds] = np.take(col_means, inds[1])
    Z = StandardScaler().fit_transform(arr)
    n_comp = min(2, Z.shape[0], Z.shape[1])
    pca = PCA(n_components=n_comp)
    scores = pca.fit_transform(Z)
    out = {
        "variance_ratio": pca.explained_variance_ratio_.tolist(),
        "loadings": pd.DataFrame(
            pca.components_.T,
            index=list(X.columns),
            columns=[f"PC{i+1}" for i in range(n_comp)],
        ),
        "scores": pd.DataFrame(
            scores,
            index=list(X.index),
            columns=[f"PC{i+1}" for i in range(n_comp)],
        ),
    }
    return out


def correlation_matrix(X: pd.DataFrame) -> pd.DataFrame:
    return X.corr(method="pearson")


def _fmt(x: float) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "nan"
    if abs(x) >= 1000 or (abs(x) > 0 and abs(x) < 1e-3):
        return f"{x:.4g}"
    return f"{x:.4g}"


def write_figures(
    corr: pd.DataFrame,
    pca: dict,
    out_dir: Path,
) -> list[Path]:
    paths: list[Path] = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return paths

    out_dir.mkdir(parents=True, exist_ok=True)

    # Correlation heatmap
    fig, ax = plt.subplots(figsize=(8, 6))
    cax = ax.imshow(corr.to_numpy(), vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=8)
    ax.set_yticklabels(corr.index, fontsize=8)
    ax.set_title("Culture Δ-metric correlation (n=4, descriptive)")
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    p1 = out_dir / "comovement_corr.png"
    fig.savefig(p1, dpi=140)
    plt.close(fig)
    paths.append(p1)

    # PCA loadings bar for PC1
    load = pca["loadings"]
    if "PC1" in load.columns:
        fig, ax = plt.subplots(figsize=(8, 4))
        order = load["PC1"].abs().sort_values(ascending=False).index
        ax.bar(range(len(order)), load.loc[order, "PC1"].to_numpy(), color="steelblue")
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels(order, rotation=90, fontsize=8)
        ax.axhline(0, color="k", lw=0.8)
        var1 = pca["variance_ratio"][0] * 100
        ax.set_title(f"PC1 loadings ({var1:.1f}% var; n=4 descriptive)")
        ax.set_ylabel("loading")
        fig.tight_layout()
        p2 = out_dir / "comovement_pca.png"
        fig.savefig(p2, dpi=140)
        plt.close(fig)
        paths.append(p2)

    return paths


def write_comovement_md(
    matrix: pd.DataFrame,
    pca_cols: list[str],
    pca: dict,
    corr: pd.DataFrame,
    *,
    csv_path: Path,
    fig_paths: Sequence[Path],
    out_path: Path,
) -> None:
    load = pca["loadings"]
    pc1 = load["PC1"].reindex(pca_cols) if "PC1" in load.columns else pd.Series(dtype=float)
    top = pc1.reindex(pc1.abs().sort_values(ascending=False).index)

    # Co-moving groups: |corr| >= 0.7 pairs among PCA cols
    pairs = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            r = corr.loc[a, b]
            if np.isfinite(r) and abs(r) >= 0.7:
                pairs.append((a, b, float(r)))
    pairs.sort(key=lambda t: -abs(t[2]))

    var = pca["variance_ratio"]
    var_txt = ", ".join(f"PC{i+1}={100*v:.1f}%" for i, v in enumerate(var))

    lines = [
        "# Culture × Δ-metric co-movement (Plan C optional)",
        "",
        "## Method",
        "",
        "- One row per recording (n=4 Adam cultures).",
        "- Region split = same screen harness logic: "
        "`partition_regions` / `_injury_region_split` with injury from novel "
        "`injury_start_s`/`injury_end_s` (written by novel build via matref + "
        "`pick_primary_injury`).",
        "- **Δ columns:** for novel `*_delta`, culture mean of per-unit deltas; "
        "for unit metrics, median-across-units of (unit post median − unit baseline median); "
        "for window metrics, mean(post regions) − mean(baseline regions).",
        "- Recovery `tau_rec_*` are times (s); `*_ratio_*` are post/baseline ratios "
        "(not true deltas). PCA uses the coherent Δ set only (standardized columns).",
        "- **Descriptive only.** n=4 → no inference, no LOO classifiers, no p-values.",
        "",
        f"Matrix CSV: `{csv_path.as_posix()}`",
        "",
    ]
    if fig_paths:
        lines.append("Figures: " + ", ".join(f"`{p.as_posix()}`" for p in fig_paths))
        lines.append("")

    lines.extend(
        [
            "## Table snapshot (PCA Δ columns)",
            "",
            "| recording | " + " | ".join(pca_cols) + " |",
            "|---|" + "|".join(["---:" for _ in pca_cols]) + "|",
        ]
    )
    for rec in matrix.index:
        cells = [_fmt(float(matrix.loc[rec, c])) if c in matrix.columns else "nan" for c in pca_cols]
        lines.append(f"| `{rec}` | " + " | ".join(cells) + " |")
    lines.append("")

    lines.extend(
        [
            "## Field kinds (ratios / taus excluded from PCA)",
            "",
            "| field | kind |",
            "|---|---|",
        ]
    )
    for f in list(CULTURE_RATIO_FIELDS) + list(CULTURE_TAU_FIELDS):
        lines.append(f"| `{f}` | {FIELD_KIND.get(f, '?')} |")
    lines.append("")

    lines.extend(
        [
            "## PCA (standardized Δ columns)",
            "",
            f"- Variance explained: **{var_txt}**",
            "- Top PC1 loadings (signed):",
            "",
        ]
    )
    for name, val in top.items():
        lines.append(f"  - `{name}`: {_fmt(float(val))}")
    if "PC2" in load.columns:
        pc2 = load["PC2"]
        pc2_top = pc2.reindex(pc2.abs().sort_values(ascending=False).index)
        lines.append("- Top PC2 loadings (signed):")
        lines.append("")
        for name, val in list(pc2_top.items())[:8]:
            lines.append(f"  - `{name}`: {_fmt(float(val))}")
    lines.append("")

    lines.extend(["## Co-moving pairs (|r|≥0.7 among PCA Δ cols)", ""])
    if not pairs:
        lines.append("_No pairs at |r|≥0.7 (or too few finite columns)._")
    else:
        for a, b, r in pairs[:20]:
            lines.append(f"- `{a}` ↔ `{b}`: r={_fmt(r)}")
    lines.append("")

    # Brief takeaway from loadings / pairs
    pos = [k for k, v in top.items() if v > 0]
    neg = [k for k, v in top.items() if v < 0]
    lines.extend(
        [
            "## Takeaway (3–5 sentences, descriptive)",
            "",
            f"Across the four cultures, PC1 explains {100*var[0]:.0f}% of standardized Δ variance"
            + (f" and PC2 {100*var[1]:.0f}%." if len(var) > 1 else "."),
            (
                "PC1 co-loads positively on "
                + ", ".join(f"`{x}`" for x in pos[:4])
                + ("…" if len(pos) > 4 else "")
                + " and negatively on "
                + ", ".join(f"`{x}`" for x in neg[:4])
                + ("…" if len(neg) > 4 else "")
                + ", i.e. rate/burst and STTC topology deltas tend to move as one polarity axis."
                if pos and neg
                else "PC1 loadings are one-sided on this tiny matrix — treat as exploratory only."
            ),
            (
                "High |r| pairs reinforce that unit STTC / degree / rate deltas travel together "
                "more than residualized STTC in this n=4 sketch."
                if pairs
                else "Correlation structure is weak or unstable at n=4."
            ),
            "Ratios and τ_rec are reported in the CSV for context but were kept out of PCA "
            "so the component axes stay in Δ-units.",
            "**Hard caveat: n=4, descriptive only — no inference, no classifiers, no threshold changes.**",
            "",
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")


def run(
    *,
    library_dir: Path = Path("reports/library"),
    out_dir: Path = Path("reports/screen"),
    recordings: Sequence[str] = ALL_RECORDINGS,
) -> dict:
    matrix = build_culture_delta_matrix(recordings, library_dir=library_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "culture_delta_matrix.csv"
    # Include kind row? Keep flat; document kinds in MD.
    matrix.to_csv(csv_path)

    pca_frame, pca_cols = _pca_ready(matrix, PCA_DELTA_METRICS)
    pca = run_pca(pca_frame)
    corr = correlation_matrix(pca_frame)
    figs = write_figures(corr, pca, out_dir)
    md_path = out_dir / "COMOVEMENT.md"
    write_comovement_md(
        matrix,
        pca_cols,
        pca,
        corr,
        csv_path=csv_path,
        fig_paths=figs,
        out_path=md_path,
    )
    return {
        "matrix": matrix,
        "pca_cols": pca_cols,
        "pca": pca,
        "corr": corr,
        "csv": csv_path,
        "md": md_path,
        "figs": figs,
    }


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Culture × Δ-metric co-movement (descriptive n=4)")
    p.add_argument("--library-dir", default="reports/library")
    p.add_argument("--out-dir", default="reports/screen")
    args = p.parse_args(argv)
    result = run(library_dir=Path(args.library_dir), out_dir=Path(args.out_dir))
    pca = result["pca"]
    print(f"wrote {result['csv']}")
    print(f"wrote {result['md']}")
    for f in result["figs"]:
        print(f"wrote {f}")
    print("PCA variance:", ", ".join(f"{100*v:.1f}%" for v in pca["variance_ratio"]))
    print("PC1 loadings:")
    pc1 = pca["loadings"]["PC1"]
    for k, v in pc1.reindex(pc1.abs().sort_values(ascending=False).index).items():
        print(f"  {k}: {v:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
