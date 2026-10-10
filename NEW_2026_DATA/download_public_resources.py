#!/usr/bin/env python3
"""Download selected public, processed enhancer resources into this folder.

Raw sequencing reads are not part of the default download. For oversized Zenodo
records, the script downloads selected analysis outputs and records optional
archives with their direct file URLs, sizes, and checksums in the manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "download_manifest.tsv"
USER_AGENT = "EnhancerPredictionResearchDataFetcher/1.0 (public academic data)"
ZENODO_LIMIT = 2 * 1024**3
ZENODO_SELECTED_FILES = {
    # Download author-reported and analysis outputs; skip raw reads and the
    # multi-decade-GB uniform/reference bundles.
    "16887276": {"lab_reported_data.tar.gz", "output.tar.gz", "qc.tar.gz"},
}
VISTA_FILES = [
    "allelic.dictionary.csv",
    "allelic_curation.tsv.gz",
    "allelic_curation_munged.tsv.gz",
    "backbone.dictionary.tsv",
    "experiments.tsv.gz",
    "field_descriptions.tsv",
    "images.tsv.gz",
    "locus.tsv.gz",
    "locus_ucsc_hg38.bed",
    "locus_ucsc_mm10.bed",
    "tissue.dictionary.csv",
]
ENCODE_ACCESSIONS = [
    "ENCSR463IRX", "ENCSR460LZI", "ENCSR022GQD", "ENCSR382BVV",
    "ENCSR244FWB", "ENCSR405QCT", "ENCSR203UFY", "ENCSR336MKI",
]

manifest_rows: list[dict[str, str]] = []


def request_bytes(url: str, accept: str = "*/*") -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(req, timeout=60) as response:
        return response.read()


def add_row(source: str, filename: str, size: int | str, status: str,
            url: str, checksum: str = "", note: str = "") -> None:
    manifest_rows.append({
        "source": source,
        "filename": filename,
        "size_bytes": str(size),
        "status": status,
        "url": url,
        "checksum": checksum,
        "note": note,
    })


def download(url: str, destination: Path, source: str,
             expected_checksum: str = "", note: str = "") -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    md5 = hashlib.md5()
    size = 0
    try:
        with urlopen(req, timeout=120) as response, partial.open("wb") as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
                md5.update(block)
                size += len(block)
        if size == 0:
            partial.unlink(missing_ok=True)
            raise ValueError(f"Empty response for {destination.name}; refusing to save a zero-byte file")
        digest = md5.hexdigest()
        if expected_checksum.startswith("md5:") and digest.lower() != expected_checksum[4:].lower():
            partial.unlink(missing_ok=True)
            raise ValueError(f"MD5 mismatch for {destination.name}: {digest}")
        partial.replace(destination)
        add_row(source, destination.name, size, "downloaded", url, digest, note)
        print(f"Downloaded {destination.relative_to(ROOT)} ({size:,} bytes)")
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def download_screen_enhancers() -> None:
    url = "https://downloads.wenglab.org/Registry-V4/GRCh38-cCREs.ELS.bed"
    dest = ROOT / "01_ENCODE4_SCREEN" / "GRCh38-cCREs.ELS.bed"
    if dest.exists():
        add_row("SCREEN ENCODE4", dest.name, dest.stat().st_size, "already_present", url,
                note="Human candidate enhancer-like cCREs (pELS and dELS), GRCh38.")
        return
    download(url, dest, "SCREEN ENCODE4",
             note="Human candidate enhancer-like cCREs (pELS and dELS), GRCh38.")


def download_figshare_mpra() -> None:
    url = "https://ndownloader.figshare.com/files/53009321"
    dest = ROOT / "05_HEMATOPOIESIS_MPRA" / "data_updated2.rda"
    if dest.exists() and dest.stat().st_size > 0:
        add_row("Figshare hematopoiesis MPRA", dest.name, dest.stat().st_size,
                "already_present", url)
        return
    if dest.exists():
        dest.unlink()
        print(f"Removed incomplete zero-byte file; retrying {dest.name}")
    download(url, dest, "Figshare hematopoiesis MPRA",
             note="Quantitative MPRA data across seven mouse HSPC states and K562; synthetic and genomic libraries.")


def download_zenodo_record(record_id: str, folder: str, source: str) -> None:
    api = f"https://zenodo.org/api/records/{record_id}"
    record = json.loads(request_bytes(api, "application/json"))
    files = record.get("files", [])
    total = sum(int(f.get("size", 0)) for f in files)
    if not files:
        add_row(source, "(no files listed)", 0, "no_files", api)
        return
    selected_names = ZENODO_SELECTED_FILES.get(record_id)
    if total > ZENODO_LIMIT and selected_names is None:
        for item in files:
            add_row(source, Path(item["key"]).name, item.get("size", 0), "available_optional",
                    item.get("links", {}).get("self", ""), item.get("checksum", ""),
                    "Optional large Zenodo archive; use download_project_resources.py --group optional.")
        print(f"Skipped Zenodo {record_id}: {total:,} bytes exceeds 2 GiB limit")
        return
    for item in files:
        name = Path(item["key"]).name
        if selected_names is not None and name not in selected_names:
            if name == "raw_data.tar.gz":
                omission_note = "Omitted from this curated download; inspect archive contents before deciding whether it is needed."
            elif name == "uniform_processed_data.tar.gz":
                omission_note = "25.4 GB uniformly reprocessed bundle omitted from this initial download."
            elif name == "reference.tar.gz":
                omission_note = "11.1 GB reference bundle omitted; retrieve only if the analysis requires it."
            else:
                omission_note = "Omitted by the selective download plan."
            add_row(source, name, item.get("size", 0), "available_optional",
                    item.get("links", {}).get("self", ""), item.get("checksum", ""),
                    f"{omission_note} Download on demand with download_project_resources.py --group optional.")
            continue
        dest = ROOT / folder / name
        if dest.exists():
            add_row(source, name, dest.stat().st_size, "already_present",
                    item.get("links", {}).get("self", ""), item.get("checksum", ""))
            continue
        download(item["links"]["self"], dest, source,
                 expected_checksum=item.get("checksum", ""), note=f"Zenodo record {record_id}")


def download_vista_tables() -> None:
    base = "https://gitlab.com/egsb-mfgl/vista-data/-/raw/main/"
    folder = ROOT / "04_VISTA"
    for name in VISTA_FILES:
        dest = folder / name
        url = base + name
        if dest.exists() and dest.stat().st_size > 0:
            add_row("VISTA Enhancer Browser", name, dest.stat().st_size,
                    "already_present", url,
                    note="Official VISTA database export; GitLab main branch.")
            continue
        if dest.exists():
            dest.unlink()
        download(url, dest, "VISTA Enhancer Browser",
                 note="Official VISTA database export; GitLab main branch.")


def download_encode_processed() -> None:
    accepted_formats = {"bed", "bigbed", "bedgraph", "tsv", "csv", "xlsx", "json", "txt"}
    for accession in ENCODE_ACCESSIONS:
        query = urlencode({
            "type": "File",
            "dataset": f"/functional-characterization-experiments/{accession}/",
            "status": "released",
            "format": "json",
            "limit": "all",
        })
        api = f"https://www.encodeproject.org/search/?{query}"
        try:
            data = json.loads(request_bytes(api, "application/json"))
        except Exception as exc:
            add_row(f"ENCODE {accession}", "(metadata query failed)", 0,
                    "metadata_error", api, note=str(exc))
            print(f"Metadata query failed for {accession}: {exc}")
            continue
        files = data.get("@graph", [])
        selected = []
        for item in files:
            fmt = str(item.get("file_format", "")).lower()
            output_type = str(item.get("output_type", "")).lower()
            status = str(item.get("status", ""))
            if status != "released" or fmt not in accepted_formats:
                continue
            if output_type in {"reads", "raw data", "raw reads"}:
                continue
            href = item.get("href")
            if not href:
                continue
            selected.append(item)
        for item in selected:
            accession_id = item.get("accession", "file")
            fmt = str(item.get("file_format", "dat"))
            ext = "." + fmt
            if item.get("file_format_type") == "bed bed9+":
                ext = ".bed"
            name = f"{accession_id}{ext}"
            dest = ROOT / "02_LENTIMPRA_ENCODE_2025" / accession / name
            url = "https://www.encodeproject.org" + item["href"]
            checksum = item.get("md5sum", "")
            if dest.exists():
                add_row(f"ENCODE {accession}", name, dest.stat().st_size,
                        "already_present", url, checksum)
                continue
            download(url, dest, f"ENCODE {accession}",
                     expected_checksum=f"md5:{checksum}" if checksum else "",
                     note=f"Processed {fmt}; {item.get('output_type', 'output type unspecified')}")


def write_manifest() -> None:
    columns = ["source", "filename", "size_bytes", "status", "url", "checksum", "note"]
    with MANIFEST.open("w", encoding="utf-8") as handle:
        handle.write("\t".join(columns) + "\n")
        for row in manifest_rows:
            handle.write("\t".join(row.get(col, "").replace("\t", " ").replace("\n", " ")
                                     for col in columns) + "\n")


def main() -> int:
    jobs = [
        ("SCREEN ENCODE4", lambda: download_screen_enhancers()),
        ("Genome Biology 2025 MPRA/STARR", lambda: download_zenodo_record(
            "16887276", "03_MPRA_STARR_CROSS_ASSAY_2025", "Genome Biology 2025 MPRA/STARR")),
        ("DNABERT-Enhancer models", lambda: download_zenodo_record(
            "19157566", "06_DNABERT_ENHANCER_2026", "DNABERT-Enhancer models")),
        ("VISTA database tables", lambda: download_vista_tables()),
        ("Hematopoiesis MPRA", lambda: download_figshare_mpra()),
        ("ENCODE lentiMPRA processed files", lambda: download_encode_processed()),
    ]
    for label, job in jobs:
        print(f"\n== {label} ==")
        try:
            job()
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
            add_row(label, "(download/query failed)", 0, "error", "", note=str(exc))
            print(f"Stopped this resource after error: {exc}", file=sys.stderr)
    write_manifest()
    print(f"\nManifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
