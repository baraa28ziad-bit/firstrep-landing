#!/usr/bin/env python3
"""
Outreach Campaign Preparation
Takes scored leads and generates campaign-ready CSV files for email tools.

Usage:
    python prepare_outreach.py --input leads/scored_leads.csv --output outreach/

Output:
    outreach/campaign_competitor_users.csv  (Template A: Switch and Save)
    outreach/campaign_hot_leads.csv         (Template B: Level Up)
    outreach/campaign_warm_leads.csv        (Template C: Scale Without Burnout)
    outreach/campaign_cold_leads.csv        (Template D: Launch Right)
    outreach/campaign_summary.txt           (Campaign statistics)

Each CSV is ready to import into Instantly.ai, Lemlist, or Mailshake.
"""

import os
import csv
import argparse
import re
import random
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "leads")
OUTREACH_DIR = os.path.join(os.path.dirname(__file__), "outreach")

# Personalization templates for the {{personalized_line}} variable
PERSONALIZED_LINES = {
    "competitor_user": [
        "I noticed you're already using coaching software — always great to see trainers investing in their business.",
        "As someone who already uses digital coaching tools, you probably know the pain of programming taking too long.",
        "You clearly take your coaching business seriously — that's exactly who I built this for.",
    ],
    "hot_lead": [
        "Your reviews speak for themselves — your clients clearly love working with you.",
        "It's clear from your online presence that you run a professional operation.",
        "With the reputation you've built, you deserve tools that match your quality of service.",
    ],
    "warm_lead": [
        "I came across your business while researching trainers in {city} and was impressed.",
        "Your focus on {business_type} is exactly the kind of specialty that clients look for.",
        "Trainers like you — passionate about results — are exactly who we built FirstRep for.",
    ],
    "cold_lead": [
        "I found your listing while looking at trainers in the {city} area.",
        "As a trainer in {city}, you probably know how competitive the local market is.",
        "Building a training business from scratch takes guts — respect.",
    ]
}


def extract_first_name(business_name):
    """Try to extract a first name from the business name."""
    if not business_name:
        return "there"

    # Common patterns: "John Smith Personal Training", "John's Fitness", "Coach John"
    name = business_name.strip()

    # Remove common suffixes
    for suffix in ["personal training", "fitness", "coaching", "training", "pt", "llc", "inc",
                   "studio", "gym", "performance", "athletics", "wellness", "health"]:
        name = re.sub(rf'\b{suffix}\b', '', name, flags=re.IGNORECASE)

    # Remove possessives
    name = name.replace("'s", "").replace("'s", "")

    # Clean up
    name = name.strip(" -–—.,")

    # If what's left looks like a name (1-2 words, capitalized), use the first word
    parts = name.split()
    if parts and len(parts[0]) > 1 and parts[0][0].isupper() and parts[0].isalpha():
        return parts[0]

    return "there"


def extract_business_type(lead):
    """Try to determine the business type/specialty."""
    category = lead.get("category", "").lower()
    business_name = lead.get("business_name", "").lower()

    specialties = {
        "strength": "strength training",
        "weight loss": "weight loss coaching",
        "crossfit": "CrossFit coaching",
        "yoga": "yoga instruction",
        "pilates": "Pilates instruction",
        "boxing": "boxing/martial arts training",
        "nutrition": "nutrition coaching",
        "athletic": "athletic performance training",
        "sports": "sports performance coaching",
        "rehabilitation": "rehabilitation training",
        "senior": "senior fitness",
        "group": "group fitness",
    }

    for keyword, specialty in specialties.items():
        if keyword in category or keyword in business_name:
            return specialty

    return "personal training"


def generate_personalized_line(lead, segment):
    """Generate a personalized first line for the email."""
    templates = PERSONALIZED_LINES.get(segment, PERSONALIZED_LINES["cold_lead"])
    template = random.choice(templates)

    city = lead.get("city", "your area")
    business_type = extract_business_type(lead)

    return template.format(city=city, business_type=business_type)


