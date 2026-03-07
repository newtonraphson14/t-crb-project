# T CrB Pipeline

Analysis and artifact pipeline for T Coronae Borealis (`T CrB`) built around two complementary lanes:

- `modern V` for signal-rich modern analysis
- `all-cycles Vis` for cross-cycle consistency

The repo contains cleaned tabular products, figures, notebooks, and a first raw-image lane for T CrB reference / single-epoch cutouts.

## Current status

- Core photometry pipeline implemented in `tcrb_processing.py`
- Notebook flow `01` to `04` aligned with the current pipeline
- Modern `V` exports and smoothing products generated
- Cross-cycle `Vis` products generated
- AAVSO vs ASAS-SN overlap cross-check generated
- Raw-image reference assets and a small PS1 progressive panel added

## Main outputs

### Modern `V`

- `data/clean/modern_V_2015_2025_bin1d.parquet`
- `data/clean/modern_V_2015_2025_bin7d.parquet`
- `data/clean/modern_V_2015_2025_bin7d_rollmed3.parquet`
- `data/clean/modern_V_2015_2025_bin7d_rollmed5.parquet`
- `data/clean/modern_V_2015_2025_strict_unc005_bin7d.parquet`

### Cross-cycle `Vis`

- `data/clean/allcycles_Vis_1860_1870_bin7d.parquet`
- `data/clean/allcycles_Vis_1935_1955_bin7d.parquet`
- `data/clean/allcycles_Vis_2015_2025_bin7d.parquet`

### Figures

- `figures/modern_V_loose_vs_strict_bin7d.png`
- `figures/modern_V_bin7d_with_rollmed.png`
- `figures/allcycles_Vis_1935_1955_vs_2015_2025_bin7d_overlay.png`
- `figures/overlay_aavso_vs_asassn_V_overlap.png`
- `figures/raw_images/modern_panels/tcrb_ps1_r_timeline.png`

## Key numbers

- Modern `V` loose: `174872`
- Modern `V` strict (`unc <= 0.05`): `157810`
- AAVSO vs ASAS-SN overlap bins: `71`
- Median delta (`ASAS-SN - AAVSO`): about `-0.019 mag`
- MAD delta: about `0.052 mag`
- Spearman correlation: about `0.883`

## Repo layout

- `tcrb_processing.py` — main photometry pipeline and artifact writers
- `fetch_raw_images.py` — downloader for reference / PS1 single-epoch image assets
- `notebooks/` — notebook wrappers for each pipeline stage
- `data/` — raw, interim, clean, and image assets
- `figures/` — plots, summaries, and image panels
- `notes/` — design decisions, image notes, and provenance records

## Quickstart

Assuming the local virtual environment already exists:

```bash
cd "/home/ikbarfaiz/Astrophysics Project/T CrB Projects"
./.venv/bin/python -c "from tcrb_processing import run_all; run_all('.')"
./.venv/bin/python fetch_raw_images.py
```

To verify notebooks:

```bash
./.venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/02_windows_export.ipynb
./.venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/03_binning_smoothing.ipynb
./.venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/04_asassn_crosscheck.ipynb
```

## Important notes

- The full raw AAVSO CSV is expected at `data/raw/aavso_tcrb_raw_fullrange.csv`.
- That file is intentionally not tracked in git because it exceeds GitHub's 100 MB file limit.
- Download / provenance notes are recorded in `tcrb_data_download_record.md`.
- Pipeline decisions are recorded in `notes/decisions.md`.

## Raw image lane

The repo now includes:

- Legacy Survey reference cutouts
- PS1 reference cutouts
- PS1 single-epoch warp cutouts
- a first stitched modern panel: `figures/raw_images/modern_panels/tcrb_ps1_r_timeline.png`

See:

- `notes/raw_image_assets.md`
- `notes/raw_image_pipeline_map.md`
- `notes/raw_image_guide.md`

## Acknowledgment note

This project uses public astronomy data products and archives including AAVSO, ASAS-SN, Pan-STARRS, and Legacy Survey.
