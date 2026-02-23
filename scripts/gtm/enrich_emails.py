#!/usr/bin/env python3
"""
Email Enrichment & Verification Pipeline
Takes scraped leads with website URLs and finds/verifies email addresses.

Usage:
    export HUNTER_API_KEY="your_key_here"
    python enrich_emails.py --input leads/google_maps_leads.csv --output leads/enriched_leads.csv

Requires:
    pip install requests

API Keys needed (get free tiers):
    - Hunter.io: 25 free searches/month (https://hunter.io)
    - OR Apollo.io: 50 free credits/month (https://apollo.io)
"""

import os
import csv
import json
import time
import argparse
import sys
from datetime import datetime
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Run: pip install requests")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "leads")


def extract_domain(website_url):
    """Extract domain from a URL."""
    if not website_url:
        return None

    # Add scheme if missing
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    try:
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path
        # Remove www.
        domain = domain.replace("www.", "")
        # Remove trailing slashes
        domain = domain.rstrip("/")

        # Skip social media and common platforms
        skip_domains = [
            "facebook.com", "instagram.com", "twitter.com", "linkedin.com",
            "youtube.com", "tiktok.com", "yelp.com", "google.com",
            "wix.com", "squarespace.com", "wordpress.com", "linktree.com"
        ]

        for skip in skip_domains:
            if skip in domain:
                return None

        return domain
    except Exception:
        return None


def find_email_hunter(domain, api_key):
    """
    Use Hunter.io to find emails for a domain.
    Free tier: 25 searches/month.
    Paid (Starter): $49/month for 500 searches.
    """
    url = f"https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": 5
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "data" in data and "emails" in data["data"]:
            emails = data["data"]["emails"]
            if emails:
                # Prefer personal emails, then info/hello/contact
                for email in emails:
                    if email.get("type") == "personal":
                        return email["value"], email.get("confidence", 0)

                # Fall back to first email
                return emails[0]["value"], emails[0].get("confidence", 0)

        return None, 0
    except Exception as e:
        print(f"  Hunter error for {domain}: {e}")
        return None, 0


def verify_email_hunter(email, api_key):
    """
    Verify an email address using Hunter.io.
    Returns: "valid", "invalid", "accept_all", or "unknown"
    """
    url = f"https://api.hunter.io/v2/email-verifier"
    params = {
        "email": email,
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "data" in data:
            return data["data"].get("status", "unknown")

        return "unknown"
    except Exception:
        return "unknown"


def find_email_apollo(first_name, last_name, domain, api_key):
    """
    Use Apollo.io to find an email.
    Free tier: 50 credits/month.
    """
    url = "https://api.apollo.io/api/v1/people/match"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key
    }
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "organization_name": domain,
        "domain": domain
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        result = response.json()

        if "person" in result and result["person"]:
            person = result["person"]
            email = person.get("email")
            if email:
                return email, 90  # Apollo doesn't return confidence scores

        return None, 0
    except Exception as e:
        print(f"  Apollo error: {e}")
        return None, 0


def enrich_leads(input_file, output_file):
    """Main enrichment pipeline."""

    # Check API keys
    hunter_key = os.environ.get("HUNTER_API_KEY")
    apollo_key = os.environ.get("APOLLO_API_KEY")

    if not hunter_key and not apollo_key:
        print("=" * 60)
        print("EMAIL ENRICHMENT SETUP")
        print("=" * 60)
        print()
        print("You need at least one API key:")
        print()
        print("Option 1: Hunter.io (Recommended)")
        print("  1. Sign up at https://hunter.io (free: 25 searches/month)")
        print("  2. Go to https://hunter.io/api_keys")
        print("  3. Copy your API key")
        print("  4. Run: export HUNTER_API_KEY='your_key_here'")
        print()
        print("Option 2: Apollo.io")
        print("  1. Sign up at https://apollo.io (free: 50 credits/month)")
        print("  2. Go to Settings > API Keys")
        print("  3. Copy your API key")
        print("  4. Run: export APOLLO_API_KEY='your_key_here'")
        print()
        print("Then run this script again.")
        return

    # Read input leads
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        print("Run scrape_google_maps.py first to generate leads.")
        return

    with open(input_file, "r") as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"Loaded {len(leads)} leads from {input_file}")

    enriched = []
    found_count = 0
    verified_count = 0

    for i, lead in enumerate(leads):
        # Skip if already has email
        if lead.get("email"):
            lead["email_source"] = "scraped"
            lead["email_verified"] = "unknown"
            lead["email_confidence"] = "100"
            enriched.append(lead)
            found_count += 1
            continue

        # Extract domain from website
        domain = extract_domain(lead.get("website", ""))
        if not domain:
            lead["email_source"] = "none"
            lead["email_verified"] = "none"
            lead["email_confidence"] = "0"
            enriched.append(lead)
            continue

        print(f"[{i+1}/{len(leads)}] Enriching: {lead.get('business_name', 'Unknown')} ({domain})")

        email = None
        confidence = 0
        source = "none"

        # Try Hunter.io first
        if hunter_key:
            email, confidence = find_email_hunter(domain, hunter_key)
            if email:
                source = "hunter"
                print(f"  Found: {email} (confidence: {confidence}%)")

                # Verify
                if confidence < 90:
                    status = verify_email_hunter(email, hunter_key)
                    lead["email_verified"] = status
                    if status == "valid":
                        verified_count += 1
                else:
                    lead["email_verified"] = "high_confidence"
                    verified_count += 1

        # Try Apollo if Hunter didn't find anything
        if not email and apollo_key:
            # Try to extract first/last name from business name
            name_parts = lead.get("business_name", "").split()
            if len(name_parts) >= 2:
                email, confidence = find_email_apollo(
                    name_parts[0], name_parts[-1], domain, apollo_key
                )
                if email:
                    source = "apollo"
                    lead["email_verified"] = "apollo_match"
                    print(f"  Found via Apollo: {email}")

        lead["email"] = email or ""
        lead["email_source"] = source
        lead["email_confidence"] = str(confidence)
        if not email:
            lead["email_verified"] = "none"

        if email:
            found_count += 1

        enriched.append(lead)

        # Rate limiting
        time.sleep(1)

    # Save enriched leads
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Determine headers (original + new enrichment columns)
    all_headers = list(enriched[0].keys()) if enriched else []

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_headers)
        writer.writeheader()
        writer.writerows(enriched)

    print(f"\n{'=' * 60}")
    print(f"ENRICHMENT COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total leads: {len(leads)}")
    print(f"Emails found: {found_count} ({found_count*100//max(len(leads),1)}%)")
    print(f"Emails verified: {verified_count}")
    print(f"Output saved to: {output_file}")
    print(f"\nNext step: Run score_leads.py to prioritize your outreach list.")


def main():
    parser = argparse.ArgumentParser(description="Enrich leads with verified emails")
    parser.add_argument(
        "--input",
        default=os.path.join(OUTPUT_DIR, "google_maps_leads.csv"),
        help="Input CSV file with leads"
    )
    parser.add_argument(
        "--output",
        default=os.path.join(OUTPUT_DIR, "enriched_leads.csv"),
        help="Output CSV file with enriched leads"
    )

    args = parser.parse_args()
    enrich_leads(args.input, args.output)


if __name__ == "__main__":
    main()
