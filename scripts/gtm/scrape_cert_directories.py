#!/usr/bin/env python3
"""
Certification Directory Scraper for Personal Trainers
Searches NASM, ACE, NSCA, and USREPS directories for certified trainers.

Usage:
    python scrape_cert_directories.py

Output: leads/cert_directory_leads.csv

Note: These directories have rate limits. Be respectful — add delays between requests.
Always check each directory's Terms of Service before scraping.
"""

import os
import csv
import json
import time
import sys
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Required packages not installed. Run:")
    print("  pip install requests beautifulsoup4")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "leads")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "cert_directory_leads.csv")

CSV_HEADERS = [
    "name", "certification", "location", "city", "state", "website",
    "email", "phone", "specialties", "directory_url", "source",
    "scraped_date"
]

# US States for systematic search
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

# Major zip codes for geo-based searches (one per major metro)
MAJOR_ZIPS = [
    "90001", "10001", "60601", "77001", "85001",  # LA, NYC, Chicago, Houston, Phoenix
    "92101", "75201", "78701", "80201", "33101",  # SD, Dallas, Austin, Denver, Miami
    "30301", "98101", "94101", "97201", "37201",  # Atlanta, Seattle, SF, Portland, Nashville
    "28201", "33601", "55401", "02101", "19101",  # Charlotte, Tampa, Minneapolis, Boston, Philly
]

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})


def scrape_ace_directory():
    """
    Scrape ACE (American Council on Exercise) Find a Pro directory.
    URL: https://www.acefitness.org/resources/everyone/find-ace-pro/

    ACE uses an API endpoint for their directory search.
    """
    print("\n--- Scraping ACE Directory ---")
    leads = []

    # ACE uses a search API — try common patterns
    base_url = "https://www.acefitness.org/resources/everyone/find-ace-pro/"

    print(f"  ACE Directory URL: {base_url}")
    print("  ACE uses dynamic JavaScript loading.")
    print("  For automated scraping, use one of these approaches:")
    print()
    print("  Option 1: Use Apify's ACE Scraper")
    print("    Visit: https://apify.com/store and search for 'ACE fitness'")
    print()
    print("  Option 2: Use Selenium/Playwright")
    print("    pip install playwright && playwright install")
    print("    Then use a headless browser to interact with the search form")
    print()
    print("  Option 3: Manual search + export")
    print("    1. Go to the ACE directory URL above")
    print("    2. Search by zip code for each major metro")
    print("    3. Copy results to a spreadsheet")
    print()

    # Save search URLs for manual method
    urls = []
    for zip_code in MAJOR_ZIPS:
        urls.append(f"{base_url}?zipcode={zip_code}&distance=25")

    return leads, urls


