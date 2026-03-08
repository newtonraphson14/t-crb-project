from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
RA_DEG = 239.87567
DEC_DEG = 25.92017
USER_AGENT = "CodexCLI/1.0 raw-image-fetcher"
DASCH_API_BASE = "https://api.starglass.cfa.harvard.edu/public"
ZTF_SEARCH_BASE = "https://irsa.ipac.caltech.edu/ibe/search/ztf/products"
ZTF_DATA_BASE = "https://irsa.ipac.caltech.edu/ibe/data/ztf/products"
MANIFEST_FIELDNAMES = [
    "source",
    "product_type",
    "file_name",
    "local_path",
    "url",
    "bytes",
    "sha256",
    "date_obs",
    "jd_mid",
    "ra_deg",
    "dec_deg",
    "band_or_emulsion",
    "exptime_s",
    "pixel_scale_arcsec",
    "wcs_status",
    "notes",
]
PANEL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def ensure_dirs() -> None:
    for rel in (
        Path("data/raw_images/dasch"),
        Path("data/raw_images/ztf"),
        Path("data/raw_images/reference/legacy"),
        Path("data/raw_images/reference/ps1"),
        Path("data/raw_images/reference/ps1/timeline_i"),
        Path("data/raw_images/reference/ps1/timeline_r"),
        Path("figures/raw_images/historical_panels"),
        Path("figures/raw_images/modern_panels"),
        Path("figures/raw_images/qc"),
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=120) as response:
        return response.read()


def fetch_url(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 120) -> bytes:
    merged_headers = {"User-Agent": USER_AGENT}
    if headers:
        merged_headers.update(headers)
    request = Request(url, data=data, headers=merged_headers)
    transient_codes = {429, 500, 502, 503, 504}
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code not in transient_codes or attempt == 2:
                raise
            last_error = exc
        except URLError as exc:
            if attempt == 2:
                raise
            last_error = exc
        time.sleep(2 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to fetch URL after retries: {url}")


def fetch_text(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 120) -> str:
    return fetch_url(url, data=data, headers=headers, timeout=timeout).decode("utf-8", errors="replace")


def fetch_json(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 120) -> object:
    return json.loads(fetch_text(url, data=data, headers=headers, timeout=timeout))


def post_json(url: str, payload: dict[str, object], *, headers: dict[str, str] | None = None, timeout: int = 120) -> object:
    merged_headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    if headers:
        merged_headers.update(headers)
    return fetch_json(url, data=json.dumps(payload).encode("utf-8"), headers=merged_headers, timeout=timeout)


def download(url: str, out_path: Path) -> dict[str, object]:
    payload = fetch_bytes(url)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)
    return {
        "url": url,
        "file_name": out_path.name,
        "local_path": str(out_path.relative_to(ROOT)),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def parse_ps1_table(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=" ")
    rows: list[dict[str, str]] = []
    for row in reader:
        compact = {key: value for key, value in row.items() if key and value}
        if compact:
            rows.append(compact)
    if rows:
        return rows

    header = lines[0].split()
    parsed_rows: list[dict[str, str]] = []
    for line in lines[1:]:
        values = line.split()
        if len(values) != len(header):
            continue
        parsed_rows.append(dict(zip(header, values)))
    return parsed_rows


def parse_csv_text(text: str) -> list[dict[str, str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def query_ps1_rows(filter_name: str = "i", image_type: str = "stack") -> list[dict[str, str]]:
    query = urlencode({"ra": RA_DEG, "dec": DEC_DEG, "filters": filter_name, "type": image_type})
    text = fetch_bytes(f"https://ps1images.stsci.edu/cgi-bin/ps1filenames.py?{query}").decode("utf-8", errors="replace")
    return parse_ps1_table(text)


def pick_ps1_filename(filter_name: str = "i") -> str:
    rows = query_ps1_rows(filter_name=filter_name, image_type="stack")
    for row in rows:
        if row.get("filter") == filter_name and row.get("filename"):
            return row["filename"]
    raise RuntimeError(f"Could not resolve a PS1 filename for filter={filter_name!r}")


def mjd_to_datestr(mjd_value: str) -> str:
    dt = datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=float(mjd_value))
    return dt.strftime("%Y-%m-%d")


def jd_to_datestr(jd_value: str) -> str:
    dt = datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=(float(jd_value) - 2400000.5))
    return dt.strftime("%Y-%m-%d")


def build_panel(image_paths: list[Path], labels: list[str], out_path: Path) -> None:
    opened = [Image.open(path).convert("L") for path in image_paths]
    tile_w, tile_h = opened[0].size
    pad = 12
    label_h = 22
    panel = Image.new("L", ((tile_w * len(opened)) + (pad * (len(opened) + 1)), tile_h + label_h + (pad * 2)), color=18)
    draw = ImageDraw.Draw(panel)
    x = pad
    for image, label in zip(opened, labels, strict=True):
        panel.paste(image, (x, pad))
        draw.text((x, tile_h + pad + 2), label, fill=235)
        x += tile_w + pad
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out_path)


