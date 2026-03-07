from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


AAVSO_RAW_REL = Path("data/raw/aavso_tcrb_raw_fullrange.csv")
ASASSN_RAW_REL = Path("data/raw/asassn_tcrb_vband_raw.csv")
ZTF_RAW_REL = Path("data/raw/ztf_tcrb_lightcurve_raw.csv")

VALIDCORE_REL = Path("data/interim/aavso_tcrb_validcore.parquet")

MODERN_START_JD = 2457023.5
MODERN_END_JD = 2461041.5

WINDOW_1946_START_JD = float(pd.Timestamp("1935-01-01").to_julian_date())
WINDOW_1946_END_JD = float(pd.Timestamp("1955-12-31").to_julian_date())

WINDOW_1866_START_JD = float(pd.Timestamp("1860-01-01").to_julian_date())
WINDOW_1866_END_JD = float(pd.Timestamp("1870-12-31").to_julian_date())

STRICT_UNCERTAINTY_MAX = 0.05

MODERN_V_LOOSE_REL = Path("data/interim/modern_V_2015_2025_loose.parquet")
MODERN_V_STRICT_REL = Path("data/interim/modern_V_2015_2025_strict_unc005.parquet")
MODERN_B_LOOSE_REL = Path("data/interim/modern_B_2015_2025_loose.parquet")
MODERN_VIS_REL = Path("data/interim/allcycles_Vis_2015_2025_raw.parquet")

ALLCYCLES_VIS_1866_RAW_REL = Path("data/interim/allcycles_Vis_1860_1870_raw.parquet")
ALLCYCLES_VIS_1946_RAW_REL = Path("data/interim/allcycles_Vis_1935_1955_raw.parquet")
AROUND_1946_V_REL = Path("data/interim/aavso_around_1946_1935_1955_V.parquet")

MODERN_V_BIN1D_CLEAN_REL = Path("data/clean/modern_V_2015_2025_bin1d.parquet")
MODERN_V_BIN7D_CLEAN_REL = Path("data/clean/modern_V_2015_2025_bin7d.parquet")
MODERN_V_BIN7D_ROLLMED3_CLEAN_REL = Path("data/clean/modern_V_2015_2025_bin7d_rollmed3.parquet")
MODERN_V_BIN7D_ROLLMED5_CLEAN_REL = Path("data/clean/modern_V_2015_2025_bin7d_rollmed5.parquet")
MODERN_V_STRICT_BIN7D_CLEAN_REL = Path("data/clean/modern_V_2015_2025_strict_unc005_bin7d.parquet")

ALLCYCLES_VIS_1866_BIN7D_CLEAN_REL = Path("data/clean/allcycles_Vis_1860_1870_bin7d.parquet")
ALLCYCLES_VIS_1946_BIN7D_CLEAN_REL = Path("data/clean/allcycles_Vis_1935_1955_bin7d.parquet")
ALLCYCLES_VIS_2015_BIN7D_CLEAN_REL = Path("data/clean/allcycles_Vis_2015_2025_bin7d.parquet")
RAW_IMAGE_GUIDE_REL = Path("notes/raw_image_guide.md")

AAVSO_USECOLS = [
    "JD",
    "Magnitude",
    "Uncertainty",
    "HQuncertainty",
    "Band",
    "Observer Code",
    "Validation Flag",
    "HJD",
    "Measurement Method",
]

ASASSN_USECOLS = ["hjd", "camera", "mag", "mag_err", "flux", "flux_err"]


def ensure_project_layout(root_dir: Path) -> None:
    for rel in (
        Path("data/raw"),
        Path("data/interim"),
        Path("data/clean"),
        Path("notebooks"),
        Path("figures"),
        Path("notes"),
    ):
        (root_dir / rel).mkdir(parents=True, exist_ok=True)


def standardize_columns(columns: list[str]) -> list[str]:
    return [
        column.strip()
        .lower()
        .replace("(", "")
        .replace(")", "")
        .replace("/", "_")
        .replace("-", "_")
        .replace(".", "")
        .replace(" ", "_")
        for column in columns
    ]


