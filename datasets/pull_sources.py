#!/usr/bin/env python3
"""
Fetch raw authoritative data sources into datasets/sources/.

This script is idempotent: re-running it skips files that already exist.
Every downloaded file gets a sibling .source.json sidecar recording the
upstream URL, retrieval ISO timestamp, declared license, and SHA256.

Source catalogue is defined inline in SOURCES below, each entry keyed by
source_id. Keep SOURCES.md in sync with this file.

Running this script:
    python datasets/pull_sources.py              # fetch all sources
    python datasets/pull_sources.py --dry-run    # print what would be fetched
    python datasets/pull_sources.py --verify     # recompute SHA256 on existing files

Author: Dave Cook
License: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SOURCES_DIR = Path(__file__).resolve().parent / "sources"
RATE_LIMIT_SECONDS = 2.0  # be polite to government portals


SOURCES = [
    # --- Statistics Canada ---
    {
        "source_id": "statcan-14-10-0417-01",
        "organisation": "Statistics Canada",
        "filename": "14-10-0417-01_employment_weekly_earnings.csv.landing.html",
        "url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410041701",
        "license": "Statistics Canada Open Licence",
        "format": "html",
    },
    {
        "source_id": "statcan-17-10-0005-01",
        "organisation": "Statistics Canada",
        "filename": "17-10-0005-01_population_estimates.landing.html",
        "url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000501",
        "license": "Statistics Canada Open Licence",
        "format": "html",
    },
    {
        "source_id": "statcan-18-10-0004-01",
        "organisation": "Statistics Canada",
        "filename": "18-10-0004-01_cpi_health_personal_care.landing.html",
        "url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401",
        "license": "Statistics Canada Open Licence",
        "format": "html",
    },
    {
        "source_id": "statcan-gss-2018-caregiving",
        "organisation": "Statistics Canada",
        "filename": "gss-2018-caregiving-cycle-32.landing.html",
        "url": "https://www150.statcan.gc.ca/n1/en/catalogue/89M0033X",
        "license": "Statistics Canada Open Licence",
        "format": "html",
    },
    # --- CIHI ---
    {
        "source_id": "cihi-hcrs-indicators",
        "organisation": "CIHI",
        "filename": "hcrs-metadata.landing.html",
        "url": "https://www.cihi.ca/en/home-care-reporting-system-metadata",
        "license": "CIHI Terms of Use",
        "format": "html",
    },
    {
        "source_id": "cihi-your-health-system",
        "organisation": "CIHI",
        "filename": "your-health-system-home-care.landing.html",
        "url": "https://yourhealthsystem.cihi.ca",
        "license": "CIHI Terms of Use",
        "format": "html",
    },
    # --- CRA ---
    {
        "source_id": "cra-s1-f1-c1-metc",
        "organisation": "Canada Revenue Agency",
        "filename": "s1-f1-c1-medical-expense-tax-credit.html",
        "url": "https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios-index/series-1-individuals/folio-1-health-medical/income-tax-folio-s1-f1-c1-medical-expense-tax-credit.html",
        "license": "Government of Canada — attribution required",
        "format": "html",
    },
    {
        "source_id": "cra-s1-f1-c2-dtc",
        "organisation": "Canada Revenue Agency",
        "filename": "s1-f1-c2-disability-tax-credit.html",
        "url": "https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios-index/series-1-individuals/folio-1-health-medical/income-tax-folio-s1-f1-c2-disability-tax-credit.html",
        "license": "Government of Canada — attribution required",
        "format": "html",
    },
    {
        "source_id": "cra-canada-caregiver-credit",
        "organisation": "Canada Revenue Agency",
        "filename": "canada-caregiver-amount.html",
        "url": "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses/canada-caregiver-amount.html",
        "license": "Government of Canada — attribution required",
        "format": "html",
    },
    # --- Veterans Affairs Canada ---
    {
        "source_id": "vac-vip-2026",
        "organisation": "Veterans Affairs Canada",
        "filename": "vip-program.html",
        "url": "https://www.veterans.gc.ca/en/health-support/physical-health-and-wellness/compensation-illness-injury/veterans-independence-program",
        "license": "Government of Canada",
        "format": "html",
    },
    # --- Indigenous Services Canada ---
    {
        "source_id": "isc-fnihb-home-community-care",
        "organisation": "Indigenous Services Canada",
        "filename": "fnihb-home-community-care.html",
        "url": "https://www.sac-isc.gc.ca/eng/1100100035250/1533317440443",
        "license": "Government of Canada",
        "format": "html",
    },
    # --- Provincial programs ---
    {
        "source_id": "hccss-ontario",
        "organisation": "Ontario Ministry of Health",
        "filename": "hccss-ontario.html",
        "url": "https://www.ontario.ca/page/homecare-seniors",
        "license": "Open Government Licence – Ontario",
        "format": "html",
    },
    {
        "source_id": "gov-bc-home-community-care",
        "organisation": "Government of British Columbia",
        "filename": "bc-home-community-care.html",
        "url": "https://www2.gov.bc.ca/gov/content/health/accessing-health-care/home-community-care",
        "license": "Open Government Licence – British Columbia",
        "format": "html",
    },
    {
        "source_id": "ahs-continuing-care-at-home",
        "organisation": "Alberta Health Services",
        "filename": "ahs-continuing-care.html",
        "url": "https://www.albertahealthservices.ca/cc/page15517.aspx",
        "license": "Open Government Licence – Alberta",
        "format": "html",
    },
    {
        "source_id": "quebec-clsc-sad",
        "organisation": "Gouvernement du Québec",
        "filename": "quebec-soutien-a-domicile.html",
        "url": "https://www.quebec.ca/en/health/health-system-and-services/home-support/home-care-services",
        "license": "Creative Commons Attribution 4.0 Quebec",
        "format": "html",
    },
    {
        "source_id": "sha-home-care",
        "organisation": "Saskatchewan Health Authority",
        "filename": "sha-home-care.html",
        "url": "https://www.saskhealthauthority.ca/our-services/services-directory/home-care",
        "license": "Government of Saskatchewan",
        "format": "html",
    },
    {
        "source_id": "gov-mb-home-care",
        "organisation": "Government of Manitoba",
        "filename": "manitoba-home-care.html",
        "url": "https://www.gov.mb.ca/health/homecare",
        "license": "Government of Manitoba",
        "format": "html",
    },
    {
        "source_id": "nshealth-home-care",
        "organisation": "Nova Scotia Health",
        "filename": "nova-scotia-home-care.html",
        "url": "https://novascotia.ca/dhw/ccs/home-care.asp",
        "license": "Government of Nova Scotia",
        "format": "html",
    },
    {
        "source_id": "gnb-extra-mural-program",
        "organisation": "Government of New Brunswick",
        "filename": "new-brunswick-extra-mural.html",
        "url": "https://www2.gnb.ca/content/gnb/en/departments/health/MedicarePrescriptionDrugPlan/TheExtraMuralProgram.html",
        "license": "Government of New Brunswick",
        "format": "html",
    },
    {
        "source_id": "pei-home-care",
        "organisation": "Government of Prince Edward Island",
        "filename": "pei-home-care.html",
        "url": "https://www.princeedwardisland.ca/en/information/health-pei/home-care",
        "license": "Government of PEI",
        "format": "html",
    },
    {
        "source_id": "nlh-home-care",
        "organisation": "Newfoundland and Labrador Health Services",
        "filename": "nl-home-support.html",
        "url": "https://www.nlhealthservices.ca/find-care/community-based-care/home-support-program/",
        "license": "Government of Newfoundland and Labrador",
        "format": "html",
    },
    {
        "source_id": "yukon-home-care",
        "organisation": "Government of Yukon",
        "filename": "yukon-home-care.html",
        "url": "https://yukon.ca/en/health-and-wellness/care-services/apply-home-care",
        "license": "Government of Yukon",
        "format": "html",
    },
    {
        "source_id": "gnwt-home-community-care",
        "organisation": "Government of Northwest Territories",
        "filename": "gnwt-home-community-care.html",
        "url": "https://www.hss.gov.nt.ca/en/services/home-and-community-care",
        "license": "Government of Northwest Territories",
        "format": "html",
    },
    {
        "source_id": "gn-home-community-care",
        "organisation": "Government of Nunavut",
        "filename": "nunavut-home-community-care.html",
        "url": "https://www.gov.nu.ca/health/information/home-and-community-care",
        "license": "Government of Nunavut",
        "format": "html",
    },
    # --- Non-governmental ---
    {
        "source_id": "chca-high-value-home-care",
        "organisation": "Canadian Home Care Association",
        "filename": "chca-publications.landing.html",
        "url": "https://cdnhomecare.ca/category/publications/",
        "license": "CHCA Terms of Use",
        "format": "html",
    },
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def dest_path(source: dict) -> Path:
    org = source["organisation"].replace(" ", "_").replace(",", "")
    return SOURCES_DIR / org / source["filename"]


def sidecar_path(data_path: Path) -> Path:
    return data_path.with_suffix(data_path.suffix + ".source.json")


def fetch_one(source: dict, dry_run: bool = False) -> tuple[str, Path]:
    target = dest_path(source)
    if target.exists():
        return ("skip", target)
    if dry_run:
        return ("would-fetch", target)

    target.parent.mkdir(parents=True, exist_ok=True)
    req = Request(
        source["url"],
        headers={
            "User-Agent": (
                "home-care-cost-model/0.1 (+https://github.com/"
                "DaveCookVectorLabs/home-care-cost-model) "
                "research data collection"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml,"
                      "application/pdf,text/csv,*/*;q=0.8",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
    except (URLError, HTTPError) as e:
        stub = (
            f"# Placeholder for {source['source_id']}\n"
            f"# URL: {source['url']}\n"
            f"# Fetch failed at {datetime.now(timezone.utc).isoformat()}: {e}\n"
            f"# The metadata sidecar still records the upstream URL for "
            f"citation purposes.\n"
        ).encode("utf-8")
        with open(target, "wb") as f:
            f.write(stub)
        write_sidecar(source, target, fetch_status=f"failed: {e}")
        return ("failed", target)

    with open(target, "wb") as f:
        f.write(data)
    write_sidecar(source, target, fetch_status="ok")
    return ("ok", target)


def write_sidecar(source: dict, data_path: Path, fetch_status: str):
    sidecar = {
        "source_id": source["source_id"],
        "organisation": source["organisation"],
        "upstream_url": source["url"],
        "license": source["license"],
        "format": source["format"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "fetch_status": fetch_status,
        "sha256": sha256_of(data_path),
        "byte_size": data_path.stat().st_size,
    }
    with open(sidecar_path(data_path), "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2, sort_keys=True)


def verify_existing():
    """Recompute SHA256 on all existing sources and flag mismatches."""
    problems = 0
    for source in SOURCES:
        target = dest_path(source)
        if not target.exists():
            print(f"  missing: {source['source_id']}")
            problems += 1
            continue
        sidecar = sidecar_path(target)
        if not sidecar.exists():
            print(f"  missing sidecar: {source['source_id']}")
            problems += 1
            continue
        with open(sidecar, "r", encoding="utf-8") as f:
            meta = json.load(f)
        actual = sha256_of(target)
        if actual != meta.get("sha256"):
            print(f"  sha256 drift: {source['source_id']}")
            problems += 1
    if problems == 0:
        print(f"all {len(SOURCES)} sources verified")
    else:
        print(f"{problems} issue(s) found")
    return problems


def main():
    parser = argparse.ArgumentParser(description="Fetch authoritative sources")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        rc = verify_existing()
        sys.exit(0 if rc == 0 else 1)

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    counts = {"ok": 0, "skip": 0, "failed": 0, "would-fetch": 0}
    for i, source in enumerate(SOURCES):
        status, path = fetch_one(source, dry_run=args.dry_run)
        counts[status] = counts.get(status, 0) + 1
        print(f"  [{i+1}/{len(SOURCES)}] {status:12s} {source['source_id']}")
        if status == "ok" and i + 1 < len(SOURCES):
            time.sleep(RATE_LIMIT_SECONDS)

    print()
    print(f"Summary: {counts}")


if __name__ == "__main__":
    main()
