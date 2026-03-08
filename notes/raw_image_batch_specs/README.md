# Raw Image Batch Specs

Folder ini berisi template JSON untuk ingest asset image yang sudah diunduh manual dari arsip eksternal ke struktur repo T CrB.

Tujuannya:

- mendaftarkan asset DASCH / ZTF ke `data/raw_images/`
- menulis manifest CSV dengan schema yang konsisten
- membangun panel quick-look bila batch menyertakan JPEG/PNG yang diberi `panel_include: true`

Workflow:

1. Salin salah satu file `*_example.json` lalu edit `source_path` agar menunjuk ke file yang benar-benar ada di mesin lokal.
2. Sesuaikan `date_obs`, `jd_mid`, `band_or_emulsion`, dan metadata lain.
3. Jalankan:

```bash
./.venv/bin/python fetch_raw_images.py --skip-reference --stage-spec notes/raw_image_batch_specs/dasch_1935_1955_example.json
```

atau:

```bash
./.venv/bin/python fetch_raw_images.py --skip-reference --stage-spec notes/raw_image_batch_specs/ztf_2018_2025_example.json
```

Catatan:

- Script ini tidak mengunduh DASCH / ZTF langsung dari internet.
- Script ini meng-copy asset lokal ke lokasi repo yang sudah distandardisasi, lalu menulis manifest dan panel.
- Untuk menjaga provenance, isi `url` dengan link query/download asal bila tersedia.