def normalize_band(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    cleaned = str(value).strip()
    if not cleaned:
        return pd.NA
    stripped = cleaned.rstrip(".")
    upper = stripped.upper()
    mapping = {
        "VIS": "Vis",
        "V": "V",
        "B": "B",
        "I": "I",
        "R": "R",
        "U": "U",
        "CV": "CV",
        "TG": "TG",
        "TB": "TB",
        "TR": "TR",
    }
    return mapping.get(upper, stripped)


def resolve_root(root_dir: Path | str | None = None) -> Path:
    resolved = Path(root_dir).resolve() if root_dir is not None else Path(__file__).resolve().parent
    ensure_project_layout(resolved)
    return resolved


def save_frame(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Unsupported output type for {path}")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read_aavso_preview(root_dir: Path) -> pd.DataFrame:
    return pd.read_csv(root_dir / AAVSO_RAW_REL, nrows=5, low_memory=False)


def _add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["is_flagged"] = enriched["validation_flag"].fillna("").astype(str).str.strip().ne("")
    enriched["unc_isna"] = enriched["uncertainty"].isna()
    enriched["passes_strict_unc005"] = enriched["uncertainty"].notna() & (enriched["uncertainty"] <= STRICT_UNCERTAINTY_MAX)
    return enriched


def load_aavso_core(root_dir: Path | str | None = None) -> pd.DataFrame:
    root = resolve_root(root_dir)
    df = pd.read_csv(root / AAVSO_RAW_REL, usecols=AAVSO_USECOLS, low_memory=False)
    df.columns = standardize_columns(list(df.columns))
    for column in ("jd", "magnitude", "uncertainty", "hquncertainty", "hjd"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.rename(columns={"magnitude": "mag", "hquncertainty": "hq_uncertainty"})
    for column in ("band", "observer_code", "validation_flag", "measurement_method"):
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()
    df["band"] = df["band"].map(normalize_band).astype("string")
    return df


def load_validcore(root_dir: Path | str | None = None) -> pd.DataFrame:
    root = resolve_root(root_dir)
    path = root / VALIDCORE_REL
    if not path.exists():
        notebook_01_ingest_qc(root)
    return pd.read_parquet(path)


def load_asassn(root_dir: Path | str | None = None) -> pd.DataFrame:
    root = resolve_root(root_dir)
    df = pd.read_csv(root / ASASSN_RAW_REL, usecols=ASASSN_USECOLS)
    df.columns = standardize_columns(list(df.columns))
    for column in ("hjd", "mag", "mag_err", "flux", "flux_err"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def _window(df: pd.DataFrame, start_jd: float, end_jd: float, band: str | None = None) -> pd.DataFrame:
    subset = df.loc[df["jd"].between(start_jd, end_jd, inclusive="both")].copy()
    if band is not None:
        subset = subset.loc[subset["band"] == band].copy()
    return subset.sort_values("jd").reset_index(drop=True)


def _band_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["band", "n_points", "jd_min", "jd_max"])
    grouped = (
        df.dropna(subset=["band"])
        .groupby("band", dropna=False)
        .agg(n_points=("jd", "size"), jd_min=("jd", "min"), jd_max=("jd", "max"))
        .reset_index()
        .sort_values(["n_points", "band"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return grouped


def _filter_summary(df: pd.DataFrame, bands: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for band in bands:
        subset = df.loc[df["band"] == band].copy()
        rows.append(
            {
                "band": band,
                "n_loose": int(len(subset)),
                "n_unc_present": int(subset["uncertainty"].notna().sum()),
                "n_flagged": int(subset["is_flagged"].sum()),
                "n_strict_unc005": int(subset["passes_strict_unc005"].sum()),
                "pct_retained_strict_unc005": float(subset["passes_strict_unc005"].mean() * 100) if len(subset) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def notebook_01_ingest_qc(root_dir: Path | str | None = None) -> dict[str, object]:
    root = resolve_root(root_dir)
    preview = _read_aavso_preview(root)
    df = load_aavso_core(root)

    invalid_jd_mask = df["jd"].isna() | (df["jd"] == 0)
    dropped_jd_null_or_zero = int(invalid_jd_mask.sum())

    after_jd = df.loc[~invalid_jd_mask].copy()
    mag_null_mask = after_jd["mag"].isna()
    dropped_mag_null = int(mag_null_mask.sum())

    validcore = _add_quality_flags(after_jd.loc[~mag_null_mask].copy().sort_values("jd").reset_index(drop=True))
    save_frame(validcore, root / VALIDCORE_REL)

    qc_counts = pd.DataFrame(
        [
            {
                "total_raw": int(len(df)),
                "dropped_jd_null_or_zero": dropped_jd_null_or_zero,
                "dropped_mag_null": dropped_mag_null,
                "remaining_core": int(len(validcore)),
            }
        ]
    )
    save_frame(qc_counts, root / "figures/qc_table_core_counts.csv")

    band_summary = _band_summary(validcore)
    save_frame(band_summary, root / "figures/qc_band_summary.csv")

    _save_lightcurve_scatter(validcore, "V", "AAVSO Raw Scatter: V Band", root / "figures/aavso_raw_V_scatter.png")
    _save_lightcurve_scatter(validcore, "B", "AAVSO Raw Scatter: B Band", root / "figures/aavso_raw_B_scatter.png")
    _save_uncertainty_histogram(validcore, root / "figures/aavso_uncertainty_hist.png")

    uncertainty = validcore["uncertainty"].dropna()
    uncertainty_summary = "\n".join(
        [
            f"total_core_rows: {len(validcore)}",
            f"flagged_rows: {int(validcore['is_flagged'].sum())}",
            f"flagged_pct: {validcore['is_flagged'].mean() * 100:.2f}",
            f"uncertainty_present_rows: {int((~validcore['unc_isna']).sum())}",
            f"uncertainty_missing_rows: {int(validcore['unc_isna'].sum())}",
            f"uncertainty_missing_pct: {validcore['unc_isna'].mean() * 100:.2f}",
            f"strict_unc005_rows: {int(validcore['passes_strict_unc005'].sum())}",
            f"strict_unc005_pct: {validcore['passes_strict_unc005'].mean() * 100:.2f}",
            f"uncertainty_min: {uncertainty.min():.5f}" if not uncertainty.empty else "uncertainty_min: nan",
            f"uncertainty_median: {uncertainty.median():.5f}" if not uncertainty.empty else "uncertainty_median: nan",
            f"uncertainty_max: {uncertainty.max():.5f}" if not uncertainty.empty else "uncertainty_max: nan",
        ]
    )
    write_text(root / "figures/qc_uncertainty_summary.txt", uncertainty_summary + "\n")

    return {
        "n_rows_raw": int(len(df)),
        "columns": list(preview.columns),
        "preview": preview.to_dict(orient="records"),
        "core_counts": qc_counts.to_dict(orient="records")[0],
        "band_summary_head": band_summary.head(10).to_dict(orient="records"),
    }


def notebook_02_windows_export(root_dir: Path | str | None = None) -> dict[str, object]:
    root = resolve_root(root_dir)
    validcore = load_validcore(root)

    modern_v = _window(validcore, MODERN_START_JD, MODERN_END_JD, band="V")
    modern_b = _window(validcore, MODERN_START_JD, MODERN_END_JD, band="B")
    modern_vis = _window(validcore, MODERN_START_JD, MODERN_END_JD, band="Vis")
    vis_1935_1955 = _window(validcore, WINDOW_1946_START_JD, WINDOW_1946_END_JD, band="Vis")
    vis_1860_1870 = _window(validcore, WINDOW_1866_START_JD, WINDOW_1866_END_JD, band="Vis")
    around_1946_v = _window(validcore, WINDOW_1946_START_JD, WINDOW_1946_END_JD, band="V")

    save_frame(modern_v, root / MODERN_V_LOOSE_REL)
    save_frame(modern_b, root / MODERN_B_LOOSE_REL)
    save_frame(modern_vis, root / MODERN_VIS_REL)
    save_frame(vis_1935_1955, root / ALLCYCLES_VIS_1946_RAW_REL)
    save_frame(vis_1860_1870, root / ALLCYCLES_VIS_1866_RAW_REL)
    save_frame(around_1946_v, root / AROUND_1946_V_REL)

    modern_counts = pd.DataFrame(
        [
            {"band": "V", "n_points": int(len(modern_v))},
            {"band": "B", "n_points": int(len(modern_b))},
            {"band": "Vis", "n_points": int(len(modern_vis))},
        ]
    )
    save_frame(modern_counts, root / "figures/window_modern_counts.csv")
    save_frame(_band_summary(_window(validcore, WINDOW_1946_START_JD, WINDOW_1946_END_JD)), root / "figures/window_1946_counts.csv")
    save_frame(_band_summary(_window(validcore, WINDOW_1866_START_JD, WINDOW_1866_END_JD)), root / "figures/window_1866_coverage.csv")

    return {
        "modern_window": {
            "start_jd": MODERN_START_JD,
            "end_jd": MODERN_END_JD,
            "counts": modern_counts.to_dict(orient="records"),
        },
        "historical_vis_window": {
            "start_jd": WINDOW_1946_START_JD,
            "end_jd": WINDOW_1946_END_JD,
            "vis_points": int(len(vis_1935_1955)),
            "v_points": int(len(around_1946_v)),
        },
        "allcycles_1866_vis_window": {
            "start_jd": WINDOW_1866_START_JD,
            "end_jd": WINDOW_1866_END_JD,
            "vis_points": int(len(vis_1860_1870)),
        },
    }


def _bin_lightcurve(
    df: pd.DataFrame,
    time_col: str,
    mag_col: str,
    bin_days: int,
    anchor_jd: float,
) -> pd.DataFrame:
    work = df[[time_col, mag_col]].dropna().copy()
    if work.empty:
        return pd.DataFrame(
            columns=[
                "jd_bin_start",
                "jd_bin_center",
                "bin_days",
                "date_utc",
                "mag_median",
                "n_points",
                "mag_mad",
                "mag_std",
            ]
        )
    work["bin_index"] = np.floor((work[time_col] - anchor_jd) / bin_days).astype(int)
    work["jd_bin_start"] = anchor_jd + (work["bin_index"] * bin_days)
    grouped = work.groupby("jd_bin_start", sort=True)[mag_col]
    binned = grouped.agg(mag_median="median", n_points="size", mag_std="std").reset_index()
    mad = grouped.apply(lambda values: float(np.median(np.abs(values - np.median(values))))).rename("mag_mad")
    binned = binned.merge(mad.reset_index(), on="jd_bin_start", how="left")
    binned["jd_bin_center"] = binned["jd_bin_start"] + (bin_days / 2.0)
    binned["bin_days"] = bin_days
    binned["date_utc"] = pd.to_datetime(binned["jd_bin_center"], unit="D", origin="julian").dt.strftime("%Y-%m-%d")
    ordered = [
        "jd_bin_start",
        "jd_bin_center",
        "bin_days",
        "date_utc",
        "mag_median",
        "n_points",
        "mag_mad",
        "mag_std",
    ]
    return binned.loc[:, ordered].sort_values("jd_bin_start").reset_index(drop=True)


def _with_rollmed(base_binned: pd.DataFrame, window_bins: int) -> pd.DataFrame:
    smoothed = base_binned.copy()
    smoothed["mag_rollmed"] = smoothed["mag_median"].rolling(window=window_bins, center=True, min_periods=1).median()
    smoothed["rollmed_window_bins"] = window_bins
    return smoothed


def _save_lightcurve_scatter(df: pd.DataFrame, band: str, title: str, out_path: Path) -> None:
    subset = df.loc[df["band"] == band, ["jd", "mag"]].dropna().sort_values("jd")
    fig, ax = plt.subplots(figsize=(12, 4))
    if subset.empty:
        ax.text(0.5, 0.5, f"No data for band {band}", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.scatter(subset["jd"], subset["mag"], s=6, alpha=0.28, edgecolors="none", color="#1f4f7a")
        ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel("Julian Date")
    ax.set_ylabel("Magnitude")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _save_uncertainty_histogram(df: pd.DataFrame, out_path: Path) -> None:
    values = df["uncertainty"].dropna()
    fig, ax = plt.subplots(figsize=(8, 4))
    if values.empty:
        ax.text(0.5, 0.5, "No uncertainty values available", ha="center", va="center", transform=ax.transAxes)
    else:
        clipped = values[values.between(values.quantile(0.01), values.quantile(0.99))]
        ax.hist(clipped, bins=40, color="#487a52", alpha=0.85)
    ax.set_title("AAVSO Uncertainty Distribution")
    ax.set_xlabel("Uncertainty")
    ax.set_ylabel("Count")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _plot_raw_vs_binned(raw_df: pd.DataFrame, binned_df: pd.DataFrame, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    if raw_df.empty:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.scatter(raw_df["jd"], raw_df["mag"], s=5, alpha=0.18, edgecolors="none", color="#5a7ca4", label="Raw")
        if not binned_df.empty:
            ax.plot(
                binned_df["jd_bin_center"],
                binned_df["mag_median"],
                color="#d24f45",
                linewidth=1.4,
                label=f"Binned {int(binned_df['bin_days'].iloc[0])}d",
            )
        ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel("Julian Date")
    ax.set_ylabel("Magnitude")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _plot_binned_with_rollmed(base_binned: pd.DataFrame, roll3: pd.DataFrame, roll5: pd.DataFrame, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    if base_binned.empty:
        ax.text(0.5, 0.5, "No binned data available", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.plot(base_binned["jd_bin_center"], base_binned["mag_median"], color="#7393b3", linewidth=1.0, alpha=0.85, label="7d median")
        ax.plot(roll3["jd_bin_center"], roll3["mag_rollmed"], color="#c07a2f", linewidth=1.5, label="Rolling median (3 bins)")
        ax.plot(roll5["jd_bin_center"], roll5["mag_rollmed"], color="#8e2f2f", linewidth=1.8, label="Rolling median (5 bins)")
        ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel("Julian Date")
    ax.set_ylabel("Magnitude")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _plot_loose_vs_strict(loose_binned: pd.DataFrame, strict_binned: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    if loose_binned.empty and strict_binned.empty:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
    else:
        if not loose_binned.empty:
            ax.plot(loose_binned["jd_bin_center"], loose_binned["mag_median"], color="#2f5b88", linewidth=1.6, label="Loose 7d")
        if not strict_binned.empty:
            ax.plot(strict_binned["jd_bin_center"], strict_binned["mag_median"], color="#c54e52", linewidth=1.4, label="Strict 7d (unc <= 0.05)")
        ax.invert_yaxis()
    ax.set_title("Modern V: loose vs strict robustness check")
    ax.set_xlabel("Julian Date")
    ax.set_ylabel("Magnitude")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _plot_allcycles_vis_overlay(vis_1946: pd.DataFrame, vis_2015: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    if vis_1946.empty and vis_2015.empty:
        ax.text(0.5, 0.5, "No all-cycles Vis data available", ha="center", va="center", transform=ax.transAxes)
    else:
        if not vis_1946.empty:
            temp_1946 = vis_1946.copy()
            temp_1946["years_since_window_start"] = (temp_1946["jd_bin_center"] - WINDOW_1946_START_JD) / 365.25
            ax.plot(temp_1946["years_since_window_start"], temp_1946["mag_median"], color="#8d4b32", linewidth=1.6, label="Vis 1935-1955")
        if not vis_2015.empty:
            temp_2015 = vis_2015.copy()
            temp_2015["years_since_window_start"] = (temp_2015["jd_bin_center"] - MODERN_START_JD) / 365.25
            ax.plot(temp_2015["years_since_window_start"], temp_2015["mag_median"], color="#2f6673", linewidth=1.6, label="Vis 2015-2025")
        ax.invert_yaxis()
    ax.set_title("All-cycles Vis comparison on matched 7-day bins")
    ax.set_xlabel("Years Since Window Start")
    ax.set_ylabel("Magnitude")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def notebook_03_binning_smoothing(root_dir: Path | str | None = None) -> dict[str, object]:
    root = resolve_root(root_dir)
    if not (root / MODERN_V_LOOSE_REL).exists():
        notebook_02_windows_export(root)

    modern_v_loose = pd.read_parquet(root / MODERN_V_LOOSE_REL)
    modern_v_strict = modern_v_loose.loc[modern_v_loose["passes_strict_unc005"]].copy().reset_index(drop=True)
    modern_b = pd.read_parquet(root / MODERN_B_LOOSE_REL)
    modern_vis = pd.read_parquet(root / MODERN_VIS_REL)
    vis_1935_1955 = pd.read_parquet(root / ALLCYCLES_VIS_1946_RAW_REL)
    vis_1860_1870 = pd.read_parquet(root / ALLCYCLES_VIS_1866_RAW_REL)

    save_frame(modern_v_strict, root / MODERN_V_STRICT_REL)

    filter_counts = _filter_summary(pd.concat([modern_v_loose, modern_b, modern_vis], ignore_index=True), ["V", "B", "Vis"])
    save_frame(filter_counts, root / "figures/filter_counts_modern_window.csv")

    modern_v_bin1d = _bin_lightcurve(modern_v_loose, "jd", "mag", 1, anchor_jd=MODERN_START_JD)
    modern_v_bin7d = _bin_lightcurve(modern_v_loose, "jd", "mag", 7, anchor_jd=MODERN_START_JD)
    modern_v_roll3 = _with_rollmed(modern_v_bin7d, 3)
    modern_v_roll5 = _with_rollmed(modern_v_bin7d, 5)
    modern_v_strict_bin7d = _bin_lightcurve(modern_v_strict, "jd", "mag", 7, anchor_jd=MODERN_START_JD)

    allcycles_vis_1860_1870_bin7d = _bin_lightcurve(vis_1860_1870, "jd", "mag", 7, anchor_jd=WINDOW_1866_START_JD)
    allcycles_vis_1935_1955_bin7d = _bin_lightcurve(vis_1935_1955, "jd", "mag", 7, anchor_jd=WINDOW_1946_START_JD)
    allcycles_vis_2015_2025_bin7d = _bin_lightcurve(modern_vis, "jd", "mag", 7, anchor_jd=MODERN_START_JD)

    save_frame(modern_v_bin1d, root / MODERN_V_BIN1D_CLEAN_REL)
    save_frame(modern_v_bin7d, root / MODERN_V_BIN7D_CLEAN_REL)
    save_frame(modern_v_roll3, root / MODERN_V_BIN7D_ROLLMED3_CLEAN_REL)
    save_frame(modern_v_roll5, root / MODERN_V_BIN7D_ROLLMED5_CLEAN_REL)
    save_frame(modern_v_strict_bin7d, root / MODERN_V_STRICT_BIN7D_CLEAN_REL)

    save_frame(allcycles_vis_1860_1870_bin7d, root / ALLCYCLES_VIS_1866_BIN7D_CLEAN_REL)
    save_frame(allcycles_vis_1935_1955_bin7d, root / ALLCYCLES_VIS_1946_BIN7D_CLEAN_REL)
    save_frame(allcycles_vis_2015_2025_bin7d, root / ALLCYCLES_VIS_2015_BIN7D_CLEAN_REL)

    _plot_raw_vs_binned(modern_v_loose, modern_v_bin1d, "Modern V raw vs 1-day bin", root / "figures/modern_V_raw_vs_bin1d.png")
    _plot_raw_vs_binned(modern_v_loose, modern_v_bin7d, "Modern V raw vs 7-day bin", root / "figures/modern_V_raw_vs_bin7d.png")
    _plot_binned_with_rollmed(
        modern_v_bin7d,
        modern_v_roll3,
        modern_v_roll5,
        "Modern V 7-day bin with rolling medians",
        root / "figures/modern_V_bin7d_with_rollmed.png",
    )
    _plot_loose_vs_strict(modern_v_bin7d, modern_v_strict_bin7d, root / "figures/modern_V_loose_vs_strict_bin7d.png")
    _plot_allcycles_vis_overlay(
        allcycles_vis_1935_1955_bin7d,
        allcycles_vis_2015_2025_bin7d,
        root / "figures/allcycles_Vis_1935_1955_vs_2015_2025_bin7d_overlay.png",
    )

    return {
        "modern_v": {
            "loose_points": int(len(modern_v_loose)),
            "strict_points_unc005": int(len(modern_v_strict)),
            "bin1d_rows": int(len(modern_v_bin1d)),
            "bin7d_rows": int(len(modern_v_bin7d)),
        },
        "allcycles_vis": {
            "vis_1860_1870_rows": int(len(allcycles_vis_1860_1870_bin7d)),
            "vis_1935_1955_rows": int(len(allcycles_vis_1935_1955_bin7d)),
            "vis_2015_2025_rows": int(len(allcycles_vis_2015_2025_bin7d)),
        },
        "filter_counts": filter_counts.to_dict(orient="records"),
    }


def _plot_overlay(aavso_binned: pd.DataFrame, asassn_binned: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    if aavso_binned.empty and asassn_binned.empty:
        ax.text(0.5, 0.5, "No overlap data available", ha="center", va="center", transform=ax.transAxes)
    else:
        if not aavso_binned.empty:
            ax.plot(aavso_binned["jd_bin_center"], aavso_binned["mag_median"], color="#1f4f7a", linewidth=1.6, label="AAVSO V 7d")
        if not asassn_binned.empty:
            ax.plot(asassn_binned["jd_bin_center"], asassn_binned["mag_median"], color="#b34a3c", linewidth=1.4, label="ASAS-SN V 7d")
        ax.invert_yaxis()
    ax.set_title("AAVSO vs ASAS-SN V-band overlap")
    ax.set_xlabel("Julian Date")
    ax.set_ylabel("Magnitude")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _spearman_corr(left: pd.Series, right: pd.Series) -> float:
    valid = pd.DataFrame({"left": left, "right": right}).dropna()
    if len(valid) < 2:
        return float("nan")
    ranked = valid.rank(method="average")
    return float(ranked["left"].corr(ranked["right"]))


def notebook_04_asassn_crosscheck(root_dir: Path | str | None = None) -> dict[str, object]:
    root = resolve_root(root_dir)
    if not (root / MODERN_V_BIN7D_CLEAN_REL).exists():
        notebook_03_binning_smoothing(root)

    asassn = load_asassn(root).dropna(subset=["hjd", "mag"]).sort_values("hjd").reset_index(drop=True)
    asassn_binned = _bin_lightcurve(asassn.rename(columns={"hjd": "jd"}), "jd", "mag", 7, anchor_jd=MODERN_START_JD)
    aavso_modern_bin7d = pd.read_parquet(root / MODERN_V_BIN7D_CLEAN_REL)

    overlap = aavso_modern_bin7d.merge(
        asassn_binned,
        on="jd_bin_start",
        how="inner",
        suffixes=("_aavso", "_asassn"),
    ).sort_values("jd_bin_start").reset_index(drop=True)
    overlap["delta_mag_asassn_minus_aavso"] = overlap["mag_median_asassn"] - overlap["mag_median_aavso"]

    overlap_start = float(overlap["jd_bin_start"].min()) if not overlap.empty else np.nan
    overlap_end = float(overlap["jd_bin_start"].max()) if not overlap.empty else np.nan

    aavso_overlap = aavso_modern_bin7d.loc[
        aavso_modern_bin7d["jd_bin_start"].isin(overlap["jd_bin_start"])
    ].copy()
    asassn_overlap = asassn_binned.loc[
        asassn_binned["jd_bin_start"].isin(overlap["jd_bin_start"])
    ].copy()
    _plot_overlay(aavso_overlap, asassn_overlap, root / "figures/overlay_aavso_vs_asassn_V_overlap.png")

    delta = overlap["delta_mag_asassn_minus_aavso"].dropna()
    delta_median = float(delta.median()) if not delta.empty else np.nan
    delta_mad = float(np.median(np.abs(delta - np.median(delta)))) if not delta.empty else np.nan
    spearman_corr = _spearman_corr(overlap["mag_median_aavso"], overlap["mag_median_asassn"])

    summary_text = "\n".join(
        [
            f"asassn_points_raw: {len(asassn)}",
            f"asassn_hjd_min: {asassn['hjd'].min():.5f}",
            f"asassn_hjd_max: {asassn['hjd'].max():.5f}",
            f"asassn_bin7d_rows: {len(asassn_binned)}",
            f"overlap_start_jd_bin: {overlap_start:.5f}" if not np.isnan(overlap_start) else "overlap_start_jd_bin: nan",
            f"overlap_end_jd_bin: {overlap_end:.5f}" if not np.isnan(overlap_end) else "overlap_end_jd_bin: nan",
            f"n_overlap_bins: {len(overlap)}",
        ]
    )
    write_text(root / "figures/asassn_qc_counts.txt", summary_text + "\n")

    metrics_text = "\n".join(
        [
            f"n_overlap: {len(overlap)}",
            f"median_delta_mag_asassn_minus_aavso: {delta_median:.6f}" if not np.isnan(delta_median) else "median_delta_mag_asassn_minus_aavso: nan",
            f"mad_delta_mag_asassn_minus_aavso: {delta_mad:.6f}" if not np.isnan(delta_mad) else "mad_delta_mag_asassn_minus_aavso: nan",
            f"spearman_correlation: {spearman_corr:.6f}" if not np.isnan(spearman_corr) else "spearman_correlation: nan",
        ]
    )
    write_text(root / "notes/asassn_vs_aavso_overlap_metrics.txt", metrics_text + "\n")

    return {
        "asassn_rows": int(len(asassn)),
        "asassn_range": [float(asassn["hjd"].min()), float(asassn["hjd"].max())],
        "overlap_bins": int(len(overlap)),
        "median_delta_mag_asassn_minus_aavso": delta_median,
        "mad_delta_mag_asassn_minus_aavso": delta_mad,
        "spearman_correlation": spearman_corr,
    }


def write_decisions(root_dir: Path | str | None = None) -> None:
    root = resolve_root(root_dir)
    content = """# Decisions

- Core invalid rows are dropped only when `JD` is null/0 or `Magnitude` is null.
- Validation-flagged AAVSO rows are retained in the base dataset and tracked with `is_flagged`.
- Loose filtering keeps all core-valid rows and tracks missing uncertainty with `unc_isna`.
- Strict filtering is used only as a robustness check and currently means `Uncertainty` is present and `<= 0.05`.
- The pipeline is split into two lanes: `modern V` for signal-rich modern analysis and `all-cycles Vis` for cross-cycle consistency.
- Modern `V` products are generated on shared 1-day and 7-day bins, plus 3-bin and 5-bin rolling medians on the 7-day series.
- A shared 7-day grid anchored at `JD` 2457023.5 is used for modern `V` and the AAVSO-vs-ASAS-SN overlap comparison.
- For cross-cycle work, `Vis` is the design choice rather than an ad hoc fallback.
- AAVSO coverage in 1935-1955 is effectively `Vis`-only; `V` is not available in a usable amount there, so historical lane products are defined as `Vis` by design.
- Early-cycle context uses `Vis` coverage from 1860-01-01 to 1870-12-31.
- ASAS-SN is compared against AAVSO using `HJD ~= JD` as a first-pass approximation, and overlap metrics are computed from directly merged 7-day bins.
- ZTF raw download is preserved under `data/raw/`, but skipped because the file content is an HTML 504 error page.
"""
    write_text(root / "notes/decisions.md", content)


def write_raw_image_guide(root_dir: Path | str | None = None) -> None:
    root = resolve_root(root_dir)
    if not (root / VALIDCORE_REL).exists():
        notebook_01_ingest_qc(root)
    if not (root / MODERN_V_BIN7D_CLEAN_REL).exists():
        notebook_03_binning_smoothing(root)
    if not (root / "notes/asassn_vs_aavso_overlap_metrics.txt").exists():
        notebook_04_asassn_crosscheck(root)

    qc_counts = pd.read_csv(root / "figures/qc_table_core_counts.csv").iloc[0]
    filter_counts = pd.read_csv(root / "figures/filter_counts_modern_window.csv")
    overlap_metrics = (root / "notes/asassn_vs_aavso_overlap_metrics.txt").read_text(encoding="utf-8").strip().splitlines()

    modern_v = filter_counts.loc[filter_counts["band"] == "V"].iloc[0]
    modern_b = filter_counts.loc[filter_counts["band"] == "B"].iloc[0]
    modern_vis = filter_counts.loc[filter_counts["band"] == "Vis"].iloc[0]

    content = f"""# Raw Image Guide

Dokumen ini mencatat provenance dan cara baca figure PNG quick-look yang dihasilkan pipeline T CrB. Fokusnya adalah diagnostic images berbasis raw atau near-raw products, bukan figure final untuk publikasi.

## Current Snapshot

- Raw AAVSO file: `{AAVSO_RAW_REL}` dengan `753656` rows pada download saat ini.
- Core-valid AAVSO dataset: `{VALIDCORE_REL}` dengan `{int(qc_counts["remaining_core"])}` rows setelah drop `JD` null/0 dan `Magnitude` null.
- Modern `V` loose vs strict: `{int(modern_v["n_loose"])}` vs `{int(modern_v["n_strict_unc005"])}` rows, dengan strict = `Uncertainty <= {STRICT_UNCERTAINTY_MAX:.2f}`.
- Modern `B` snapshot: `{int(modern_b["n_loose"])}` loose rows, `{int(modern_b["n_strict_unc005"])}` strict rows.
- Modern `Vis` snapshot: `{int(modern_vis["n_loose"])}` loose rows; strict count tetap `0` karena uncertainty hampir selalu tidak tersedia di lane ini.
- AAVSO vs ASAS-SN overlap metrics saat ini:
  - `{overlap_metrics[0]}`
  - `{overlap_metrics[1]}`
  - `{overlap_metrics[2]}`
  - `{overlap_metrics[3]}`

## Figure Inventory

- `figures/aavso_raw_V_scatter.png`
  - Dibuat oleh `notebook_01_ingest_qc()`.
  - Input: core-valid `V` rows dari `{VALIDCORE_REL}`.
  - Makna: sebaran observasi AAVSO `V` terhadap `JD` sebelum binning modern lane.

- `figures/aavso_raw_B_scatter.png`
  - Dibuat oleh `notebook_01_ingest_qc()`.
  - Input: core-valid `B` rows dari `{VALIDCORE_REL}`.
  - Makna: sanity-check coverage dan noise visual pada band `B`.

- `figures/aavso_uncertainty_hist.png`
  - Dibuat oleh `notebook_01_ingest_qc()`.
  - Input: kolom `uncertainty` non-null dari `{VALIDCORE_REL}`.
  - Makna: distribusi uncertainty AAVSO setelah clipping ke quantile 1%–99% agar ekor ekstrem tidak mendominasi histogram.

- `figures/modern_V_raw_vs_bin1d.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input raw: `{MODERN_V_LOOSE_REL}`.
  - Input binned: `{MODERN_V_BIN1D_CLEAN_REL}`.
  - Makna: raw modern `V` dibanding median bin 1 hari pada anchor grid modern yang sama.

- `figures/modern_V_raw_vs_bin7d.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input raw: `{MODERN_V_LOOSE_REL}`.
  - Input binned: `{MODERN_V_BIN7D_CLEAN_REL}`.
  - Makna: versi 7 hari dari figure di atas; ini quick-look utama untuk melihat sinyal yang lebih stabil.

- `figures/modern_V_bin7d_with_rollmed.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input: `{MODERN_V_BIN7D_CLEAN_REL}`, `{MODERN_V_BIN7D_ROLLMED3_CLEAN_REL}`, `{MODERN_V_BIN7D_ROLLMED5_CLEAN_REL}`.
  - Makna: perbandingan median 7 hari dengan rolling median 3-bin dan 5-bin.

- `figures/modern_V_loose_vs_strict_bin7d.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input: `{MODERN_V_BIN7D_CLEAN_REL}` dan `{MODERN_V_STRICT_BIN7D_CLEAN_REL}`.
  - Makna: robustness check untuk melihat dampak threshold strict uncertainty.

- `figures/allcycles_Vis_1935_1955_vs_2015_2025_bin7d_overlay.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input: `{ALLCYCLES_VIS_1946_BIN7D_CLEAN_REL}` dan `{ALLCYCLES_VIS_2015_BIN7D_CLEAN_REL}`.
  - Makna: overlay lane `all-cycles Vis` untuk konsistensi lintas siklus.

- `figures/overlay_aavso_vs_asassn_V_overlap.png`
  - Dibuat oleh `notebook_04_asassn_crosscheck()`.
  - Input: `{MODERN_V_BIN7D_CLEAN_REL}` dan hasil binning 7 hari ASAS-SN dari `{ASASSN_RAW_REL}`.
  - Makna: cross-check modern `V` AAVSO vs ASAS-SN pada grid 7 hari yang sama.

## Interpretation Rules

- Semua light-curve figure memakai magnitude axis terbalik; nilai magnitudo lebih kecil berarti bintang lebih terang.
- Figure `raw` memakai core-valid rows, bukan subset strict. Artinya row ber-flag validasi tetap ikut tampil sebagai bagian dari data dasar.
- Lane `1935–1955` dan `1860–1870` sengaja memakai `Vis`; ini keputusan desain pipeline, bukan fallback sementara.
- Figure overlap ASAS-SN memakai pendekatan `HJD ~= JD` sebagai first-pass comparison; pakai untuk cross-check, bukan kalibrasi absolut.
- File raw ZTF tetap disimpan di `{ZTF_RAW_REL}`, tetapi tidak dipakai karena isi unduhannya adalah halaman HTML `504`.

## Regeneration

- Jalankan `run_all()` untuk rebuild artefak utama dan perbarui `notes/decisions.md`.
- Jalankan `write_raw_image_guide()` untuk me-refresh dokumen ini setelah figure atau metrik berubah.
- Untuk verifikasi notebook, gunakan `jupyter nbconvert --to notebook --execute notebooks/02_windows_export.ipynb` dan analog untuk notebook `03` serta `04`.
"""
    write_text(root / RAW_IMAGE_GUIDE_REL, content)


def run_all(root_dir: Path | str | None = None) -> dict[str, object]:
    root = resolve_root(root_dir)
    write_decisions(root)
    results = {
        "notebook_01": notebook_01_ingest_qc(root),
        "notebook_02": notebook_02_windows_export(root),
        "notebook_03": notebook_03_binning_smoothing(root),
        "notebook_04": notebook_04_asassn_crosscheck(root),
    }
    write_raw_image_guide(root)
    return results
