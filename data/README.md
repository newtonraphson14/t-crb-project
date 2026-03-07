# Data

Data products are split into four layers:

- `raw/` — raw survey files used by the photometry pipeline
- `interim/` — filtered or windowed products before final packaging
- `clean/` — main analysis-ready tabular outputs
- `raw_images/`, `interim_images/`, `clean_images/` — image-lane assets

## Important note

- `data/raw/aavso_tcrb_raw_fullrange.csv` is expected by the pipeline but is not committed to git because it is larger than GitHub's file-size limit.
- The expected source and checksum are documented in `tcrb_data_download_record.md`.

See also:

- `data/raw_images/README.md`
- `data/interim_images/README.md`
- `data/clean_images/README.md`