def maybe_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_date_value(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    numeric = maybe_float(text)
    if numeric is not None and numeric > 2_000_000:
        return jd_to_datestr(text)
    return text


def value_in_date_window(date_obs: str, start: str | None, end: str | None) -> bool:
    if not date_obs:
        return False
    if start and date_obs < start:
        return False
    if end and date_obs > end:
        return False
    return True


def safe_stem(text: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in text.strip())
    return cleaned.strip("_") or "unknown"


def evenly_sample_rows(rows: list[dict[str, object]], max_items: int) -> list[dict[str, object]]:
    if max_items <= 0 or len(rows) <= max_items:
        return rows
    if max_items == 1:
        return [rows[len(rows) // 2]]

    selected: list[dict[str, object]] = []
    used_indexes: set[int] = set()
    last_index = len(rows) - 1
    for idx in range(max_items):
        raw_index = round(idx * last_index / (max_items - 1))
        if raw_index in used_indexes:
            continue
        used_indexes.add(raw_index)
        selected.append(rows[raw_index])
    return selected


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_path(path_value: str, *, base_dir: Path) -> Path:
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    return candidate


def relative_to_root(path: Path) -> Path:
    return path.resolve().relative_to(ROOT)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def ensure_repo_relative(target_rel: Path) -> Path:
    target_path = (ROOT / target_rel).resolve()
    target_path.relative_to(ROOT)
    return target_path


def file_metadata(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "file_name": path.name,
        "local_path": str(relative_to_root(path)),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def default_target_rel(source: str, source_path: Path) -> Path:
    return Path("data/raw_images") / source / source_path.name


def stage_local_asset(asset_spec: dict[str, object], *, spec_dir: Path, default_source: str) -> tuple[dict[str, object], Path, str] | tuple[dict[str, object], None, None]:
    source = str(asset_spec.get("source", default_source) or default_source).strip().lower()
    source_path = resolve_path(str(asset_spec["source_path"]), base_dir=spec_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Missing source asset: {source_path}")

    target_rel_value = asset_spec.get("target_path")
    if target_rel_value:
        target_rel = Path(str(target_rel_value))
    else:
        target_rel = default_target_rel(source, source_path)
    target_path = ensure_repo_relative(target_rel)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if source_path.resolve() != target_path:
        shutil.copy2(source_path, target_path)

    row = {
        "source": source,
        "product_type": str(asset_spec.get("product_type", "")),
        **file_metadata(target_path),
        "url": str(asset_spec.get("url", "")),
        "date_obs": str(asset_spec.get("date_obs", "")),
        "jd_mid": str(asset_spec.get("jd_mid", "")),
        "ra_deg": asset_spec.get("ra_deg", RA_DEG),
        "dec_deg": asset_spec.get("dec_deg", DEC_DEG),
        "band_or_emulsion": str(asset_spec.get("band_or_emulsion", "")),
        "exptime_s": str(asset_spec.get("exptime_s", "")),
        "pixel_scale_arcsec": str(asset_spec.get("pixel_scale_arcsec", "")),
        "wcs_status": str(asset_spec.get("wcs_status", "")),
        "notes": str(asset_spec.get("notes", "")),
    }

    include_in_panel = bool(asset_spec.get("panel_include", False))
    panel_label = str(asset_spec.get("panel_label", row["date_obs"] or target_path.stem))
    if include_in_panel and target_path.suffix.lower() in PANEL_EXTENSIONS:
        return row, target_path, panel_label
    return row, None, None


def process_stage_spec(spec_path: Path) -> dict[str, object]:
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    source = str(payload.get("source", "")).strip().lower()
    if not source:
        raise ValueError(f"Stage spec {spec_path} is missing 'source'")

    asset_specs = payload.get("assets", [])
    if not isinstance(asset_specs, list) or not asset_specs:
        raise ValueError(f"Stage spec {spec_path} must contain a non-empty 'assets' list")

    rows: list[dict[str, object]] = []
    panel_paths: list[Path] = []
    panel_labels: list[str] = []
    for asset_spec in asset_specs:
        if not isinstance(asset_spec, dict):
            raise ValueError(f"Invalid asset entry in {spec_path}: expected object")
        row, panel_path, panel_label = stage_local_asset(asset_spec, spec_dir=spec_path.parent, default_source=source)
        rows.append(row)
        if panel_path is not None and panel_label is not None:
            panel_paths.append(panel_path)
            panel_labels.append(panel_label)

    manifest_output = payload.get("manifest_output", f"data/raw_images/{source}/manifest_{source}.csv")
    manifest_path = ensure_repo_relative(Path(str(manifest_output)))
    write_manifest(rows, manifest_path)

    panel_output = payload.get("panel_output")
    panel_path_value = None
    if panel_output and panel_paths:
        panel_path = ensure_repo_relative(Path(str(panel_output)))
        build_panel(panel_paths, panel_labels, panel_path)
        panel_path_value = str(relative_to_root(panel_path))

    return {
        "source": source,
        "spec_path": display_path(spec_path),
        "manifest_path": display_path(manifest_path),
        "panel_path": panel_path_value,
        "assets": rows,
    }


def dasch_headers(api_key: str | None) -> dict[str, str]:
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def query_dasch_exposures(*, ra_deg: float, dec_deg: float, api_key: str | None = None) -> list[dict[str, str]]:
    payload = {"ra_deg": ra_deg, "dec_deg": dec_deg}
    response = post_json(f"{DASCH_API_BASE}/dasch/dr7/queryexps", payload, headers=dasch_headers(api_key), timeout=180)
    if not isinstance(response, list):
        raise RuntimeError("Unexpected DASCH query response shape")
    return parse_csv_text("\n".join(str(line) for line in response))


def pick_dasch_rows(
    rows: list[dict[str, str]],
    *,
    window_start: str | None,
    window_end: str | None,
    max_epochs: int,
) -> list[dict[str, str]]:
    curated: list[dict[str, str]] = []
    for row in rows:
        row["date_obs"] = normalize_date_value(row.get("expdate") or row.get("obsDate") or row.get("obs_date"))
        row["jd_mid"] = str(row.get("obsDate") or row.get("obs_date") or "")
        if not value_in_date_window(row["date_obs"], window_start, window_end):
            continue
        wcssource = str(row.get("wcssource", "")).strip().lower()
        if wcssource and wcssource not in {"imwcs", "wcsloc"}:
            continue
        if not str(row.get("solnum", "")).strip():
            continue
        curated.append(row)

    curated.sort(key=lambda row: (row.get("date_obs", ""), str(row.get("series", "")), str(row.get("platenum", ""))))
    return evenly_sample_rows(curated, max_epochs)


def download_dasch_cutouts(
    *,
    api_key: str | None,
    ra_deg: float,
    dec_deg: float,
    radius_arcsec: int,
    window_start: str,
    window_end: str,
    max_epochs: int,
    dry_run: bool,
) -> dict[str, object]:
    query_rows = query_dasch_exposures(ra_deg=ra_deg, dec_deg=dec_deg, api_key=api_key)
    query_out = ROOT / f"data/raw_images/dasch/queryexps_{window_start}_{window_end}.csv"
    if query_rows:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(query_rows[0].keys()))
        writer.writeheader()
        writer.writerows(query_rows)
        write_text(query_out, output.getvalue())

    selected_rows = pick_dasch_rows(query_rows, window_start=window_start, window_end=window_end, max_epochs=max_epochs)
    assets: list[dict[str, object]] = []
    for row in selected_rows:
        series = str(row.get("series", "")).strip().lower()
        platenum = str(row.get("platenum", "")).strip()
        solnum = str(row.get("solnum", "")).strip()
        date_obs = str(row.get("date_obs", "")).strip()
        jd_mid = str(row.get("jd_mid", "")).strip()
        plate_id = f"{series}{int(float(platenum)):05d}"
        plate_token = safe_stem(plate_id)
        stem = f"tcrb_dasch_{plate_token}_{safe_stem(date_obs)}_sol{safe_stem(solnum)}_cutout"
        target_path = ROOT / "data/raw_images/dasch" / f"{stem}.fits.gz"
        cutout_payload = {
            "plate_id": plate_id,
            "solution_number": int(float(solnum)),
            "center_ra_deg": ra_deg,
            "center_dec_deg": dec_deg,
        }
        url = f"{DASCH_API_BASE}/dasch/dr7/cutout"
        if not dry_run:
            response = post_json(url, cutout_payload, headers=dasch_headers(api_key), timeout=300)
            if not isinstance(response, str):
                raise RuntimeError(f"Unexpected DASCH cutout response for {plate_id}")
            payload_bytes = base64.b64decode(response)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(payload_bytes)
            metadata = file_metadata(target_path)
        else:
            metadata = {
                "file_name": target_path.name,
                "local_path": str(relative_to_root(target_path)),
                "bytes": 0,
                "sha256": "",
            }

        assets.append(
            {
                "source": "dasch",
                "product_type": "postage_stamp_fits_gz",
                **metadata,
                "url": url,
                "date_obs": date_obs,
                "jd_mid": jd_mid,
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
                "band_or_emulsion": str(row.get("series", "")),
                "exptime_s": str(row.get("exptime") or row.get("exptime_s") or ""),
                "pixel_scale_arcsec": "",
                "wcs_status": str(row.get("wcssource", "")),
                "notes": f"DASCH cutout for plate {plate_id} solution_number={solnum}. Server-side cutout size is fixed by DR7.",
            }
        )

    manifest_path = ROOT / "data/raw_images/dasch/manifest_dasch.csv"
    write_manifest(assets, manifest_path)
    return {
        "source": "dasch",
        "query_path": display_path(query_out),
        "manifest_path": display_path(manifest_path),
        "selected_epochs": len(selected_rows),
        "assets": assets,
    }


def ztf_search_url(product: str, params: dict[str, str]) -> str:
    return f"{ZTF_SEARCH_BASE}/{product}?" + urlencode(params)


def query_ztf_rows(
    *,
    product: str,
    ra_deg: float,
    dec_deg: float,
    size_deg: float,
    columns: list[str] | None = None,
    where: str | None = None,
) -> tuple[list[dict[str, str]], str]:
    params = {
        "POS": f"{ra_deg:.5f},{dec_deg:.5f}",
        "INTERSECT": "CENTER",
        "ct": "csv",
    }
    if size_deg > 0:
        params["SIZE"] = f"{size_deg:.5f}"
    if columns:
        params["COLUMNS"] = ",".join(columns)
    if where:
        params["WHERE"] = where
    url = ztf_search_url(product, params)
    text = fetch_text(url, timeout=180)
    if text.lstrip().startswith("<"):
        snippet = text.strip().splitlines()[0][:120] if text.strip() else "empty response"
        raise RuntimeError(f"ZTF search returned HTML instead of CSV: {snippet}")
    return parse_csv_text(text), text


def build_ztf_science_cutout_url(row: dict[str, str], *, ra_deg: float, dec_deg: float, cutout_size_arcsec: int) -> str:
    filefracday = str(row["filefracday"]).strip()
    padded_field = f"{int(row['field']):06d}"
    ccdid = f"{int(row['ccdid']):02d}"
    qid = str(row["qid"]).strip()
    filtercode = str(row["filtercode"]).strip()
    imgtypecode = str(row.get("imgtypecode", "o")).strip() or "o"
    path = (
        f"sci/{filefracday[:4]}/{filefracday[4:8]}/{filefracday}/"
        f"ztf_{filefracday}_{padded_field}_{filtercode}_c{ccdid}_{imgtypecode}_q{qid}_sciimg.fits"
    )
    params = urlencode({"center": f"{ra_deg:.5f},{dec_deg:.5f}", "size": f"{cutout_size_arcsec}arcsec", "gzip": "false"})
    return f"{ZTF_DATA_BASE}/{path}?{params}"


def build_ztf_reference_cutout_url(row: dict[str, str], *, ra_deg: float, dec_deg: float, cutout_size_arcsec: int) -> str:
    padded_field = f"{int(row['field']):06d}"
    ccdid = f"{int(row['ccdid']):02d}"
    qid = str(row["qid"]).strip()
    filtercode = str(row["filtercode"]).strip()
    fieldprefix = padded_field[:3]
    path = (
        f"ref/{fieldprefix}/field{padded_field}/{filtercode}/ccd{ccdid}/q{qid}/"
        f"ztf_{padded_field}_{filtercode}_c{ccdid}_q{qid}_refimg.fits"
    )
    params = urlencode({"center": f"{ra_deg:.5f},{dec_deg:.5f}", "size": f"{cutout_size_arcsec}arcsec", "gzip": "false"})
    return f"{ZTF_DATA_BASE}/{path}?{params}"


def pick_ztf_science_rows(
    rows: list[dict[str, str]],
    *,
    window_start: str | None,
    window_end: str | None,
    max_epochs: int,
    filtercode: str | None,
) -> list[dict[str, str]]:
    curated: list[dict[str, str]] = []
    for row in rows:
        date_obs = normalize_date_value(row.get("obsdate"))
        row["date_obs"] = date_obs
        if not value_in_date_window(date_obs, window_start, window_end):
            continue
        if filtercode and str(row.get("filtercode", "")).strip() != filtercode:
            continue
        infobits = maybe_float(row.get("infobits"))
        if infobits is not None and infobits != 0:
            continue
        curated.append(row)

    curated.sort(key=lambda row: row.get("date_obs", ""))
    return evenly_sample_rows(curated, max_epochs)


def download_ztf_cutouts(
    *,
    ra_deg: float,
    dec_deg: float,
    cutout_size_arcsec: int,
    size_deg: float,
    window_start: str,
    window_end: str,
    max_epochs: int,
    filtercode: str | None,
    dry_run: bool,
) -> dict[str, object]:
    where_parts = [f"obsdate>='{window_start}'", f"obsdate<='{window_end}'"]
    if filtercode:
        where_parts.append(f"filtercode='{filtercode}'")
    sci_rows, sci_csv = query_ztf_rows(
        product="sci",
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        size_deg=size_deg,
        columns=["filefracday", "field", "ccdid", "qid", "filtercode", "imgtypecode", "obsdate", "obsjd", "infobits"],
        where=" AND ".join(where_parts),
    )
    sci_query_path = ROOT / f"data/raw_images/ztf/search_sci_{window_start}_{window_end}.csv"
    write_text(sci_query_path, sci_csv)
    selected_rows = pick_ztf_science_rows(
        sci_rows,
        window_start=window_start,
        window_end=window_end,
        max_epochs=max_epochs,
        filtercode=filtercode,
    )

    assets: list[dict[str, object]] = []
    downloaded_refs: set[tuple[str, str, str, str]] = set()
    for row in selected_rows:
        date_obs = str(row.get("date_obs", "")).strip()
        filefracday = str(row.get("filefracday", "")).strip()
        jd_mid = str(row.get("obsjd") or row.get("jd") or "")
        this_filter = str(row.get("filtercode", "")).strip()
        stem = f"tcrb_ztf_{safe_stem(date_obs)}_{safe_stem(this_filter)}_{safe_stem(filefracday)}"
        sci_url = build_ztf_science_cutout_url(row, ra_deg=ra_deg, dec_deg=dec_deg, cutout_size_arcsec=cutout_size_arcsec)
        sci_path = ROOT / "data/raw_images/ztf" / f"{stem}_sci.fits"
        if not dry_run:
            sci_path.parent.mkdir(parents=True, exist_ok=True)
            sci_path.write_bytes(fetch_url(sci_url, timeout=300))
            sci_meta = file_metadata(sci_path)
        else:
            sci_meta = {"file_name": sci_path.name, "local_path": str(relative_to_root(sci_path)), "bytes": 0, "sha256": ""}
        assets.append(
            {
                "source": "ztf",
                "product_type": "science_cutout_fits",
                **sci_meta,
                "url": sci_url,
                "date_obs": date_obs,
                "jd_mid": jd_mid,
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
                "band_or_emulsion": this_filter,
                "exptime_s": "30",
                "pixel_scale_arcsec": "1.01",
                "wcs_status": "native_cutout",
                "notes": f"ZTF science cutout for filefracday={filefracday}.",
            }
        )

        ref_key = (
            str(row.get("field", "")),
            str(row.get("ccdid", "")),
            str(row.get("qid", "")),
            this_filter,
        )
        if ref_key in downloaded_refs:
            continue
        downloaded_refs.add(ref_key)
        ref_url = build_ztf_reference_cutout_url(row, ra_deg=ra_deg, dec_deg=dec_deg, cutout_size_arcsec=cutout_size_arcsec)
        ref_stem = (
            f"tcrb_ztf_ref_field{safe_stem(str(row.get('field', '')))}_"
            f"c{safe_stem(str(row.get('ccdid', '')))}_q{safe_stem(str(row.get('qid', '')))}_{safe_stem(this_filter)}"
        )
        ref_path = ROOT / "data/raw_images/ztf" / f"{ref_stem}.fits"
        if not dry_run:
            ref_path.write_bytes(fetch_url(ref_url, timeout=300))
            ref_meta = file_metadata(ref_path)
        else:
            ref_meta = {"file_name": ref_path.name, "local_path": str(relative_to_root(ref_path)), "bytes": 0, "sha256": ""}
        assets.append(
            {
                "source": "ztf",
                "product_type": "reference_cutout_fits",
                **ref_meta,
                "url": ref_url,
                "date_obs": "",
                "jd_mid": "",
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
                "band_or_emulsion": this_filter,
                "exptime_s": "",
                "pixel_scale_arcsec": "1.01",
                "wcs_status": "native_cutout",
                "notes": (
                    f"ZTF reference cutout for field={row.get('field')} ccdid={row.get('ccdid')} "
                    f"qid={row.get('qid')} filter={this_filter}, derived from the selected science exposure."
                ),
            }
        )

    manifest_path = ROOT / "data/raw_images/ztf/manifest_ztf.csv"
    write_manifest(assets, manifest_path)
    return {
        "source": "ztf",
        "query_paths": [display_path(sci_query_path)],
        "manifest_path": display_path(manifest_path),
        "selected_epochs": len(selected_rows),
        "assets": assets,
    }


def fetch_legacy_reference() -> list[dict[str, object]]:
    base = ROOT / "data/raw_images/reference/legacy"
    params_common = {
        "ra": f"{RA_DEG:.5f}",
        "dec": f"{DEC_DEG:.5f}",
        "pixscale": "0.262",
        "size": "256",
        "layer": "ls-dr10",
    }
    fits_url = "https://www.legacysurvey.org/viewer/fits-cutout?" + urlencode(
        params_common | {"bands": "griz"}
    )
    jpeg_url = "https://www.legacysurvey.org/viewer/jpeg-cutout?" + urlencode(params_common)

    assets = [
        {
            "source": "legacy",
            "product_type": "fits_cutout_griz",
            **download(fits_url, base / "tcrb_legacy_lsdr10_ref_griz_cutout.fits"),
            "ra_deg": RA_DEG,
            "dec_deg": DEC_DEG,
            "date_obs": "",
            "jd_mid": "",
            "band_or_emulsion": "griz",
            "exptime_s": "",
            "pixel_scale_arcsec": "0.262",
            "wcs_status": "native_cutout",
            "notes": "Legacy Survey DR10 reference FITS cutout centered on T CrB.",
        },
        {
            "source": "legacy",
            "product_type": "jpeg_cutout_rgb",
            **download(jpeg_url, base / "tcrb_legacy_lsdr10_ref_rgb_cutout.jpg"),
            "ra_deg": RA_DEG,
            "dec_deg": DEC_DEG,
            "date_obs": "",
            "jd_mid": "",
            "band_or_emulsion": "rgb",
            "exptime_s": "",
            "pixel_scale_arcsec": "0.262",
            "wcs_status": "display_cutout",
            "notes": "Legacy Survey DR10 reference JPEG cutout centered on T CrB.",
        },
    ]
    return assets


def fetch_ps1_reference() -> list[dict[str, object]]:
    base = ROOT / "data/raw_images/reference/ps1"
    filename_i = pick_ps1_filename("i")
    encoded_filename_i = quote(filename_i, safe="/")
    fits_url = (
        "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?"
        + urlencode(
            {
                "ra": f"{RA_DEG:.5f}",
                "dec": f"{DEC_DEG:.5f}",
                "size": "256",
                "format": "fits",
            }
        )
        + f"&red={encoded_filename_i}"
    )
    jpg_url = (
        "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?"
        + urlencode(
            {
                "ra": f"{RA_DEG:.5f}",
                "dec": f"{DEC_DEG:.5f}",
                "size": "256",
                "format": "jpg",
            }
        )
        + f"&red={encoded_filename_i}"
    )

    assets = [
        {
            "source": "ps1",
            "product_type": "fits_cutout_i",
            **download(fits_url, base / "tcrb_ps1_ref_i_cutout.fits"),
            "ra_deg": RA_DEG,
            "dec_deg": DEC_DEG,
            "date_obs": "",
            "jd_mid": "",
            "band_or_emulsion": "i",
            "exptime_s": "",
            "pixel_scale_arcsec": "",
            "wcs_status": "native_cutout",
            "notes": f"PS1 i-band FITS cutout using filename {filename_i}.",
        },
        {
            "source": "ps1",
            "product_type": "jpeg_cutout_i",
            **download(jpg_url, base / "tcrb_ps1_ref_i_cutout.jpg"),
            "ra_deg": RA_DEG,
            "dec_deg": DEC_DEG,
            "date_obs": "",
            "jd_mid": "",
            "band_or_emulsion": "i",
            "exptime_s": "",
            "pixel_scale_arcsec": "",
            "wcs_status": "display_cutout",
            "notes": f"PS1 i-band JPEG cutout using filename {filename_i}.",
        },
    ]
    return assets


def fetch_ps1_timeline(filter_name: str = "i", max_years: int = 5) -> list[dict[str, object]]:
    base = ROOT / f"data/raw_images/reference/ps1/timeline_{filter_name}"
    rows = query_ps1_rows(filter_name=filter_name, image_type="warp")
    selected_by_year: dict[str, dict[str, str]] = {}
    for row in rows:
        mjd = row.get("mjd")
        filename = row.get("filename")
        if not mjd or not filename:
            continue
        year = mjd_to_datestr(mjd)[:4]
        if year not in selected_by_year:
            selected_by_year[year] = row
    selected_rows = [selected_by_year[year] for year in sorted(selected_by_year)[:max_years]]

    assets: list[dict[str, object]] = []
    panel_paths: list[Path] = []
    panel_labels: list[str] = []
    for row in selected_rows:
        mjd = row["mjd"]
        date_obs = mjd_to_datestr(mjd)
        filename = row["filename"]
        encoded_filename = quote(filename, safe="/")
        stem = f"tcrb_ps1_warp_{filter_name}_{date_obs}_mjd{mjd.replace('.', '_')}"
        fits_url = (
            "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?"
            + urlencode({"ra": f"{RA_DEG:.5f}", "dec": f"{DEC_DEG:.5f}", "size": "256", "format": "fits"})
            + f"&red={encoded_filename}"
        )
        jpg_url = (
            "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?"
            + urlencode({"ra": f"{RA_DEG:.5f}", "dec": f"{DEC_DEG:.5f}", "size": "256", "format": "jpg"})
            + f"&red={encoded_filename}"
        )
        fits_path = base / f"{stem}.fits"
        jpg_path = base / f"{stem}.jpg"
        assets.extend(
            [
                {
                    "source": "ps1",
                    "product_type": f"warp_fits_{filter_name}",
                    **download(fits_url, fits_path),
                    "ra_deg": RA_DEG,
                    "dec_deg": DEC_DEG,
                    "date_obs": date_obs,
                    "jd_mid": mjd,
                    "band_or_emulsion": filter_name,
                    "exptime_s": "",
                    "pixel_scale_arcsec": "",
                    "wcs_status": "native_cutout",
                    "notes": f"PS1 single-epoch warp {filter_name}-band FITS cutout using filename {filename}.",
                },
                {
                    "source": "ps1",
                    "product_type": f"warp_jpeg_{filter_name}",
                    **download(jpg_url, jpg_path),
                    "ra_deg": RA_DEG,
                    "dec_deg": DEC_DEG,
                    "date_obs": date_obs,
                    "jd_mid": mjd,
                    "band_or_emulsion": filter_name,
                    "exptime_s": "",
                    "pixel_scale_arcsec": "",
                    "wcs_status": "display_cutout",
                    "notes": f"PS1 single-epoch warp {filter_name}-band JPEG cutout using filename {filename}.",
                },
            ]
        )
        panel_paths.append(jpg_path)
        panel_labels.append(date_obs)

    write_manifest(assets, base / f"manifest_ps1_timeline_{filter_name}.csv")
    if panel_paths:
        build_panel(
            panel_paths,
            panel_labels,
            ROOT / f"figures/raw_images/modern_panels/tcrb_ps1_{filter_name}_timeline.png",
        )
    return assets


def write_manifest(rows: Iterable[dict[str, object]], out_path: Path) -> None:
    rows = list(rows)
    if not rows:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch or stage raw-image assets for the T CrB project.")
    parser.add_argument(
        "--skip-reference",
        action="store_true",
        help="Skip the Legacy/PS1 online fetch flow and only process local stage specs.",
    )
    parser.add_argument(
        "--stage-spec",
        action="append",
        default=[],
        help="Path to a JSON stage spec for local DASCH/ZTF asset ingestion. Can be passed multiple times.",
    )
    parser.add_argument("--download-dasch", action="store_true", help="Query DASCH and download representative historical cutouts.")
    parser.add_argument("--download-ztf", action="store_true", help="Query ZTF/IRSA and download representative modern cutouts.")
    parser.add_argument("--dry-run", action="store_true", help="Query endpoints and write manifests without downloading payload files.")
    parser.add_argument("--ra-deg", type=float, default=RA_DEG, help="Target right ascension in degrees.")
    parser.add_argument("--dec-deg", type=float, default=DEC_DEG, help="Target declination in degrees.")
    parser.add_argument("--max-epochs", type=int, default=5, help="Maximum representative epochs to download per source.")
    parser.add_argument("--cutout-radius-arcsec", type=int, default=60, help="Reserved DASCH argument. DR7 cutout size is fixed by the server.")
    parser.add_argument("--cutout-size-arcsec", type=int, default=60, help="ZTF cutout size in arcsec.")
    parser.add_argument("--ztf-search-size-deg", type=float, default=0.0, help="Optional ZTF search box size in degrees. Default 0 uses a point query.")
    parser.add_argument("--dasch-window-start", default="1935-01-01", help="Historical DASCH window start in YYYY-MM-DD.")
    parser.add_argument("--dasch-window-end", default="1955-12-31", help="Historical DASCH window end in YYYY-MM-DD.")
    parser.add_argument("--ztf-window-start", default="2018-01-01", help="Modern ZTF window start in YYYY-MM-DD.")
    parser.add_argument("--ztf-window-end", default="2025-12-31", help="Modern ZTF window end in YYYY-MM-DD.")
    parser.add_argument("--ztf-filtercode", choices=["zg", "zr", "zi"], help="Optional ZTF filter restriction.")
    parser.add_argument("--dasch-api-key", default=os.environ.get("DASCH_API_KEY", ""), help="Optional DASCH Starglass API key. Defaults to env DASCH_API_KEY.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dirs()
    legacy_assets: list[dict[str, object]] = []
    ps1_assets: list[dict[str, object]] = []
    ps1_timeline_i_assets: list[dict[str, object]] = []
    ps1_timeline_r_assets: list[dict[str, object]] = []
    if not args.skip_reference:
        legacy_assets = fetch_legacy_reference()
        ps1_assets = fetch_ps1_reference()
        ps1_timeline_i_assets = fetch_ps1_timeline(filter_name="i", max_years=5)
        ps1_timeline_r_assets = fetch_ps1_timeline(filter_name="r", max_years=5)

        write_manifest(legacy_assets, ROOT / "data/raw_images/reference/legacy/manifest_legacy.csv")
        write_manifest(ps1_assets, ROOT / "data/raw_images/reference/ps1/manifest_ps1.csv")
        write_manifest(
            [*legacy_assets, *ps1_assets, *ps1_timeline_i_assets, *ps1_timeline_r_assets],
            ROOT / "data/raw_images/reference/manifest_reference.csv",
        )

    stage_runs = [process_stage_spec(resolve_path(spec_path, base_dir=ROOT)) for spec_path in args.stage_spec]
    download_runs: list[dict[str, object]] = []
    if args.download_dasch:
        try:
            download_runs.append(
                download_dasch_cutouts(
                    api_key=args.dasch_api_key or None,
                    ra_deg=args.ra_deg,
                    dec_deg=args.dec_deg,
                    radius_arcsec=args.cutout_radius_arcsec,
                    window_start=args.dasch_window_start,
                    window_end=args.dasch_window_end,
                    max_epochs=args.max_epochs,
                    dry_run=args.dry_run,
                )
            )
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DASCH download failed with HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"DASCH download failed: {exc}") from exc
    if args.download_ztf:
        try:
            download_runs.append(
                download_ztf_cutouts(
                    ra_deg=args.ra_deg,
                    dec_deg=args.dec_deg,
                    cutout_size_arcsec=args.cutout_size_arcsec,
                    size_deg=args.ztf_search_size_deg,
                    window_start=args.ztf_window_start,
                    window_end=args.ztf_window_end,
                    max_epochs=args.max_epochs,
                    filtercode=args.ztf_filtercode,
                    dry_run=args.dry_run,
                )
            )
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ZTF download failed with HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"ZTF download failed: {exc}") from exc

    summary: dict[str, object] = {
        "ra_deg": args.ra_deg,
        "dec_deg": args.dec_deg,
        "reference_assets": [*legacy_assets, *ps1_assets, *ps1_timeline_i_assets, *ps1_timeline_r_assets],
        "stage_runs": stage_runs,
        "download_runs": download_runs,
    }
    if not args.skip_reference:
        (ROOT / "notes/raw_image_reference_downloads.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
