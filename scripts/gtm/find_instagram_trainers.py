#!/usr/bin/env python3
"""
Instagram Personal Trainer Finder
Finds personal trainers on Instagram via hashtag mining and competitor follower analysis.

Usage:
    python find_instagram_trainers.py

This script provides:
1. A list of hashtags to search
2. Instructions for using PhantomBuster or manual methods
3. A CSV template for organizing Instagram leads
4. DM tracking spreadsheet setup

Note: Instagram scraping at scale requires PhantomBuster ($69/month) or similar tools.
Manual method works for 20-30 DMs/day without any tools.
"""

import os
import csv
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "leads")
OUTREACH_DIR = os.path.join(os.path.dirname(__file__), "outreach")


# High-value hashtags for finding personal trainers
HASHTAGS = {
    "tier_1_direct": [
        "#personaltrainer",
        "#personaltraining",
        "#fitnesscoach",
        "#onlinecoach",
        "#certifiedpersonaltrainer",
        "#onlinepersonaltrainer",
        "#onlinefitnesscoach",
    ],
    "tier_2_business": [
        "#fitnessbusiness",
        "#personaltrainerlife",
        "#ptlife",
        "#fitpro",
        "#trainertips",
        "#fitnesscoaching",
        "#fitnessprofessional",
    ],
    "tier_3_competitor_users": [
        "#trainerize",
        "#truecoach",
        "#ptdistinction",
        "#everfit",
        "#trainheroic",
    ],
    "tier_4_specialty": [
        "#strengthcoach",
        "#transformationcoach",
        "#onlinetrainer",
        "#macrocoach",
        "#bodybuilding",
        "#weightlosscoach",
        "#functionaltraining",
    ]
}

# Competitor accounts whose followers are likely PTs
COMPETITOR_ACCOUNTS = [
    "traborize",          # Trainerize official
    "truecoach",          # TrueCoach official
    "ptdistinction",      # PT Distinction
    "everfit.io",         # Everfit
    "trainheroic",        # TrainHeroic
    "theptdc",            # Personal Trainer Development Center
    "nasmpersonaltrainer", # NASM
    "acefitness",         # ACE Fitness
]


