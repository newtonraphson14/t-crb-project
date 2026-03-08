# Raw Image Guide

Dokumen ini mencatat provenance dan cara baca figure PNG quick-look yang dihasilkan pipeline T CrB. Fokusnya adalah diagnostic images berbasis raw atau near-raw products, bukan figure final untuk publikasi.

## Current Snapshot

- Raw AAVSO file: `data/raw/aavso_tcrb_raw_fullrange.csv` dengan `753656` rows pada download saat ini.
- Core-valid AAVSO dataset: `data/interim/aavso_tcrb_validcore.parquet` dengan `749410` rows setelah drop `JD` null/0 dan `Magnitude` null.
- Modern `V` loose vs strict: `174872` vs `157810` rows, dengan strict = `Uncertainty <= 0.05`.
- Modern `B` snapshot: `162889` loose rows, `117593` strict rows.
- Modern `Vis` snapshot: `26807` loose rows; strict count tetap `0` karena uncertainty hampir selalu tidak tersedia di lane ini.
- AAVSO vs ASAS-SN overlap metrics saat ini:
  - `n_overlap: 71`
  - `median_delta_mag_asassn_minus_aavso: -0.019000`
  - `mad_delta_mag_asassn_minus_aavso: 0.052000`
  - `spearman_correlation: 0.882985`

## Figure Inventory

- `figures/aavso_raw_V_scatter.png`
  - Dibuat oleh `notebook_01_ingest_qc()`.
  - Input: core-valid `V` rows dari `data/interim/aavso_tcrb_validcore.parquet`.
  - Makna: sebaran observasi AAVSO `V` terhadap `JD` sebelum binning modern lane.

- `figures/aavso_raw_B_scatter.png`
  - Dibuat oleh `notebook_01_ingest_qc()`.
  - Input: core-valid `B` rows dari `data/interim/aavso_tcrb_validcore.parquet`.
  - Makna: sanity-check coverage dan noise visual pada band `B`.

- `figures/aavso_uncertainty_hist.png`
  - Dibuat oleh `notebook_01_ingest_qc()`.
  - Input: kolom `uncertainty` non-null dari `data/interim/aavso_tcrb_validcore.parquet`.
  - Makna: distribusi uncertainty AAVSO setelah clipping ke quantile 1%–99% agar ekor ekstrem tidak mendominasi histogram.

- `figures/modern_V_raw_vs_bin1d.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input raw: `data/interim/modern_V_2015_2025_loose.parquet`.
  - Input binned: `data/clean/modern_V_2015_2025_bin1d.parquet`.
  - Makna: raw modern `V` dibanding median bin 1 hari pada anchor grid modern yang sama.

- `figures/modern_V_raw_vs_bin7d.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input raw: `data/interim/modern_V_2015_2025_loose.parquet`.
  - Input binned: `data/clean/modern_V_2015_2025_bin7d.parquet`.
  - Makna: versi 7 hari dari figure di atas; ini quick-look utama untuk melihat sinyal yang lebih stabil.

- `figures/modern_V_bin7d_with_rollmed.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input: `data/clean/modern_V_2015_2025_bin7d.parquet`, `data/clean/modern_V_2015_2025_bin7d_rollmed3.parquet`, `data/clean/modern_V_2015_2025_bin7d_rollmed5.parquet`.
  - Makna: perbandingan median 7 hari dengan rolling median 3-bin dan 5-bin.

- `figures/modern_V_loose_vs_strict_bin7d.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input: `data/clean/modern_V_2015_2025_bin7d.parquet` dan `data/clean/modern_V_2015_2025_strict_unc005_bin7d.parquet`.
  - Makna: robustness check untuk melihat dampak threshold strict uncertainty.

- `figures/allcycles_Vis_1935_1955_vs_2015_2025_bin7d_overlay.png`
  - Dibuat oleh `notebook_03_binning_smoothing()`.
  - Input: `data/clean/allcycles_Vis_1935_1955_bin7d.parquet` dan `data/clean/allcycles_Vis_2015_2025_bin7d.parquet`.
  - Makna: overlay lane `all-cycles Vis` untuk konsistensi lintas siklus.

- `figures/overlay_aavso_vs_asassn_V_overlap.png`
  - Dibuat oleh `notebook_04_asassn_crosscheck()`.
  - Input: `data/clean/modern_V_2015_2025_bin7d.parquet` dan hasil binning 7 hari ASAS-SN dari `data/raw/asassn_tcrb_vband_raw.csv`.
  - Makna: cross-check modern `V` AAVSO vs ASAS-SN pada grid 7 hari yang sama.

## Interpretation Rules

- Semua light-curve figure memakai magnitude axis terbalik; nilai magnitudo lebih kecil berarti bintang lebih terang.
- Figure `raw` memakai core-valid rows, bukan subset strict. Artinya row ber-flag validasi tetap ikut tampil sebagai bagian dari data dasar.
- Lane `1935–1955` dan `1860–1870` sengaja memakai `Vis`; ini keputusan desain pipeline, bukan fallback sementara.
- Figure overlap ASAS-SN memakai pendekatan `HJD ~= JD` sebagai first-pass comparison; pakai untuk cross-check, bukan kalibrasi absolut.
- File raw ZTF tetap disimpan di `data/raw/ztf_tcrb_lightcurve_raw.csv`, tetapi tidak dipakai karena isi unduhannya adalah halaman HTML `504`.
- Raw-image downloader terpisah di `fetch_raw_images.py` sekarang bisa query DASCH dan ZTF tanpa bergantung pada file light-curve raw ZTF di atas.

## Regeneration

- Jalankan `run_all()` untuk rebuild artefak utama dan perbarui `notes/decisions.md`.
- Jalankan `write_raw_image_guide()` untuk me-refresh dokumen ini setelah figure atau metrik berubah.
- Untuk verifikasi notebook, gunakan `jupyter nbconvert --to notebook --execute notebooks/02_windows_export.ipynb` dan analog untuk notebook `03` serta `04`.
- Untuk asset image DASCH / ZTF yang sudah diunduh manual, stage dulu batch-nya dengan `fetch_raw_images.py --skip-reference --stage-spec <spec.json>` memakai template di `notes/raw_image_batch_specs/`.
- Untuk unduhan live historical lane, jalankan `fetch_raw_images.py --skip-reference --download-dasch`.
- Untuk unduhan live modern lane, mulai aman dengan `fetch_raw_images.py --skip-reference --download-ztf --dry-run`.
