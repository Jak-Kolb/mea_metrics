"""Rate-normalized STTC (residualize vs mean firing rate)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_rate_normalized_sttc(df: pd.DataFrame) -> pd.DataFrame:
    """Add residual STTC columns after linear regression on rate.

    - ``sttc_rate_resid_unit``: residual of ``sttc_mean_unit`` ~ ``rate_hz``
      (fit on finite active rows).
    - ``sttc_rate_resid_window``: residual of ``sttc_mean_window`` ~ window mean rate
      (one fit across regions using per-region means).
    """
    out = df.copy()

    # Unit-level residual
    m = out["is_active"].astype(bool) if "is_active" in out.columns else np.ones(len(out), bool)
    x = out.loc[m, "rate_hz"].to_numpy(float)
    y = out.loc[m, "sttc_mean_unit"].to_numpy(float)
    ok = np.isfinite(x) & np.isfinite(y)
    resid = np.full(len(out), np.nan)
    if ok.sum() >= 10 and np.std(x[ok]) > 0:
        coef = np.polyfit(x[ok], y[ok], 1)
        pred = np.polyval(coef, out["rate_hz"].to_numpy(float))
        resid = out["sttc_mean_unit"].to_numpy(float) - pred
    out["sttc_rate_resid_unit"] = resid

    # Window-level: regress region-mean STTC on region-mean rate
    g = out.groupby("region_index", as_index=False).agg(
        rate_hz=("rate_hz", "mean"),
        sttc_mean_window=("sttc_mean_window", "first"),
    )
    xr = g["rate_hz"].to_numpy(float)
    yr = g["sttc_mean_window"].to_numpy(float)
    ok = np.isfinite(xr) & np.isfinite(yr)
    wresid_map = {}
    if ok.sum() >= 4 and np.std(xr[ok]) > 0:
        coef = np.polyfit(xr[ok], yr[ok], 1)
        for _, row in g.iterrows():
            ridx = int(row["region_index"])
            if np.isfinite(row["sttc_mean_window"]) and np.isfinite(row["rate_hz"]):
                wresid_map[ridx] = float(row["sttc_mean_window"] - np.polyval(coef, row["rate_hz"]))
            else:
                wresid_map[ridx] = float("nan")
    out["sttc_rate_resid_window"] = out["region_index"].map(wresid_map)
    return out
