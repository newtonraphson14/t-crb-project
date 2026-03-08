# Raw Image Assets

Berikut asset raw/reference image T CrB yang sudah benar-benar diunduh ke repo.

## Downloaded on 2026-03-07

### Legacy Survey DR10

- FITS: `data/raw_images/reference/legacy/tcrb_legacy_lsdr10_ref_griz_cutout.fits`
- JPEG: `data/raw_images/reference/legacy/tcrb_legacy_lsdr10_ref_rgb_cutout.jpg`
- Manifest: `data/raw_images/reference/legacy/manifest_legacy.csv`
- Keterangan:
  - cutout berpusat di koordinat T CrB
  - ukuran `256 x 256`
  - layer `ls-dr10`
  - ini adalah reference image modern, bukan time-series per tahun

### Pan-STARRS PS1

- FITS: `data/raw_images/reference/ps1/tcrb_ps1_ref_i_cutout.fits`
- JPEG: `data/raw_images/reference/ps1/tcrb_ps1_ref_i_cutout.jpg`
- Manifest: `data/raw_images/reference/ps1/manifest_ps1.csv`
- Keterangan:
  - cutout `i`-band berpusat di koordinat T CrB
  - ukuran `256 x 256`
  - ini adalah reference image modern, bukan time-series per tahun

### Pan-STARRS PS1 single-epoch timeline

- `i`-band timeline FITS/JPEG:
  - folder: `data/raw_images/reference/ps1/timeline_i/`
  - manifest: `data/raw_images/reference/ps1/timeline_i/manifest_ps1_timeline_i.csv`
- `r`-band timeline FITS/JPEG:
  - folder: `data/raw_images/reference/ps1/timeline_r/`
  - manifest: `data/raw_images/reference/ps1/timeline_r/manifest_ps1_timeline_r.csv`
- Panel PNG hasil stitch:
  - `figures/raw_images/modern_panels/tcrb_ps1_i_timeline.png`
  - `figures/raw_images/modern_panels/tcrb_ps1_r_timeline.png`
- Catatan:
  - panel `r`-band saat ini adalah versi progresif paling informatif
  - panel `i`-band tetap disimpan sebagai alternatif karena coverage tahunnya lebih panjang
  - ini memberi mini progressive image lane nyata untuk epoch PS1 sekitar `2010–2014`

## Downloaded on 2026-03-08

### DASCH DR7 historical proof-of-concept

- FITS gzip: `data/raw_images/dasch/tcrb_dasch_ai38245_1943-07-01_sol0_cutout.fits.gz`
- Query CSV: `data/raw_images/dasch/queryexps_1935-01-01_1955-12-31.csv`
- Manifest: `data/raw_images/dasch/manifest_dasch.csv`
- Catatan:
  - ini adalah unduhan live pertama yang benar-benar lolos end-to-end dari DASCH DR7 public API
  - epoch terpilih berada di lane historical `1935–1955`
  - ukuran cutout mengikuti default server DR7, bukan parameter local custom

## Combined manifests

- Combined manifest: `data/raw_images/reference/manifest_reference.csv`
- JSON summary: `notes/raw_image_reference_downloads.json`

## Important scope note

- Asset di atas membuktikan bahwa pipeline sekarang sudah punya `raw image` nyata untuk T CrB.
- Asset ini sekarang mencakup `reference cutouts`, mini `progressive image timeline` berbasis PS1 warp single-epoch, dan satu live historical cutout dari `DASCH`.
- Historical lane sekarang sudah punya proof-of-concept nyata dari `DASCH`.
- Untuk timeline modern yang lebih nyambung dengan lane `modern V`, langkah berikutnya adalah ingest `ZTF` single-epoch cutouts.
- Repo sekarang sudah punya template ingest lokal untuk keduanya di `notes/raw_image_batch_specs/`, sehingga batch yang diunduh manual bisa langsung distage ke `data/raw_images/` dan dibangun panel quick-look-nya.

## Quick open

- `data/raw_images/reference/legacy/tcrb_legacy_lsdr10_ref_rgb_cutout.jpg`
- `data/raw_images/reference/ps1/tcrb_ps1_ref_i_cutout.jpg`
- `data/raw_images/dasch/tcrb_dasch_ai38245_1943-07-01_sol0_cutout.fits.gz`
- `figures/raw_images/modern_panels/tcrb_ps1_r_timeline.png`
