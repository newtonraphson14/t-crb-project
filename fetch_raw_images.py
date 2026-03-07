from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
RA_DEG = 239.87567
DEC_DEG = 25.92017
USER_AGENT = "CodexCLI/1.0 raw-image-fetcher"


def ensure_dirs() -> None:
    for rel in (
        Path("data/raw_images/reference/legacy"),
        Path("data/raw_images/reference/ps1"),
        Path("data/raw_images/reference/ps1/timeline_i"),
        Path("data/raw_images/reference/ps1/timeline_r"),
        Path("figures/raw_images/modern_panels"),
    ):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=120) as response:
        return response.read()


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
            "band_or_emulsion": "griz",
            "notes": "Legacy Survey DR10 reference FITS cutout centered on T CrB.",
        },
        {
            "source": "legacy",
            "product_type": "jpeg_cutout_rgb",
            **download(jpeg_url, base / "tcrb_legacy_lsdr10_ref_rgb_cutout.jpg"),
            "ra_deg": RA_DEG,
            "dec_deg": DEC_DEG,
            "date_obs": "",
            "band_or_emulsion": "rgb",
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
            "band_or_emulsion": "i",
            "notes": f"PS1 i-band FITS cutout using filename {filename_i}.",
        },
        {
            "source": "ps1",
            "product_type": "jpeg_cutout_i",
            **download(jpg_url, base / "tcrb_ps1_ref_i_cutout.jpg"),
            "ra_deg": RA_DEG,
            "dec_deg": DEC_DEG,
            "date_obs": "",
            "band_or_emulsion": "i",
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
                    "band_or_emulsion": filter_name,
                    "notes": f"PS1 single-epoch warp {filter_name}-band FITS cutout using filename {filename}.",
                },
                {
                    "source": "ps1",
                    "product_type": f"warp_jpeg_{filter_name}",
                    **download(jpg_url, jpg_path),
                    "ra_deg": RA_DEG,
                    "dec_deg": DEC_DEG,
                    "date_obs": date_obs,
                    "band_or_emulsion": filter_name,
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
    fieldnames = [
        "source",
        "product_type",
        "file_name",
        "local_path",
        "url",
        "bytes",
        "sha256",
        "ra_deg",
        "dec_deg",
        "date_obs",
        "band_or_emulsion",
        "notes",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ensure_dirs()
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

    summary = {
        "ra_deg": RA_DEG,
        "dec_deg": DEC_DEG,
        "assets": [*legacy_assets, *ps1_assets, *ps1_timeline_i_assets, *ps1_timeline_r_assets],
    }
    (ROOT / "notes/raw_image_reference_downloads.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
