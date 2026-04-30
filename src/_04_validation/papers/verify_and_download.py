#!/usr/bin/env python3
"""
Verify and download scientific papers for RAG validation.

Usage:
    python verify_and_download.py --verify       # Verify DOIs only
    python verify_and_download.py --download    # Download PDFs
    python verify_and_download.py --all         # Both
"""

import os
import re
import json
import hashlib
import requests
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

PAPERS_DIR = Path(__file__).parent
CROSSREF_API = "https://api.crossref.org/works/"
USER_AGENT = "RAG-Recipe-Validator/1.0 (mailto:fede@example.com)"


@dataclass
class PaperRef:
    """Represents a paper reference found in .md files."""
    doi: Optional[str]
    title: str
    year: Optional[str]
    source_file: str
    pdf_exists: bool = False
    crossref_valid: bool = False
    download_url: Optional[str] = None
    error: Optional[str] = None


def extract_dois_from_file(md_path: Path) -> list[dict]:
    """Extract DOIs and references from a markdown file."""
    content = md_path.read_text(encoding='utf-8')
    refs = []

    doi_pattern = r'10\.\d{4,}/[A-Za-z0-9\.\-_\(\)]+'
    year_pattern = r'\((\d{4})\)'
    
    for line in content.split('\n'):
        doi_match = re.search(doi_pattern, line)
        year_match = re.search(year_pattern, line)

        if doi_match:
            doi = doi_match.group(0).rstrip('.,')
            title_match = re.search(r'"([^"]+)"', line)
            title = title_match.group(1) if title_match else "Unknown"
            
            refs.append({
                'doi': doi,
                'title': title,
                'year': year_match.group(1) if year_match else None,
                'source': md_path.name
            })

    return refs


def scan_all_files() -> list[dict]:
    """Scan all .md files in papers directory."""
    all_refs = []
    md_files = list(PAPERS_DIR.glob("**/*.md"))
    
    for md_file in md_files:
        if md_file.name == "README.md":
            continue
        
        # Extract DOIs
        refs = extract_dois_from_file(md_file)
        
        # Extract URL-based PDF references
        content = md_file.read_text(encoding='utf-8')
        for line in content.split('\n'):
            if 'Available at:' in line or 'air.unimi.it' in line:
                url_match = re.search(r'(https?://[^\s]+\.pdf)', line)
                if url_match:
                    pdf_url = url_match.group(1)
                    year_match = re.search(r'\((\d{4})\)', line)
                    author_match = re.search(r'^([^,]+)', line)
                    
                    refs.append({
                        'doi': None,
                        'pdf_url': pdf_url,
                        'title': author_match.group(1) + ' ' + (year_match.group(1) if year_match else 'Unknown') if author_match else 'URL-based reference',
                        'year': year_match.group(1) if year_match else None,
                        'source': md_file.name,
                        'url_based': True
                    })
                    break
        
        for ref in refs:
            ref['category'] = md_file.parent.name
            ref['relative_dir'] = str(md_file.parent.relative_to(PAPERS_DIR))
        all_refs.extend(refs)
    
    return all_refs


