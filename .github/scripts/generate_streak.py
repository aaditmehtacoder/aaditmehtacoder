from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

API_URL = "https://api.github.com/graphql"
USERNAME = os.environ.get("GITHUB_USERNAME", "aaditmehtacoder")
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT = Path("profile-summary-card-output/github_dark/streak.svg")


def graphql(query: str, variables: dict[str, str]) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-streak-generator",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]


def iso_datetime(day: date) -> str:
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


profile_query = """
query($login: String!) {
  user(login: $login) {
    createdAt
  }
}
"""

calendar_query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

created_at = graphql(profile_query, {"login": USERNAME})["user"]["createdAt"]
created_day = date.fromisoformat(created_at[:10])
today = datetime.now(timezone.utc).date()
counts: dict[date, int] = {}

cursor = created_day
while cursor <= today:
    end = min(cursor + timedelta(days=364), today)
    data = graphql(
        calendar_query,
        {
            "login": USERNAME,
            "from": iso_datetime(cursor),
            "to": iso_datetime(end + timedelta(days=1)),
        },
    )
    weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    for week in weeks:
        for contribution_day in week["contributionDays"]:
            day = date.fromisoformat(contribution_day["date"])
            if created_day <= day <= today:
                counts[day] = contribution_day["contributionCount"]
    cursor = end + timedelta(days=1)

# Fill any missing calendar days to keep streak calculations deterministic.
day = created_day
while day <= today:
    counts.setdefault(day, 0)
    day += timedelta(days=1)

longest_streak = 0
running_streak = 0
for day in sorted(counts):
    if counts[day] > 0:
        running_streak += 1
        longest_streak = max(longest_streak, running_streak)
    else:
        running_streak = 0

current_streak = 0
streak_day = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
if counts.get(streak_day, 0) > 0:
    while counts.get(streak_day, 0) > 0:
        current_streak += 1
        streak_day -= timedelta(days=1)

total_contributions = sum(counts.values())

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="700" height="180" viewBox="0 0 700 180" role="img" aria-label="GitHub contribution streak">
  <rect x="1" y="1" width="698" height="178" rx="8" fill="#0d1117" stroke="#30363d"/>
  <text x="350" y="34" text-anchor="middle" fill="#58a6ff" font-family="Segoe UI, Ubuntu, sans-serif" font-size="20" font-weight="600">GitHub Contribution Streak</text>
  <line x1="233" y1="55" x2="233" y2="151" stroke="#30363d"/>
  <line x1="466" y1="55" x2="466" y2="151" stroke="#30363d"/>

  <text x="116" y="94" text-anchor="middle" fill="#3fb950" font-family="Segoe UI, Ubuntu, sans-serif" font-size="34" font-weight="700">{current_streak}</text>
  <text x="116" y="121" text-anchor="middle" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="15">Current Streak</text>
  <text x="116" y="143" text-anchor="middle" fill="#8b949e" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12">consecutive days</text>

  <text x="350" y="94" text-anchor="middle" fill="#58a6ff" font-family="Segoe UI, Ubuntu, sans-serif" font-size="34" font-weight="700">{longest_streak}</text>
  <text x="350" y="121" text-anchor="middle" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="15">Longest Streak</text>
  <text x="350" y="143" text-anchor="middle" fill="#8b949e" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12">consecutive days</text>

  <text x="583" y="94" text-anchor="middle" fill="#d2a8ff" font-family="Segoe UI, Ubuntu, sans-serif" font-size="34" font-weight="700">{total_contributions:,}</text>
  <text x="583" y="121" text-anchor="middle" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, sans-serif" font-size="15">Contributions</text>
  <text x="583" y="143" text-anchor="middle" fill="#8b949e" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12">since joining GitHub</text>
</svg>
'''

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")
print(f"Wrote {OUTPUT}")