def prepare_campaign(leads, segment, output_dir):
    """Prepare a campaign CSV file for a specific segment."""
    segment_leads = [l for l in leads if l.get("segment") == segment and l.get("email")]

    if not segment_leads:
        return 0

    # Prepare output rows
    output_rows = []
    for lead in segment_leads:
        first_name = extract_first_name(lead.get("business_name", ""))
        personalized_line = generate_personalized_line(lead, segment)

        row = {
            "email": lead["email"],
            "first_name": first_name,
            "business_name": lead.get("business_name", ""),
            "city": lead.get("city", ""),
            "state": lead.get("state", ""),
            "website": lead.get("website", ""),
            "phone": lead.get("phone", ""),
            "rating": lead.get("rating", ""),
            "review_count": lead.get("review_count", ""),
            "lead_score": lead.get("lead_score", ""),
            "personalized_line": personalized_line,
            "segment": segment,
        }
        output_rows.append(row)

    # Save
    filename = f"campaign_{segment}.csv"
    filepath = os.path.join(output_dir, filename)

    headers = list(output_rows[0].keys())

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"  {segment}: {len(output_rows)} leads → {filename}")
    return len(output_rows)


def main():
    parser = argparse.ArgumentParser(description="Prepare outreach campaign files")
    parser.add_argument(
        "--input",
        default=os.path.join(OUTPUT_DIR, "scored_leads.csv"),
        help="Input CSV with scored leads"
    )
    parser.add_argument(
        "--output",
        default=OUTREACH_DIR,
        help="Output directory for campaign files"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        print("Run score_leads.py first.")
        return

    # Read scored leads
    with open(args.input, "r") as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"Loaded {len(leads)} scored leads")

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Generate campaign files for each segment
    print(f"\nGenerating campaign files:")

    segments = ["competitor_user", "hot_lead", "warm_lead", "cold_lead"]
    total = 0
    segment_counts = {}

    for segment in segments:
        count = prepare_campaign(leads, segment, args.output)
        segment_counts[segment] = count
        total += count

    # Generate summary
    summary_file = os.path.join(args.output, "campaign_summary.txt")

    with open(summary_file, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("FIRSTREP GTM: OUTREACH CAMPAIGN SUMMARY\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Total leads with email: {total}\n")
        f.write(f"Leads without email (excluded): {len(leads) - total}\n\n")

        f.write("CAMPAIGNS:\n\n")

        campaign_details = {
            "competitor_user": {
                "name": "Switch and Save",
                "template": "Template A",
                "subject": "Quick question about your training setup",
                "description": "Trainers already using Trainerize/TrueCoach/etc."
            },
            "hot_lead": {
                "name": "Level Up",
                "template": "Template B",
                "subject": "Saw your training page — quick idea",
                "description": "High-score leads with website, reviews, established business"
            },
            "warm_lead": {
                "name": "Scale Without Burnout",
                "template": "Template C",
                "subject": "Scaling past 15 clients without drowning",
                "description": "Mid-score leads, working trainers with some online presence"
            },
            "cold_lead": {
                "name": "Launch Right",
                "template": "Template D",
                "subject": "Congrats on the cert!",
                "description": "Lower-score leads, newer or less established trainers"
            }
        }

        for segment in segments:
            details = campaign_details[segment]
            count = segment_counts.get(segment, 0)

            f.write(f"Campaign: {details['name']} ({details['template']})\n")
            f.write(f"  File: campaign_{segment}.csv\n")
            f.write(f"  Leads: {count}\n")
            f.write(f"  Subject: {details['subject']}\n")
            f.write(f"  Target: {details['description']}\n\n")

        f.write("\nNEXT STEPS:\n\n")
        f.write("1. Import each CSV into your email tool (Instantly.ai / Lemlist)\n")
        f.write("2. Set up the 4-email sequence for each campaign (see GTM_PLAN.md)\n")
        f.write("3. Configure sending schedule: Tue-Thu, 7-9 AM local time\n")
        f.write("4. Set max 50 emails/day per mailbox\n")
        f.write("5. Monitor open rates (>50%), reply rates (>8%)\n")
        f.write("6. Manually reply to all positive responses within 2 hours\n")
        f.write("\nPRIORITY ORDER:\n")
        f.write("  1. competitor_user (highest conversion potential)\n")
        f.write("  2. hot_lead (established, ready to buy)\n")
        f.write("  3. warm_lead (needs nurturing)\n")
        f.write("  4. cold_lead (lowest priority, highest volume)\n")

    print(f"\n{'=' * 60}")
    print("CAMPAIGN PREPARATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total outreach-ready leads: {total}")
    print(f"Campaign files saved to: {args.output}/")
    print(f"Summary saved to: {summary_file}")
    print()
    print("Next steps:")
    print("  1. Import CSVs into Instantly.ai or Lemlist")
    print("  2. Set up email sequences from GTM_PLAN.md Section 14")
    print("  3. Start sending! (Priority: competitor_user → hot_lead → warm_lead → cold_lead)")


if __name__ == "__main__":
    main()
