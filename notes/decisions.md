# Decisions

- Core invalid rows are dropped only when `JD` is null/0 or `Magnitude` is null.
- Validation-flagged AAVSO rows are retained in the base dataset and tracked with `is_flagged`.
- Loose filtering keeps all core-valid rows and tracks missing uncertainty with `unc_isna`.
- Strict filtering is used only as a robustness check and currently means `Uncertainty` is present and `<= 0.05`.
- The pipeline is split into two lanes: `modern V` for signal-rich modern analysis and `all-cycles Vis` for cross-cycle consistency.
- Modern `V` products are generated on shared 1-day and 7-day bins, plus 3-bin and 5-bin rolling medians on the 7-day series.
- A shared 7-day grid anchored at `JD` 2457023.5 is used for modern `V` and the AAVSO-vs-ASAS-SN overlap comparison.
- For cross-cycle work, `Vis` is the design choice rather than an ad hoc fallback.
- AAVSO coverage in 1935-1955 is effectively `Vis`-only; `V` is not available in a usable amount there, so historical lane products are defined as `Vis` by design.
- Early-cycle context uses `Vis` coverage from 1860-01-01 to 1870-12-31.
- ASAS-SN is compared against AAVSO using `HJD ~= JD` as a first-pass approximation, and overlap metrics are computed from directly merged 7-day bins.
- ZTF raw download is preserved under `data/raw/`, but skipped because the file content is an HTML 504 error page.
