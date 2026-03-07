# Raw Image Pipeline Map

Dokumen ini memetakan sumber arsip image yang realistis untuk T CrB ke struktur pipeline proyek saat ini. Fokusnya adalah menyelaraskan lane image dengan lane fotometri yang sudah ada, bukan mengganti pipeline fotometri utama.

## Alignment with Current Pipeline

- `modern V` tetap menjadi lane analisis utama untuk epoch modern.
  - Sumber image utama: `ZTF` untuk time-series modern.
  - Sumber reference: `PS1` dan `Legacy Survey` untuk cutout modern yang lebih bersih / lebih dalam.
- `all-cycles Vis` tetap menjadi lane lintas-siklus untuk konteks historis.
  - Sumber image utama: `DASCH DR7` untuk plate cutouts/postage stamps dan plate mosaics.
  - Sumber pendamping: `APPLAUSE DR4` bila perlu cek scan plate, preview, atau coverage tambahan.
- Window `1860-01-01` sampai `1870-12-31` tidak diberi default image lane.
  - Alasan: arsip photographic digital yang praktis dipakai baru mulai jauh sesudah 1866.
  - `DASCH` mencakup sekitar `1880–1990`; `APPLAUSE DR4` menyebut plate tertua dari `1893`.

## Source-to-Lane Mapping

| Source | Pipeline lane | Window paling cocok | Peran |
| --- | --- | --- | --- |
| DASCH DR7 | `all-cycles Vis` | `1935-01-01` s/d `1955-12-31` | historical cutouts, plate-level context, long-baseline image checks |
| APPLAUSE DR4 | `all-cycles Vis` companion | `1935-01-01` s/d `1955-12-31` | cadangan / pelengkap historical plates dan logbook-linked scans |
| ZTF | `modern V` | efektif `2018+` di dalam window `2015-01-01` s/d `2025-12-31` | modern single-epoch science cutouts dan reference cutouts |
| PS1 | `modern V` reference | snapshot modern | reference cutout modern berkualitas baik |
| Legacy Survey | `modern V` reference | snapshot modern | reference RGB/FITS cutouts untuk visual context |

## Folder Contract

Struktur yang disarankan:

```text
data/
  raw_images/
    dasch/
    applause/
    ztf/
    reference/
  interim_images/
    aligned/
    normalized/
    reprojected/
    masks/
  clean_images/
    historical_1935_1955/
    modern_2015_2025/
    reference/
figures/
  raw_images/
    qc/
    historical_panels/
    modern_panels/
    animations/
notes/
  raw_image_pipeline_map.md
```

## Raw Layer Rules

### `data/raw_images/dasch`

- Isi dengan file hasil unduhan DASCH mentah:
  - postage stamp / cutout FITS
  - plate mosaic FITS bila diperlukan
  - metadata query / exposure list
- Simpan manifest per batch:
  - `manifest_dasch.csv`
- Nama file yang disarankan:
  - `tcrb_dasch_<plate_or_exposure_id>_<epoch_label>_<product>.fits`

### `data/raw_images/applause`

- Isi dengan produk plate archive mentah:
  - plate preview
  - scan image
  - metadata export
- Simpan manifest:
  - `manifest_applause.csv`
- Pakai hanya sebagai companion historical lane, bukan primary lane bila DASCH sudah cukup.

### `data/raw_images/ztf`

- Isi dengan produk ZTF mentah:
  - science image cutout
  - reference image cutout
  - metadata query response
- Pisahkan raw science vs reference di nama file:
  - `tcrb_ztf_<obsdate>_<filter>_sci.fits`
  - `tcrb_ztf_<obsdate>_<filter>_ref.fits`
- Simpan manifest:
  - `manifest_ztf.csv`

### `data/raw_images/reference`

- Isi dengan cutout snapshot non-time-series:
  - `ps1/`
  - `legacy/`
- Gunakan sebagai anchor visual, bukan sebagai seri temporal utama.

## Interim Layer Rules

### `data/interim_images/aligned`

- Semua source image yang sudah di-align ke cutout center T CrB yang sama.
- Gunakan naming:
  - `tcrb_<source>_<epoch_label>_<band>_aligned.fits`

### `data/interim_images/reprojected`

- Produk yang sudah diproyeksikan ke WCS target yang sama.
- Ini penting agar DASCH, APPLAUSE, dan ZTF bisa dibandingkan panel-to-panel.

