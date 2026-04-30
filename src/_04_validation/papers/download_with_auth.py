#!/usr/bin/env python3
"""
Download PDFs using your institutional credentials.

Usage:
    export WILEY_USER="your@email.com"
    export WILEY_PASS="your_password"
    python download_with_auth.py
"""

import os
import requests
from pathlib import Path

PAPERS_DIR = Path(__file__).parent

USER = os.environ.get('WILEY_USER')
PASS = os.environ.get('WILEY_PASS')

PAPERS_TO_DOWNLOAD = [
    # (category_folder, doi, filename)
    ("pizza_chemistry", "10.1111/jtxs.12311", "Almeida_2018_pizza_soy_fiber.pdf"),
    ("starch_gelatinization", "10.1016/j.carbpol.2022.119735", "Li_2022_starch_gelatinization.pdf"),
    ("heat_mass_transfer", "10.1016/j.jfoodeng.2008.09.037", "Purlis_2009_bread_baking.pdf"),
    ("thermal_properties", "10.1016/0260-8774(89)90039-3", "Rask_1989_thermal_properties.pdf"),
    ("protein_chemistry", "10.1016/j.ijbiomac.2020.11.092", "Cho_2021_gluten_denaturation.pdf"),
    ("chemistry", "10.1016/j.jfoodeng.2020.110351", "Bot_2021_fat_crystallization.pdf"),
    ("starch_gelatinization", "10.1016/0008-6215(92)85063-6", "Cooke_1992_starch_gelatinization.pdf"),
]


def download_elsevier(doi: str, dest: Path) -> bool:
    """Download via Elsevier/ScienceDirect."""
    url = f"https://doi.org/{doi}"
    session = requests.Session()
    
    # First get the redirect URL
    resp = session.head(url, allow_redirects=True, timeout=30)
    if resp.status_code != 200:
        print(f"  ✗ Initial request failed: {resp.status_code}")
        return False
    
    final_url = resp.url
    print(f"  → Redirect: {final_url[:50]}...")
    
    # Try to get PDF directly
    pdf_url = final_url.replace('/article/', '/pdf/')
    resp = session.get(pdf_url, timeout=60, stream=True)
    
    if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('application/pdf'):
        content = resp.content
        if content[:4] == b'%PDF':
            dest.write_bytes(content)
            print(f"  ✓ Saved: {dest.stat().st_size / 1024:.1f} KB")
            return True
    
    print(f"  ✗ PDF not accessible (HTTP {resp.status_code})")
    return False


def download_wiley(doi: str, dest: Path) -> bool:
    """Download via Wiley with credentials."""
    if not USER or not PASS:
        print("  ⚠ No credentials (set WILEY_USER/WILEY_PASS)")
        return False
    
    url = f"https://doi.org/{doi}"
    session = requests.Session()
    
    # First get the redirect
    resp = session.head(url, allow_redirects=True, timeout=30)
    if resp.status_code != 200:
        print(f"  ✗ Initial request failed: {resp.status_code}")
        return False
    
    # Try direct PDF first
    doi_part = doi.replace('.', '%2E')
    pdf_url = f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi_part}"
    
    resp = session.get(pdf_url, timeout=60, stream=True,
                       auth=(USER, PASS))
    
    if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('application/pdf'):
        content = resp.content
        if content[:4] == b'%PDF':
            dest.write_bytes(content)
            print(f"  ✓ Saved: {dest.stat().st_size / 1024:.1f} KB")
            return True
    
    print(f"  ✗ PDF not accessible (HTTP {resp.status_code})")
    return False


def main():
    if not USER:
        print("Set credentials first:")
        print("  export WILEY_USER='your@email.com'")
        print("  export WILEY_PASS='your_password'")
        print()
    
    print("=" * 60)
    print("DOWNLOAD PAYWALLED PDFs")
    print(f"Credentials: {'✓ Set' if USER else '✗ Not set'}")
    print("=" * 60)
    
    for category, doi, filename in PAPERS_TO_DOWNLOAD:
        dest = PAPERS_DIR / category / filename
        
        # Skip if exists
        if dest.exists():
            print(f"Skip {filename} - already exists")
            continue
        
        print(f"\n--- {category}: {doi} ---")
        print(f"  File: {filename}")
        
        # Determine publisher based on DOI
        if 'wiley' in doi.lower() or 'jtxs' in doi:
            success = download_wiley(doi, dest)
        else:
            success = download_elsevier(doi, dest)
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()