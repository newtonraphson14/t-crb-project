# T CrB Data Download Record

## AAVSO Data Download (raw, unchanged)
- Download page: https://www.aavso.org/data-download
- Request type: form submit (`aavso_dd`)
- Object input: `T CrB`
- Date range selected: `start=All`, `stop=All` (full range)
- Output format selected: `zformat=csv` (comma-delimited)
- Exclude discrepant observations: `discrepant=no`
- Exclude nonstandard transformed type records: `mtypeinput=no`
- Result file URL:
  - `https://www.aavso.org/data-download/aavsodata_69ab687a2a85d.txt/download`
- Request timestamp (server): `Fri, 06 Mar 2026 23:51:22 GMT`

Saved file:
- Path: `/home/ikbarfaiz/Astrophysics Project/T CrB Projects/data/raw/aavso_tcrb_raw_fullrange.csv`
- SHA256: `e66716509d71ec12fc96550954c5b2c8d456b7033d38486f762ba4294ded0ede`
- Total CSV lines (including header): `753657`
- Data rows: `753656`
- Parsed JD coverage (valid JD > 0):
  - Min JD: `2402744.25400`
  - Max JD: `2461105.71605`

Modern-window quick coverage check (2015-01-01 to 2025-12-31):
- JD window: `2457023.50000` to `2461041.49999`
- Rows in window: `616616`
- Min/Max JD in this window: `2457024.71180` to `2461041.04517`

## ASAS-SN comparison dataset (optional cross-check)
- Source query page: `https://asas-sn.osu.edu/variables/58553`
- Star ID on ASAS-SN: `ASASSN-V J155930.27+255511.9` (T CrB)
- CSV endpoint:
  - `https://asas-sn.osu.edu/variables/c910b37f-1ba9-5523-8e93-1f8c4067aaa7.csv`

Saved file:
- Path: `/home/ikbarfaiz/Astrophysics Project/T CrB Projects/data/raw/asassn_tcrb_vband_raw.csv`
- SHA256: `79508514b07daa9c055f7aa976f0e05dc5f532de44cb9c9510bd52546b795e4b`
- Data rows: `223`
- HJD range: `2456003.12981` to `2458185.07642`
