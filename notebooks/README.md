# Notebooks

Notebook sequence:

- `01_ingest_qc.ipynb` — load raw AAVSO data, build `validcore`, and export QC summaries
- `02_windows_export.ipynb` — export modern and historical windows
- `03_binning_smoothing.ipynb` — generate binned products, rolling medians, and overlay figures
- `04_asassn_crosscheck.ipynb` — compare modern AAVSO `V` against ASAS-SN on the shared 7-day grid

These notebooks are thin wrappers around functions in `tcrb_processing.py`, so the Python module is the source of truth for reproducible outputs.
