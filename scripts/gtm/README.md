# FirstRep GTM Automation Scripts

Lead generation and outreach automation for acquiring the first 100 paying personal trainers.

## Quick Start

```bash
cd scripts/gtm

# 1. Install dependencies
pip install requests beautifulsoup4

# 2. Generate leads from Google Maps
python scrape_google_maps.py

# 3. Scrape certification directories
python scrape_cert_directories.py

# 4. Enrich leads with verified emails
export HUNTER_API_KEY="your_key"
python enrich_emails.py --input leads/google_maps_leads.csv --output leads/enriched_leads.csv

# 5. Score and segment leads
python score_leads.py --input leads/enriched_leads.csv --output leads/scored_leads.csv

# 6. Generate campaign-ready files
python prepare_outreach.py --input leads/scored_leads.csv --output outreach/

# 7. Generate Instagram outreach guide + tracker
python find_instagram_trainers.py
```

## Pipeline Overview

```
Google Maps ──┐
Cert Dirs  ───┤──→ Enrich Emails ──→ Score Leads ──→ Prepare Campaigns ──→ Import to Instantly.ai
LinkedIn   ───┤                                                              or Lemlist
Instagram  ───┘
```

## Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `scrape_google_maps.py` | Scrape PT businesses from Google Maps | `leads/google_maps_leads.csv` |
| `scrape_cert_directories.py` | Scrape NASM/ACE/NSCA directories | `leads/cert_directory_leads.csv` |
| `enrich_emails.py` | Find & verify emails via Hunter.io/Apollo | `leads/enriched_leads.csv` |
| `score_leads.py` | Score leads 0-100, segment into campaigns | `leads/scored_leads.csv` |
| `prepare_outreach.py` | Generate campaign CSVs for email tools | `outreach/campaign_*.csv` |
| `find_instagram_trainers.py` | Instagram search guide + DM tracker | `leads/instagram_trainer_guide.md` |

## API Keys Needed

| Service | Free Tier | Paid | Sign Up |
|---------|-----------|------|---------|
| Hunter.io | 25 searches/month | $49/month (500 searches) | https://hunter.io |
| Apollo.io | 50 credits/month | $49/month | https://apollo.io |
| Outscraper | 25 free results | Pay-per-use | https://outscraper.com |
| Instantly.ai | — | $37/month | https://instantly.ai |

## Full GTM Plan

See `GTM_PLAN.md` in the landing_page root for the complete go-to-market strategy including:
- Email templates (4 sequences for 4 segments)
- Instagram DM scripts
- Community seeding strategy
- Paid ads setup
- Referral program
- 12-week execution calendar
- Budget breakdown
