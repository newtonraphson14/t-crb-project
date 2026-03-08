# Raw Image Figures

Folder ini untuk output figure berbasis image, bukan light curve.

Subfolder yang disarankan:

- `qc/`
- `historical_panels/`
- `modern_panels/`
- `animations/`

Contoh deliverable:

- panel historical DASCH proof-of-concept
- panel historical DASCH `1935–1955`
- panel modern ZTF untuk epoch penting
- GIF timeline setelah alignment dan QC cukup stabil

Rencana struktur dan source mapping ada di `notes/raw_image_pipeline_map.md`.

Panel baru dari batch DASCH / ZTF bisa dibangun lewat `fetch_raw_images.py --skip-reference --stage-spec ...` selama batch menyertakan JPEG/PNG dengan `panel_include: true`.