def verify_doi(doi: str) -> dict:
    """Verify DOI via CrossRef API."""
    try:
        url = CROSSREF_API + doi
        headers = {'User-Agent': USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            item = data.get('message', {})
            return {
                'valid': True,
                'title': item.get('title', [''])[0] if item.get('title') else '',
                'author': ', '.join([a.get('family', '') for a in item.get('author', [])[:3]]),
                'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                'year': item.get('published-print', {}).get('date-parts', [[None]])[0][0],
                'type': item.get('type', 'article'),
            }
        elif resp.status_code == 404:
            return {'valid': False, 'error': 'DOI not found in CrossRef'}
        else:
            return {'valid': False, 'error': f'HTTP {resp.status_code}'}
    except Exception as e:
        return {'valid': False, 'error': str(e)}


def find_pdf_url(doi: str, title: str) -> Optional[str]:
    """Try to find a direct PDF URL for the DOI."""
    
    # Try direct MDPI PDF first 
    mdpi_match = re.search(r'10\.3390/([a-z0-9-]+)/(\d+)/(\d+)', doi)
    if mdpi_match:
        journal, vol, page = mdpi_match.groups()
        direct_pdf = f"https://www.mdpi.com/{journal}/{vol}/{page}/pdf"
        try:
            resp = requests.get(direct_pdf, timeout=15, headers={'User-Agent': USER_AGENT})
            if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('application/pdf'):
                return direct_pdf
        except:
            pass
    
    # Try direct Wiley PDF (some are open access)
    wiley_match = re.search(r'10\.1111/([a-z.]+)', doi)
    if wiley_match:
        article_id = wiley_match.group(1)
        wiley_pdf = f"https://onlinelibrary.wiley.com/doi/pdfdirect/{article_id}"
        try:
            resp = requests.get(wiley_pdf, timeout=15, headers={'User-Agent': USER_AGENT})
            if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('application/pdf'):
                return wiley_pdf
        except:
            pass
    
    # Try via DOI redirect
    try:
        resp = requests.head(f"https://doi.org/{doi}", timeout=15, allow_redirects=True)
        if resp.status_code in (200, 303):
            final_url = resp.url
            
            if 'sciencedirect' in final_url:
                return final_url.replace('article', 'pdf')
            elif 'mdpi.com' in final_url:
                return final_url.replace('/article/', '/pdf/')
            return final_url
    except:
        pass
    
    # Try Jina AI for open access content
    try:
        resp = requests.get(f"https://r.jina.ai/http://doi.org/{doi}", timeout=10)
        if resp.status_code == 200:
            for pdf_url in re.findall(r'https?://[^\s]+\.pdf', resp.text):
                if 'pdf' in pdf_url.lower():
                    return pdf_url
    except:
        pass
    
    return None


def download_pdf(url: str, dest_path: Path) -> bool:
    """Download PDF to destination."""
    try:
        headers = {'User-Agent': USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        
        if resp.status_code == 200:
            content = resp.content
            # Verify it's actually a PDF (check magic bytes)
            if content[:4] == b'%PDF':
                dest_path.write_bytes(content)
                return True
            else:
                print(f"  Warning: Not a PDF (got {content[:20]})")
    except Exception as e:
        print(f"  Download failed: {e}")
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Verify and download papers')
    parser.add_argument('--verify', action='store_true', help='Verify DOIs only')
    parser.add_argument('--download', action='store_true', help='Download PDFs')
    parser.add_argument('--all', action='store_true', help='Verify and download')
    parser.add_argument('--report', action='store_true', help='Generate report')
    
    args = parser.parse_args()
    
    if args.download:
        args.verify = True

    print("=" * 60)
    print("SCANNING FOR REFERENCES")
    print("=" * 60)
    
    refs = scan_all_files()
    print(f"Found {len(refs)} references across .md files\n")
    
    inventory = []
    for ref in refs:
        print(f"Category: {ref['category']}")
        print(f"  DOI: {ref['doi']}")
        
        if args.verify or args.all:
            print(f"  Verifying with CrossRef...")
            result = verify_doi(ref['doi'])
            ref['crossref_valid'] = result.get('valid', False)
            
            if result.get('valid'):
                ref['crossref_title'] = result.get('title', '')
                ref['crossref_year'] = result.get('year')
                ref['crossref_journal'] = result.get('journal', '')
                print(f"    ✓ Valid: {result.get('title', '')[:60]}...")
            else:
                print(f"    ✗ Invalid: {result.get('error', 'Unknown error')}")
        else:
            ref['crossref_valid'] = None
        
        # Build expected filename and check
        year_str = ref.get('year', 'unknown') or 'unknown'
        expected_filename = f"{year_str}_{ref['doi'].replace('/', '_')}.pdf"
        pdf_path = PAPERS_DIR / ref['relative_dir'] / expected_filename
        
        # Only try fuzzy matching for specific known papers
        if not pdf_path.exists() and ref.get('doi'):
            dir_path = PAPERS_DIR / ref['relative_dir']
            for existing_pdf in dir_path.glob('*.pdf'):
                pdf_name = existing_pdf.stem.lower()
                year = ref.get('year', '')
                title = ref.get('crossref_title', '').lower()
                journal = ref.get('crossref_journal', '').lower()
                
                # Masi 2023 pizza (foods journal)
                if year and year in existing_pdf.name:
                    if 'masi' in pdf_name and 'foods' in journal:
                        pdf_path = existing_pdf
                        break
                # Li 2022 starch 
                if 'li' in pdf_name and 'starch' in title and '2022' in existing_pdf.name:
                    pdf_path = existing_pdf
                    break
        
        ref['pdf_exists'] = pdf_path.exists()
        
        if ref['pdf_exists']:
            print(f"    ✓ PDF already exists: {pdf_path.name}")
        else:
            print(f"    - PDF not found")
        
        if args.download and ref.get('crossref_valid'):
            pdf_url = find_pdf_url(ref['doi'], ref.get('title', ''))
            if pdf_url:
                print(f"    → Downloading from {pdf_url[:60]}...")
                success = download_pdf(pdf_url, pdf_path)
                ref['download_success'] = success
                ref['pdf_exists'] = success
                print(f"    {'✓ Downloaded' if success else '✗ Failed'}")
        
        print()
        inventory.append(ref)
    
    print("=" * 60)
    print("INVENTORY SUMMARY")
    print("=" * 60)
    
    total = len(inventory)
    valid = sum(1 for r in inventory if r.get('crossref_valid') == True)
    with_pdf = sum(1 for r in inventory if r.get('pdf_exists'))
    
    print(f"Total references: {total}")
    print(f"Valid DOIs: {valid} ({valid/total*100:.1f}%)")
    print(f"Have PDF: {with_pdf} ({with_pdf/total*100:.1f}%)")
    
    report_path = PAPERS_DIR / "inventory.json"
    with open(report_path, 'w') as f:
        json.dump(inventory, f, indent=2)
    print(f"\nSaved inventory to: {report_path}")


if __name__ == "__main__":
    main()