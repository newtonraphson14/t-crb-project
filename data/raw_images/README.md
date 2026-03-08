# Raw Images

Folder ini disiapkan untuk arsip image mentah T CrB.

Subfolder yang dipakai:

- `dasch/` untuk DASCH historical cutouts / mosaics / metadata
- `applause/` untuk APPLAUSE scans / previews / metadata
- `ztf/` untuk ZTF science/reference cutouts
- `reference/` untuk PS1 / Legacy cutouts yang sifatnya anchor visual

Setiap source sebaiknya punya manifest CSV sendiri, misalnya:

- `manifest_dasch.csv`
- `manifest_applause.csv`
- `manifest_ztf.csv`

Blueprint lengkap ada di `notes/raw_image_pipeline_map.md`.

Jika asset DASCH atau ZTF sudah diunduh manual, gunakan template batch spec di `notes/raw_image_batch_specs/` lalu stage ke repo dengan `fetch_raw_images.py --skip-reference --stage-spec ...`.

Untuk unduhan live:

- DASCH: `fetch_raw_images.py --skip-reference --download-dasch`
- ZTF: `fetch_raw_images.py --skip-reference --download-ztf --dry-run`
