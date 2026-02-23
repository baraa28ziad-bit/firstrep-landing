#!/usr/bin/env python3
"""
Lead Scoring Pipeline
Scores each lead 0-100 based on likelihood to convert.

Usage:
    python score_leads.py --input leads/enriched_leads.csv --output leads/scored_leads.csv

Scoring Criteria:
    - Has verified email: +20
    - Has website: +15
    - Has Instagram/social: +10
    - 4+ star Google rating: +10
    - 10+ Google reviews: +10
    - Uses competitor tool (Trainerize/TrueCoach): +25
    - Has phone number: +5
    - In top 20 metro: +5
"""

import os
import csv
import argparse
import re
import sys
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "leads")

TOP_METROS = [
    "los angeles", "new york", "chicago", "houston", "phoenix",
    "san diego", "dallas", "austin", "denver", "miami",
    "atlanta", "seattle", "san francisco", "portland", "nashville",
    "charlotte", "tampa", "minneapolis", "boston", "philadelphia"
]

COMPETITOR_SIGNALS = [
    "trainerize", "truecoach", "true coach", "myPTHub", "my pt hub",
    "pt distinction", "everfit", "trainheroic", "train heroic",
    "exercise.com", "fitbot", "wodify", "pushpress"
]


def score_lead(lead):
    """Score a single lead from 0-100."""
    score = 0
    reasons = []

    # Email quality
    email = lead.get("email", "")
    email_verified = lead.get("email_verified", "")
    email_confidence = int(lead.get("email_confidence", "0") or "0")

    if email and email_verified in ("valid", "high_confidence", "apollo_match"):
        score += 20
        reasons.append("verified_email")
    elif email and email_confidence >= 70:
        score += 15
        reasons.append("likely_email")
    elif email:
        score += 10
        reasons.append("unverified_email")

    # Website
    website = lead.get("website", "")
    if website and not any(s in website.lower() for s in ["facebook.com", "instagram.com", "yelp.com"]):
        score += 15
        reasons.append("has_website")

    # Social media presence (check if website contains social links or business name suggests it)
    business_name = lead.get("business_name", "").lower()
    if "fitness" in business_name or "training" in business_name or "coaching" in business_name:
        score += 5
        reasons.append("fitness_business")

    # Google rating
    try:
        rating = float(lead.get("rating", "0") or "0")
        if rating >= 4.5:
            score += 10
            reasons.append("high_rating")
        elif rating >= 4.0:
            score += 7
            reasons.append("good_rating")
    except (ValueError, TypeError):
        pass

    # Review count (social proof = established business)
    try:
        reviews = int(lead.get("review_count", "0") or "0")
        if reviews >= 50:
            score += 10
            reasons.append("many_reviews")
        elif reviews >= 10:
            score += 7
            reasons.append("some_reviews")
        elif reviews >= 3:
            score += 3
            reasons.append("few_reviews")
    except (ValueError, TypeError):
        pass

    # Competitor usage
    all_text = json.dumps(lead).lower() if 'json' in dir() else str(lead).lower()
    for competitor in COMPETITOR_SIGNALS:
        if competitor in all_text:
            score += 25
            reasons.append(f"uses_{competitor}")
            break

    # Phone number
    if lead.get("phone", ""):
        score += 5
        reasons.append("has_phone")

    # Top metro area
    city = lead.get("city", "").lower()
    if any(metro in city for metro in TOP_METROS):
        score += 5
        reasons.append("top_metro")

    # Cap at 100
    score = min(score, 100)

    return score, reasons


def segment_lead(score, lead):
    """Assign a segment based on score and lead characteristics."""
    email = lead.get("email", "")

    if not email:
        return "no_email"

    all_text = str(lead).lower()
    uses_competitor = any(c in all_text for c in COMPETITOR_SIGNALS)

    if uses_competitor:
        return "competitor_user"  # Template A: Switch and Save
    elif score >= 60:
        return "hot_lead"  # Template B: Level Up
    elif score >= 40:
        return "warm_lead"  # Template C: Scale Without Burnout
    else:
        return "cold_lead"  # Template D: Launch Right


def main():
    parser = argparse.ArgumentParser(description="Score and segment leads")
    parser.add_argument(
        "--input",
        default=os.path.join(OUTPUT_DIR, "enriched_leads.csv"),
        help="Input CSV with enriched leads"
    )
    parser.add_argument(
        "--output",
        default=os.path.join(OUTPUT_DIR, "scored_leads.csv"),
        help="Output CSV with scored leads"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        print("Run enrich_emails.py first.")
        return

    # Read leads
    with open(args.input, "r") as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"Scoring {len(leads)} leads...")

    # Score each lead
    scored = []
    for lead in leads:
        score, reasons = score_lead(lead)
        segment = segment_lead(score, lead)

        lead["lead_score"] = str(score)
        lead["score_reasons"] = "|".join(reasons)
        lead["segment"] = segment
        scored.append(lead)

    # Sort by score descending
    scored.sort(key=lambda x: int(x.get("lead_score", "0")), reverse=True)

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    headers = list(scored[0].keys()) if scored else []

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(scored)

    # Print summary
    print(f"\n{'=' * 60}")
    print("LEAD SCORING COMPLETE")
    print(f"{'=' * 60}")

    segments = {}
    score_buckets = {"90-100": 0, "70-89": 0, "50-69": 0, "30-49": 0, "0-29": 0}

    for lead in scored:
        seg = lead["segment"]
        segments[seg] = segments.get(seg, 0) + 1

        s = int(lead["lead_score"])
        if s >= 90: score_buckets["90-100"] += 1
        elif s >= 70: score_buckets["70-89"] += 1
        elif s >= 50: score_buckets["50-69"] += 1
        elif s >= 30: score_buckets["30-49"] += 1
        else: score_buckets["0-29"] += 1

    print(f"\nTotal leads: {len(scored)}")
    print(f"\nScore Distribution:")
    for bucket, count in score_buckets.items():
        bar = "█" * (count * 40 // max(len(scored), 1))
        print(f"  {bucket}: {count:>5} {bar}")

    print(f"\nSegments:")
    for seg, count in sorted(segments.items(), key=lambda x: -x[1]):
        print(f"  {seg}: {count}")

    # Count leads with email
    with_email = sum(1 for l in scored if l.get("email"))
    print(f"\nLeads with email: {with_email}/{len(scored)}")
    print(f"Output saved to: {args.output}")
    print(f"\nNext step: Run prepare_outreach.py to generate campaign files.")


if __name__ == "__main__":
    import json
    main()
