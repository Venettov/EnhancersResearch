#!/usr/bin/env python3
"""Download manifest-listed enhancer data and companion materials.

Files stay out of Git; this script recreates them from the URLs and checksums
recorded in the two TSV manifests next to this script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DATA_MANIFEST = ROOT / "download_manifest.tsv"
PAPER_MANIFEST = ROOT / "COMPANION_MATERIALS_MANIFEST.tsv"
USER_AGENT = "EnhancerPredictionResearchDataFetcher/1.0 (public academic data)"
BLOCK_SIZE = 1024 * 1024


def rows_from(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def safe_destination(relative_path: str) -> Path:
    destination = (ROOT / relative_path).resolve()
    try:
        destination.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Manifest path escapes the project: {relative_path}") from exc
    return destination


def data_path(row: dict[str, str]) -> str | None:
    source = row.get("source", "")
    name = row.get("filename", "")
    if source.startswith("SCREEN ENCODE4"):
        return f"01_ENCODE4_SCREEN/{name}"
    if source.startswith("Genome Biology 2025 MPRA/STARR"):
        return f"03_MPRA_STARR_CROSS_ASSAY_2025/{name}"
    if source.startswith("VISTA Enhancer Browser"):
        return f"04_VISTA/{name}"
    if source.startswith("Figshare hematopoiesis MPRA"):
        return f"05_HEMATOPOIESIS_MPRA/{name}"
    if source.startswith("ENCODE "):
        accession = source.split()[-1]
        return f"02_LENTIMPRA_ENCODE_2025/{accession}/{name}"
    return None


def expected_checksum(checksum: str) -> tuple[str, str] | None:
    value = (checksum or "").strip().lower()
    if not value:
        return None
    if value.startswith("md5:"):
        return "md5", value[4:]
    if value.startswith("sha256:"):
        return "sha256", value[7:]
    if re.fullmatch(r"[0-9a-f]{32}", value):
        return "md5", value
    if re.fullmatch(r"[0-9a-f]{64}", value):
        return "sha256", value
    return None


def file_digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, size_text: str, checksum: str) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    try:
        expected_size = int(size_text) if size_text else 0
    except ValueError:
        expected_size = 0
    if expected_size and path.stat().st_size != expected_size:
        return False, f"size is {path.stat().st_size:,}; expected {expected_size:,} bytes"
    expected = expected_checksum(checksum)
    if expected:
        algorithm, value = expected
        actual = file_digest(path, algorithm)
        if actual.lower() != value:
            return False, f"{algorithm.upper()} mismatch"
    return True, "verified"


def fetch(url: str, destination: Path, size_text: str, checksum: str) -> None:
    if not url.startswith(("https://", "http://")):
        raise ValueError(f"No downloadable HTTP source URL for {destination.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=120) as response, partial.open("wb") as output:
            while True:
                block = response.read(BLOCK_SIZE)
                if not block:
                    break
                output.write(block)
        ok, reason = verify(partial, size_text, checksum)
        if not ok:
            raise ValueError(f"Downloaded file failed verification ({reason})")
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def download_row(destination: Path, url: str, size: str, checksum: str,
                 label: str) -> bool:
    ok, reason = verify(destination, size, checksum)
    if ok:
        print(f"Already available: {label}")
        return False
    if reason != "missing":
        print(f"Replacing incomplete or mismatched file: {label} ({reason})")
    print(f"Downloading: {label}")
    fetch(url, destination, size, checksum)
    print(f"Saved: {destination.relative_to(PROJECT_ROOT)}")
    return True


def run_data() -> tuple[int, int]:
    downloaded = errors = 0
    for row in rows_from(DATA_MANIFEST):
        status = row.get("status", "").strip()
        filename = row.get("filename", "").strip()
        if status not in {"downloaded", "already_present"}:
            if filename:
                print(f"Skipped by design: {filename} ({status or 'no status'})")
            continue
        relative = data_path(row)
        if not relative or not row.get("url"):
            print(f"Cannot map manifest entry to a file: {row}", file=sys.stderr)
            errors += 1
            continue
        try:
            downloaded += download_row(
                safe_destination(relative), row["url"], row.get("size_bytes", ""),
                row.get("checksum", ""), filename,
            )
        except Exception as exc:
            errors += 1
            print(f"ERROR: {filename}: {exc}", file=sys.stderr)
    return downloaded, errors


def run_papers() -> tuple[int, int]:
    downloaded = errors = 0
    for row in rows_from(PAPER_MANIFEST):
        status = row.get("status", "").strip()
        if status == "available_not_downloaded_large" or row.get("category") == "MODEL_WEIGHTS":
            print(f"Skipped by design: {row.get('filename', '')} ({status or 'large model'})")
            continue
        relative = "/".join((row.get("study_folder", ""), row.get("category", ""),
                             row.get("filename", "")))
        if not all((row.get("study_folder"), row.get("category"), row.get("filename"),
                    row.get("source_url"))):
            print(f"Incomplete companion-material manifest row: {row}", file=sys.stderr)
            errors += 1
            continue
        try:
            downloaded += download_row(
                safe_destination(relative), row["source_url"], row.get("size_bytes", ""),
                row.get("sha256", ""), row["filename"],
            )
        except Exception as exc:
            errors += 1
            print(f"ERROR: {row.get('filename', '')}: {exc}", file=sys.stderr)
    return downloaded, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=("data", "papers", "all"), required=True,
                        help="download selected datasets, papers/supporting files, or both")
    args = parser.parse_args()
    totals = [0, 0]
    if args.group in {"data", "all"}:
        print("== Selected data resources ==")
        result = run_data()
        totals = [totals[0] + result[0], totals[1] + result[1]]
    if args.group in {"papers", "all"}:
        print("== Papers and companion materials ==")
        result = run_papers()
        totals = [totals[0] + result[0], totals[1] + result[1]]
    print(f"\nFinished: {totals[0]} file(s) downloaded; {totals[1]} error(s).")
    print("Oversized archives and model weights remain source-linked in the manifests.")
    return 1 if totals[1] else 0


if __name__ == "__main__":
    raise SystemExit(main())
