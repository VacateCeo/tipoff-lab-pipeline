# NBA Watchability Score

Ranks tonight's NBA games by predicted competitiveness — spread tightness, playoff stakes, team form, rest, and injury impact.

**Live site:** https://nba-watchability-frontend.vercel.app

## How it works
- Pulls daily games from ESPN
- Fetches odds from The Odds API
- Fetches injury report from ESPN
- Scores each game 0-10 using a rule-based formula
- Stores predictions in Supabase
- Displays on a Next.js frontend hosted on Vercel

## Stack
- Python (data pipeline)
- Supabase (database)
- Next.js + Tailwind (frontend)
- GitHub Actions (daily cron at 4AM PT)

## Repos
- Pipeline: VacateCeo/nba-watchability-score
- Frontend: VacateCeo/nba-watchability-frontend