### `data/interim_images/normalized`

- Image yang sudah dinormalisasi untuk display:
  - percentile stretch
  - zscale / asinh stretch
  - background-normalized PNG

### `data/interim_images/masks`

- Simpan star mask, bad-pixel mask, atau footprint mask bila perlu.

## Clean Layer Rules

### `data/clean_images/historical_1935_1955`

- Produk final historical image lane.
- Unit kerja utama:
  - 1 representative cutout per chosen epoch
  - small panel sequences, bukan yearly cadence penuh
- Naming:
  - `tcrb_hist_<source>_<epoch_label>_<band>_clean.png`

### `data/clean_images/modern_2015_2025`

- Produk final modern image lane.
- Unit kerja utama:
  - ZTF representative epochs
  - optional monthly/seasonal picks, bukan semua exposure
- Naming:
  - `tcrb_modern_<source>_<epoch_label>_<band>_clean.png`

### `data/clean_images/reference`

- Snapshot modern/reference yang dipakai berulang dalam figure lain.

## Figure Output Rules

### `figures/raw_images/qc`

- Untuk diagnostic plot image pipeline:
  - footprint coverage
  - source count per epoch
  - rejected image count
  - cutout-center sanity checks

### `figures/raw_images/historical_panels`

- Panel historical untuk `1935–1955`.
- Format yang disarankan:
  - 4–8 epoch pilihan
  - label sumber + tanggal + orientasi

### `figures/raw_images/modern_panels`

- Panel modern untuk epoch penting `ZTF`.
- Cocok buat dibandingkan dengan `modern V` light-curve features.

### `figures/raw_images/animations`

- GIF/MP4 timeline jika nanti quality dan alignment cukup baik.
- Jangan dijadikan deliverable utama sebelum panel statis lulus QC.

## Minimal Manifest Schema

Setiap source sebaiknya punya manifest CSV dengan kolom minimum:

- `source`
- `product_type`
- `file_name`
- `date_obs`
- `jd_mid`
- `ra_deg`
- `dec_deg`
- `band_or_emulsion`
- `exptime_s`
- `pixel_scale_arcsec`
- `wcs_status`
- `notes`

## Recommended Build Order

1. `DASCH` historical proof-of-concept untuk `1935–1955`
2. `ZTF` modern proof-of-concept untuk beberapa epoch `2018+`
3. `PS1` reference cutout sebagai anchor modern
4. `APPLAUSE` hanya jika DASCH historical coverage kurang atau perlu cross-check plate scans

## Expected Relationship to Existing Artifacts

- `figures/allcycles_Vis_1935_1955_vs_2015_2025_bin7d_overlay.png`
  - dipasangkan dengan panel `historical_panels/` untuk memberi konteks visual lintas siklus
- `figures/modern_V_raw_vs_bin7d.png`
  - dipasangkan dengan panel `modern_panels/` berbasis ZTF
- `notes/raw_image_guide.md`
  - tetap menjadi guide figure quick-look yang sudah ada
- `notes/raw_image_pipeline_map.md`
  - menjadi blueprint untuk lane image yang belum diunduh

## External Source Notes

- `DASCH DR7`: mencakup data sekitar `1880–1990`, menyediakan lightcurves, cutouts/postage stamps, plate-level photometry, dan calibrated plate mosaics.
  - `https://dasch.cfa.harvard.edu/dr7/`
  - `https://dasch.cfa.harvard.edu/dr7/data-products/`
  - `https://dasch.cfa.harvard.edu/data-access/`
- `APPLAUSE DR4`: plate archive dengan image/scans/query interface; halaman DR4 menyebut plate tertua dari `1893`.
  - `https://www.plate-archive.org/`
- `ZTF via IRSA`: API image archive mendukung query metadata dan retrieval raw/science/calibration/reference/deep reference products.
  - `https://irsa.ipac.caltech.edu/docs/program_interface/ztf_api.html`
- `PS1 Cutout Service`: menyediakan stack images dan single-epoch warp images serta FITS/FITS-cutout links.
  - `https://outerspace.stsci.edu/display/PANSTARRS/PS1+Image+Cutout+Service`
- `Legacy Survey Viewer URLs`: mendokumentasikan JPEG/FITS cutouts dan single-image services.
  - `https://www.legacysurvey.org/viewer/urls`