def scrape_nasm_directory():
    """
    Scrape NASM (National Academy of Sports Medicine) directory.
    URL: https://directory.nasm.org/
    """
    print("\n--- Scraping NASM Directory ---")
    leads = []

    base_url = "https://directory.nasm.org/"

    print(f"  NASM Directory URL: {base_url}")
    print("  Searching by state...")

    # NASM directory may use an API — try to find it
    for state in US_STATES[:5]:  # Start with first 5 states as test
        try:
            # Try the search page
            search_url = f"{base_url}?state={state}"
            print(f"  Searching state: {state}")

            response = session.get(search_url, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Look for trainer cards/listings
                # The exact selectors depend on the page structure
                trainer_cards = soup.select(".trainer-card, .result-card, .professional-card, .listing")

                for card in trainer_cards:
                    name_el = card.select_one("h2, h3, .name, .trainer-name")
                    location_el = card.select_one(".location, .city, .address")

                    if name_el:
                        lead = {
                            "name": name_el.get_text(strip=True),
                            "certification": "NASM-CPT",
                            "location": location_el.get_text(strip=True) if location_el else "",
                            "city": "",
                            "state": state,
                            "website": "",
                            "email": "",
                            "phone": "",
                            "specialties": "",
                            "directory_url": search_url,
                            "source": "nasm_directory",
                            "scraped_date": datetime.now().isoformat()[:10]
                        }
                        leads.append(lead)

                print(f"    Found {len(trainer_cards)} results")

            time.sleep(2)  # Be respectful of rate limits

        except Exception as e:
            print(f"    Error for {state}: {e}")
            time.sleep(3)

    return leads


def scrape_nsca_directory():
    """
    Scrape NSCA (National Strength and Conditioning Association) directory.
    URL: https://directory.nsca.com/
    """
    print("\n--- Scraping NSCA Directory ---")
    leads = []

    print("  NSCA Directory URL: https://directory.nsca.com/")
    print("  NSCA uses a JavaScript-based search form.")
    print()
    print("  Recommended approach:")
    print("  1. Go to https://directory.nsca.com/")
    print("  2. Search by state/zip for each target area")
    print("  3. Export results")
    print()

    return leads


def generate_search_guide():
    """
    Generate a comprehensive guide for manual/semi-automated directory scraping.
    """
    guide_file = os.path.join(OUTPUT_DIR, "directory_scraping_guide.md")

    guide = """# Certification Directory Scraping Guide

## Automated Scraping (Recommended)

### Using Apify (Easiest, ~$50 for full scrape)

1. Sign up at https://apify.com/ (free trial available)
2. Use the **Web Scraper** actor for each directory
3. Configure for each directory:

#### NASM Directory
- URL: https://directory.nasm.org/
- Search each state systematically
- Extract: name, location, certification, contact info

#### ACE Directory
- URL: https://www.acefitness.org/resources/everyone/find-ace-pro/
- Search each zip code in MAJOR_ZIPS list
- Extract: name, location, certification, specialties

#### NSCA Directory
- URL: https://directory.nsca.com/
- Search by state
- Extract: name, credentials, location

#### USREPS Registry
- URL: https://usreps.org/registry/
- 130,000+ registered professionals
- Search by state and credential type

### Using Playwright (Free, requires coding)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Example: NASM Directory
    page.goto("https://directory.nasm.org/")

    # Fill in search form
    page.fill('input[name="state"]', 'CA')
    page.click('button[type="submit"]')

    # Wait for results
    page.wait_for_selector('.result-card')

    # Extract data
    results = page.query_selector_all('.result-card')
    for result in results:
        name = result.query_selector('.name').inner_text()
        print(name)

    browser.close()
```

## Manual Method (Free, time-consuming)

### Step 1: Search Each Directory

Open each URL and search by location:

"""

    for i, zip_code in enumerate(MAJOR_ZIPS):
        city_names = [
            "Los Angeles", "New York", "Chicago", "Houston", "Phoenix",
            "San Diego", "Dallas", "Austin", "Denver", "Miami",
            "Atlanta", "Seattle", "San Francisco", "Portland", "Nashville",
            "Charlotte", "Tampa", "Minneapolis", "Boston", "Philadelphia"
        ]
        city = city_names[i] if i < len(city_names) else zip_code
        guide += f"**{city} ({zip_code}):**\n"
        guide += f"- NASM: https://directory.nasm.org/?zip={zip_code}\n"
        guide += f"- ACE: https://www.acefitness.org/resources/everyone/find-ace-pro/?zipcode={zip_code}\n"
        guide += f"- NSCA: https://directory.nsca.com/?zip={zip_code}\n\n"

    guide += """
### Step 2: Export Results

For each search:
1. Select all results on the page
2. Copy to a spreadsheet (Google Sheets or Excel)
3. Clean up columns to match: name, certification, city, state, website, email, phone

### Step 3: Combine and Deduplicate

1. Combine all spreadsheets into one master file
2. Remove duplicates (same name + city)
3. Save as leads/cert_directory_leads.csv

## Expected Results

| Directory | Expected Leads |
|-----------|---------------|
| NASM | 500-1,000 |
| ACE | 400-800 |
| NSCA | 200-500 |
| USREPS | 500-1,000 |
| **Total** | **1,600-3,300** |
"""

    with open(guide_file, "w") as f:
        f.write(guide)

    print(f"\nScraping guide saved to: {guide_file}")
    return guide_file


def save_leads(leads):
    """Save leads to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not leads:
        print("No leads to save.")
        return

    # Append to existing file
    existing = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            reader = csv.DictReader(f)
            existing = list(reader)

    all_leads = existing + leads

    # Deduplicate by name + state
    seen = set()
    unique = []
    for lead in all_leads:
        key = f"{lead['name']}_{lead['state']}"
        if key not in seen:
            seen.add(key)
            unique.append(lead)

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(unique)

    print(f"Saved {len(unique)} leads to {OUTPUT_FILE}")


def main():
    print("=" * 60)
    print("FirstRep GTM: Certification Directory Scraper")
    print("=" * 60)

    all_leads = []

    # Try NASM
    nasm_leads = scrape_nasm_directory()
    all_leads.extend(nasm_leads)

    # ACE (usually requires browser automation)
    ace_leads, ace_urls = scrape_ace_directory()
    all_leads.extend(ace_leads)

    # NSCA
    nsca_leads = scrape_nsca_directory()
    all_leads.extend(nsca_leads)

    # Save whatever we got
    if all_leads:
        save_leads(all_leads)

    # Always generate the guide for manual/Apify approach
    generate_search_guide()

    print(f"\nTotal leads collected: {len(all_leads)}")
    print("\nFor best results, use the Apify or Playwright methods")
    print("described in leads/directory_scraping_guide.md")


if __name__ == "__main__":
    main()