def generate_instagram_guide():
    """Generate a comprehensive guide for finding PTs on Instagram."""

    guide = f"""# Instagram Personal Trainer Finder Guide
Generated: {datetime.now().strftime('%Y-%m-%d')}

## Strategy Overview

Instagram is where 42% of personal trainers promote their business.
Our goal: Find 500+ trainer profiles, engage warmly, then DM.

---

## Method 1: PhantomBuster (Automated, $69/month)

### Step 1: Scrape Hashtag Posts
1. Go to https://phantombuster.com/
2. Use the **"Instagram Hashtag Collector"** Phantom
3. Enter these hashtags (start with Tier 1):

**Tier 1 — Direct PT Hashtags (start here):**
"""

    for hashtag in HASHTAGS["tier_1_direct"]:
        guide += f"   - {hashtag}\n"

    guide += """
**Tier 3 — Competitor Users (GOLD — these trainers already use coaching software):**
"""
    for hashtag in HASHTAGS["tier_3_competitor_users"]:
        guide += f"   - {hashtag}\n"

    guide += """
4. Set max results: 1,000 per hashtag
5. Export results → CSV

### Step 2: Extract Profile Data
1. Use the **"Instagram Profile Scraper"** Phantom
2. Input: list of usernames from Step 1
3. Extract: bio, website, email (if public), follower count, post count
4. Filter for:
   - Follower count: 500 – 50,000 (real working trainers, not celebrities)
   - Bio contains: "trainer", "coach", "fitness", "PT", "certified", "NASM", "ACE"
   - Has website or email in bio
5. Export to CSV

### Step 3: Scrape Competitor Followers
1. Use the **"Instagram Followers Collector"** Phantom
2. Target accounts:
"""

    for account in COMPETITOR_ACCOUNTS:
        guide += f"   - @{account}\n"

    guide += """
3. Set max: 5,000 followers per account
4. Cross-reference with Step 1 results
5. Anyone following competitor accounts AND posting with PT hashtags = HOT LEAD

---

## Method 2: Manual Search (Free, 30 min/day)

### Daily Routine (20-30 DMs/day)

**Morning (15 min):**
1. Open Instagram
2. Search each Tier 1 hashtag
3. Filter by "Recent" posts (not "Top")
4. Open 10 profiles that look like working trainers
5. For each: Follow + Like 2-3 posts

**Afternoon (15 min):**
6. Go back to the 10 profiles you followed this morning
7. Leave a genuine comment on one of their posts:
   - "Great form cue! I always tell my clients the same thing about hip hinge."
   - "This is solid programming. How long are your training blocks usually?"
   - "Love the energy! Your clients are lucky to have you."
   - **NOT**: "Great post!" or "🔥🔥🔥" (these get ignored)

**Next Day:**
8. If they posted a Story, reply to it with something relevant
9. Send DM (see scripts below)

### Qualification Checklist (Before DMing)

✅ Bio mentions "trainer", "coach", "PT", or certifications
✅ Posts workout content (not just gym selfies)
✅ Has 500+ followers (established)
✅ Posts at least 1x/week (active)
✅ Not already using a competitor (check bio for Trainerize/TrueCoach links)
   - If they DO use a competitor → even better, use "switch" script

---

## DM Scripts

### Script 1: After Engaging With Their Content (WARM — Best Conversion)

Hey {name}! Been following your content for a bit — love the [specific post/topic].

Quick question: do you use any coaching software to manage your clients, or are you more of a spreadsheet/WhatsApp person?

I ask because I just launched a platform for trainers that includes a marketplace where clients find you + AI that builds programs in 30 seconds. Thought you might find it interesting.

No pressure at all — just wanted to share in case it's useful!

### Script 2: For Trainers Using Competitor Tools (SWITCHING)

Hey {name}! Noticed you're using [Trainerize/TrueCoach] — how are you finding it?

I built a similar platform called FirstRep but with something none of them have: a built-in marketplace where clients discover and book you.

Plus the AI generates programs in 30 seconds, which my trainer friends say saves them 10+ hours/week.

Free for up to 3 clients if you ever want to compare. No pressure!

### Script 3: Response to Their Story About Admin/Burnout

I feel this. I built an app specifically because I kept hearing trainers say the same thing — too much admin, not enough coaching time.

It's called FirstRep — marketplace to find clients + AI program builder + everything else in one app. Free for 3 clients.

Would you want to take a look? No sales pitch, just think you'd genuinely find it useful.

### Script 4: For Trainers Posting About Getting Clients

Finding clients is the #1 struggle I hear from trainers. That's actually why I built FirstRep — it has a built-in marketplace where clients search for and book trainers directly.

No ads, no hustling on social media. Clients come to you.

It's free for your first 3 clients. Would you be interested in checking it out?

---

## Tracking Spreadsheet

Create a Google Sheet with these columns:

| Column | Description |
|--------|-------------|
| Username | Instagram handle |
| Name | Their name |
| Followers | Count |
| Bio | Key info from bio |
| Website | URL if any |
| Email | If publicly listed |
| Certification | NASM/ACE/etc if mentioned |
| Competitor | Tool they use (if any) |
| Day 1 Action | Follow + Like (date) |
| Day 2 Action | Comment (date + what you said) |
| Day 3 Action | Story reply (date) |
| DM Sent | Date |
| DM Script Used | 1/2/3/4 |
| Reply Received | Date + summary |
| Outcome | Signed up / Not interested / Follow up |

---

## Volume Targets

| Week | Daily DMs | Weekly Total | Expected Replies | Expected Signups |
|------|-----------|-------------|-----------------|-----------------|
| 1-2 | 10 | 50 | 10-15 | 2-3 |
| 3-4 | 20 | 100 | 20-30 | 4-6 |
| 5-8 | 30 | 150 | 30-45 | 6-10 |
| 9-12 | 30 | 150 | 30-45 | 6-10 |

**Total expected signups from Instagram: 18-29 over 12 weeks**

---

## Instagram Account Setup (FirstRep Brand)

1. Create @firstrep.fit Instagram account
2. Bio: "The all-in-one platform for personal trainers | AI programs | Client marketplace | Free for 3 clients | Link below 👇"
3. Link in bio: firstrep.fit
4. Post schedule: 3x/week
   - Monday: Trainer tip (e.g., "5 ways to retain clients longer")
   - Wednesday: Product feature highlight (screenshot/video)
   - Friday: Industry stat or meme
5. Use Stories daily: behind-the-scenes, feature demos, trainer testimonials
6. Reels: 1x/week — 15-30 second feature demos or trainer tips

This builds credibility so when you DM trainers, your profile looks legit.
"""

    # Save guide
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    guide_file = os.path.join(OUTPUT_DIR, "instagram_trainer_guide.md")
    with open(guide_file, "w") as f:
        f.write(guide)
    print(f"Instagram guide saved to: {guide_file}")

    # Save DM tracking template
    tracking_file = os.path.join(OUTREACH_DIR, "instagram_dm_tracker.csv")
    os.makedirs(OUTREACH_DIR, exist_ok=True)

    headers = [
        "username", "name", "followers", "bio_summary", "website", "email",
        "certification", "competitor_used", "day1_follow_date", "day2_comment_date",
        "day2_comment_text", "day3_story_reply", "dm_sent_date", "dm_script_used",
        "reply_date", "reply_summary", "outcome", "notes"
    ]

    with open(tracking_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        # Add a sample row
        writer.writerow([
            "@example_trainer", "John Smith", "5200", "NASM-CPT | Online Coach | DM for programs",
            "johnsmithfitness.com", "", "NASM", "none", "2026-02-22", "2026-02-23",
            "Great programming post! How long are your blocks?", "2026-02-24",
            "2026-02-25", "Script 1", "", "", "pending", ""
        ])

    print(f"DM tracker template saved to: {tracking_file}")

    # Save hashtag search URLs
    search_file = os.path.join(OUTPUT_DIR, "instagram_search_urls.txt")
    with open(search_file, "w") as f:
        f.write("# Instagram Hashtag Search URLs\n")
        f.write("# Open each in a browser to find trainers posting with these hashtags\n\n")
        for tier, hashtags in HASHTAGS.items():
            f.write(f"\n## {tier.replace('_', ' ').title()}\n")
            for hashtag in hashtags:
                tag = hashtag.replace("#", "")
                f.write(f"https://www.instagram.com/explore/tags/{tag}/\n")

    print(f"Search URLs saved to: {search_file}")


def main():
    print("=" * 60)
    print("FirstRep GTM: Instagram Personal Trainer Finder")
    print("=" * 60)
    print()

    generate_instagram_guide()

    print()
    print("Files generated! Start with the Instagram guide in leads/instagram_trainer_guide.md")
    print()
    print("Quick start:")
    print("  1. Create @firstrep.fit Instagram account")
    print("  2. Follow 10 trainers from Tier 1 hashtags")
    print("  3. Engage genuinely for 2 days")
    print("  4. Send first DMs on day 3")
    print("  5. Track everything in outreach/instagram_dm_tracker.csv")


if __name__ == "__main__":
    main()
