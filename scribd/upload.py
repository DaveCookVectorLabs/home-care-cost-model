#!/usr/bin/env python3
"""
Helper script for manual Scribd upload.

Scribd does not publish a stable public API; this script prints the
metadata that should be pasted into the upload form, along with the
pre-verified description, tags, and license.

Usage:
    python scribd/upload.py
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
METADATA = HERE / "metadata.json"
PDF = HERE.parent / "pdfs" / "home-care-cost-model-guide.pdf"


def main():
    with open(METADATA, "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("=" * 70)
    print("Scribd upload helper — Home Care Cost Model")
    print("=" * 70)
    print()
    print(f"PDF path: {PDF}")
    print(f"PDF exists: {PDF.exists()}")
    if PDF.exists():
        print(f"PDF size:  {PDF.stat().st_size:,} bytes")
    print()
    print("Title:")
    print(f"  {meta['title']}")
    print()
    print("Author:")
    print(f"  {meta['author']}")
    print()
    print("Category:")
    print(f"  {meta['category']}")
    print()
    print("Tags:")
    print(f"  {', '.join(meta['tags'])}")
    print()
    print("License:")
    print(f"  {meta['license']}")
    print()
    print("Description:")
    for line in meta['description'].split('. '):
        print(f"  {line}")
    print()
    print("Manual upload: https://www.scribd.com/upload-document")
    print("Log in with davecook1985.")
    print()
    print("Restraint reminder: keep the description to the text above.")
    print("Do not add marketing adjectives or keyword-stuffed tags.")


if __name__ == "__main__":
    main()
