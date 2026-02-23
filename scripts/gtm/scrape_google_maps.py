#!/usr/bin/env python3
"""
Google Maps Lead Scraper for Personal Trainers
Searches "personal trainer" across top US cities and extracts business data.

Usage:
    pip install outscraper
    export OUTSCRAPER_API_KEY="your_key_here"
    python scrape_google_maps.py

Alternative (free, no API key): Use omkarcloud/google-maps-scraper
    pip install botasaurus google-maps-scraper
    python -m google_maps_scraper "personal trainer" --max-results 100

Output: leads/google_maps_leads.csv
"""

import os
import csv
import json
import time
import sys
from datetime import datetime

# Top 50 US cities by PT density
CITIES = [
    "Los Angeles, CA", "New York, NY", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
    "San Diego, CA", "Dallas, TX", "Austin, TX", "Denver, CO", "Miami, FL",
    "Atlanta, GA", "Seattle, WA", "San Francisco, CA", "Portland, OR", "Nashville, TN",
    "Charlotte, NC", "Tampa, FL", "Minneapolis, MN", "Boston, MA", "Philadelphia, PA",
    "San Antonio, TX", "Columbus, OH", "Indianapolis, IN", "Jacksonville, FL", "Fort Worth, TX",
    "San Jose, CA", "Scottsdale, AZ", "Raleigh, NC", "Virginia Beach, VA", "Oakland, CA",
    "Boise, ID", "Salt Lake City, UT", "Kansas City, MO", "Las Vegas, NV", "St. Louis, MO",
    "Pittsburgh, PA", "Cincinnati, OH", "Orlando, FL", "Sacramento, CA", "Cleveland, OH",
    "Milwaukee, WI", "Honolulu, HI", "Tucson, AZ", "Mesa, AZ", "Omaha, NE",
    "Colorado Springs, CO", "Richmond, VA", "Albuquerque, NM", "Birmingham, AL", "Louisville, KY"
]

SEARCH_QUERIES = [
    "personal trainer",
    "personal training studio",
    "fitness coach",
    "online personal trainer",
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "leads")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "google_maps_leads.csv")

CSV_HEADERS = [
    "business_name", "phone", "email", "website", "address", "city", "state",
    "rating", "review_count", "category", "google_maps_url", "source",
    "scraped_date"
]


def scrape_with_outscraper():
    """Use Outscraper API to scrape Google Maps (paid, reliable)."""
    try:
        from outscraper import ApiClient
    except ImportError:
        print("Outscraper not installed. Run: pip install outscraper")
        return None

    api_key = os.environ.get("OUTSCRAPER_API_KEY")
    if not api_key:
        print("Set OUTSCRAPER_API_KEY environment variable.")
        print("Get your key at: https://outscraper.com/")
        return None

    client = ApiClient(api_key=api_key)
    all_leads = []

    for city in CITIES:
        for query in SEARCH_QUERIES[:2]:  # Start with top 2 queries to save credits
            search_term = f"{query} in {city}"
            print(f"Scraping: {search_term}")

            try:
                results = client.google_maps_search(
                    search_term,
                    limit=50,  # Max results per search
                    language="en",
                    region="US"
                )

                if results and len(results) > 0:
                    for place in results[0] if isinstance(results[0], list) else results:
                        if isinstance(place, dict):
                            lead = {
                                "business_name": place.get("name", ""),
                                "phone": place.get("phone", ""),
                                "email": place.get("email", ""),
                                "website": place.get("site", ""),
                                "address": place.get("full_address", ""),
                                "city": city.split(",")[0].strip(),
                                "state": city.split(",")[1].strip() if "," in city else "",
                                "rating": place.get("rating", ""),
                                "review_count": place.get("reviews", ""),
                                "category": place.get("category", ""),
                                "google_maps_url": place.get("google_maps_url", ""),
                                "source": "google_maps",
                                "scraped_date": datetime.now().isoformat()[:10]
                            }
                            all_leads.append(lead)

                print(f"  Found {len(results[0]) if results and isinstance(results[0], list) else 0} results")
                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"  Error: {e}")
                time.sleep(2)

    return all_leads


def scrape_with_free_method():
    """
    Free alternative using the omkarcloud Google Maps scraper.
    Requires: pip install botasaurus google-maps-scraper
    """
    print("=" * 60)
    print("FREE SCRAPING METHOD")
    print("=" * 60)
    print()
    print("Option 1: Use omkarcloud/google-maps-scraper (free, open source)")
    print("  git clone https://github.com/omkarcloud/google-maps-scraper")
    print("  cd google-maps-scraper")
    print("  python -m google_maps_scraper")
    print()
    print("Option 2: Use Outscraper with free tier (25 free results)")
    print("  1. Sign up at https://outscraper.com/")
    print("  2. Get API key from dashboard")
    print("  3. export OUTSCRAPER_API_KEY='your_key'")
    print("  4. Run this script again")
    print()
    print("Option 3: Manual Google Maps export")
    print("  1. Go to Google Maps")
    print("  2. Search 'personal trainer in [city]'")
    print("  3. Use the G Maps Extractor Chrome extension to export results")
    print("  4. Save as CSV in leads/google_maps_leads.csv")
    print()

    # Generate a search URL helper file
    urls_file = os.path.join(OUTPUT_DIR, "google_maps_search_urls.txt")
    with open(urls_file, "w") as f:
        f.write("# Google Maps Search URLs for Personal Trainers\n")
        f.write("# Open each URL, then use G Maps Extractor to export results\n\n")
        for city in CITIES:
            city_encoded = city.replace(" ", "+").replace(",", "%2C")
            url = f"https://www.google.com/maps/search/personal+trainer+in+{city_encoded}"
            f.write(f"{city}: {url}\n")
    print(f"Search URLs saved to: {urls_file}")

    return None


def deduplicate_leads(leads):
    """Remove duplicate leads based on phone number or business name + city."""
    seen = set()
    unique = []
    for lead in leads:
        key = lead.get("phone", "") or f"{lead['business_name']}_{lead['city']}"
        if key and key not in seen:
            seen.add(key)
            unique.append(lead)
    return unique


def save_leads(leads):
    """Save leads to CSV file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Append to existing file if it exists
    existing = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            reader = csv.DictReader(f)
            existing = list(reader)

    all_leads = existing + leads
    all_leads = deduplicate_leads(all_leads)

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(all_leads)

    print(f"\nSaved {len(all_leads)} leads to {OUTPUT_FILE}")
    print(f"  New: {len(leads)}, Existing: {len(existing)}, After dedup: {len(all_leads)}")


def main():
    print("=" * 60)
    print("FirstRep GTM: Google Maps Personal Trainer Scraper")
    print("=" * 60)
    print(f"Target: {len(CITIES)} cities × {len(SEARCH_QUERIES)} queries")
    print()

    # Try Outscraper first
    leads = scrape_with_outscraper()

    if leads is None:
        # Fall back to free method instructions
        scrape_with_free_method()
        return

    if leads:
        save_leads(leads)
        print(f"\nDone! {len(leads)} leads scraped.")
        print(f"Next step: Run enrich_emails.py to find verified email addresses.")
    else:
        print("No leads found. Check your API key and try again.")


if __name__ == "__main__":
    main()
