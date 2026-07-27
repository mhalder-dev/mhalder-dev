#!/usr/bin/env python3
"""Regenerate the ACTIVITY card (assets/activity.svg + activity-light.svg).

Pulls live numbers from the GitHub GraphQL API through the authenticated `gh`
CLI, so the card never drifts from reality. Rerun after a busy stretch:

    python tools/update-stats.py

Private-repo work is included via `restrictedContributionsCount`, which is only
visible to a token that owns the account — this is why the script shells out to
`gh` rather than using an anonymous request.
"""

import json
import subprocess
from datetime import date, timezone, datetime

THEMES = {
    "activity.svg": {
        "bg0": "#0c1013", "bg1": "#0a0c0d", "stroke": "#20262c",
        "head": "#f3f6f7", "mono": "#9aa4ac", "accent": "#63e6a3",
        "soft": "#8ff2c0", "track": "#20262c", "glow": "0.13",
        "tile_fill": "rgba(99,230,163,0.08)", "tile_stroke": "rgba(99,230,163,0.28)",
    },
    "activity-light.svg": {
        "bg0": "#ffffff", "bg1": "#f6faf8", "stroke": "#dbe4df",
        "head": "#0e1512", "mono": "#5b6a64", "accent": "#0e8a55",
        "soft": "#0e8a55", "track": "#e3ebe6", "glow": "0.08",
        "tile_fill": "rgba(14,138,85,0.06)", "tile_stroke": "rgba(14,138,85,0.28)",
    },
}

MONO = "ui-monospace,'Cascadia Code','JetBrains Mono',Consolas,'Liberation Mono',monospace"
W, H = 1200, 300


def gh_json(args):
    out = subprocess.run(args, capture_output=True, text=True, shell=False, check=True)
    return json.loads(out.stdout)


def collect():
    years_q = "query { viewer { contributionsCollection { contributionYears } } }"
    years = gh_json(["gh", "api", "graphql", "-f", f"query={years_q}"])
    years = years["data"]["viewer"]["contributionsCollection"]["contributionYears"]

    per_year, commits, contributions = [], 0, 0
    year_q = (
        "query($f:DateTime!,$t:DateTime!){viewer{contributionsCollection(from:$f,to:$t)"
        "{totalCommitContributions restrictedContributionsCount "
        "contributionCalendar{totalContributions}}}}"
    )
    for y in sorted(years):
        data = gh_json([
            "gh", "api", "graphql", "-f", f"query={year_q}",
            "-F", f"f={y}-01-01T00:00:00Z", "-F", f"t={y}-12-31T23:59:59Z",
        ])["data"]["viewer"]["contributionsCollection"]
        total = data["contributionCalendar"]["totalContributions"]
        commits += data["totalCommitContributions"] + data["restrictedContributionsCount"]
        contributions += total
        # Skip trace years (a stray commit in 2021 with 2022 empty) so the chart
        # shows the real working span rather than a 1px bar next to a gap.
        if total >= 5:
            per_year.append((y, total))

    repos = gh_json([
        "gh", "repo", "list", "mhalder-dev", "--limit", "100",
        "--json", "name,isPrivate,isFork,primaryLanguage",
    ])
    langs = sorted({r["primaryLanguage"]["name"] for r in repos if r["primaryLanguage"]})

    return {
        "commits": commits,
        "contributions": contributions,
        "repos": len(repos),
        "public_repos": sum(1 for r in repos if not r["isPrivate"]),
        "languages": len(langs),
        "per_year": per_year,
    }


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(s, t):
    years = s["per_year"]
    peak = max(v for _, v in years) if years else 1
    span = f"{years[0][0]} — {years[-1][0]}" if years else ""
    stamp = date.today().strftime("%b %Y").upper()

    p = [
        f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f"font-family=\"'Segoe UI','Helvetica Neue',Arial,sans-serif\">",
        f'<defs><linearGradient id="abg" x1="0" y1="0" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{t["bg0"]}"/><stop offset="1" stop-color="{t["bg1"]}"/></linearGradient>'
        f'<linearGradient id="atop" x1="0" y1="0" x2="{W}" y2="0" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{t["accent"]}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{t["accent"]}" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="aclip"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
        f'<radialGradient id="aglow" cx="0.5" cy="-0.15" r="0.9">'
        f'<stop offset="0" stop-color="{t["accent"]}" stop-opacity="{t["glow"]}"/>'
        f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient></defs>',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="url(#abg)" stroke="{t["stroke"]}"/>',
        f'<path d="M40 1H{W-40}" stroke="url(#atop)" stroke-width="1"/>',
        f'<g clip-path="url(#aclip)"><rect width="{W}" height="{H}" fill="url(#aglow)"/></g>',
        # headline
        f'<text x="40" y="60" font-size="30" font-weight="700" letter-spacing="-0.8" fill="{t["head"]}">'
        f'<tspan fill="{t["accent"]}">{s["commits"]}</tspan> commits across '
        f'<tspan fill="{t["accent"]}">{s["repos"]}</tspan> repositories.</text>',
        f'<text x="40" y="88" font-family="{MONO}" font-size="11" letter-spacing="1.7" fill="{t["mono"]}">'
        f'CONTRIBUTION LOG &#183; {esc(span)} &#183; INCLUDES PRIVATE WORK &#183; UPDATED {stamp}</text>',
        f'<path d="M40 110H{W-40}" stroke="{t["stroke"]}" stroke-width="1"/>',
        f'<text x="40" y="140" font-family="{MONO}" font-size="10" letter-spacing="2" fill="{t["mono"]}">CONTRIBUTIONS BY YEAR</text>',
    ]

    # horizontal year bars
    bx, bw, y = 118, 470, 166
    for yr, val in years:
        w = max(4, round(bw * val / peak))
        p.append(f'<text x="40" y="{y+4}" font-family="{MONO}" font-size="12" font-weight="600" fill="{t["mono"]}">{yr}</text>')
        p.append(f'<rect x="{bx}" y="{y-7}" width="{bw}" height="10" rx="5" fill="{t["track"]}"/>')
        p.append(f'<rect x="{bx}" y="{y-7}" width="{w}" height="10" rx="5" fill="{t["accent"]}" fill-opacity="0.85"/>')
        p.append(f'<text x="{bx+bw+14}" y="{y+4}" font-family="{MONO}" font-size="12" font-weight="600" fill="{t["head"]}">{val}</text>')
        y += 30

    # right-hand stat tiles
    tiles = [
        (s["contributions"], "TOTAL CONTRIBUTIONS"),
        (s["public_repos"], "PUBLIC REPOSITORIES"),
        (s["languages"], "LANGUAGES SHIPPED"),
        (len(years), "ACTIVE YEARS"),
    ]
    p.append(f'<text x="700" y="140" font-family="{MONO}" font-size="10" letter-spacing="2" fill="{t["mono"]}">AT A GLANCE</text>')
    tx, ty, tw, th = 700, 156, 220, 54
    for i, (num, label) in enumerate(tiles):
        col, row = i % 2, i // 2
        x = tx + col * (tw + 20)
        yy = ty + row * (th + 16)
        p.append(f'<rect x="{x}.5" y="{yy}.5" width="{tw}" height="{th}" rx="10" fill="{t["tile_fill"]}" stroke="{t["tile_stroke"]}"/>')
        p.append(f'<text x="{x+16}" y="{yy+30}" font-size="22" font-weight="700" fill="{t["head"]}">{num}</text>')
        p.append(f'<text x="{x+16}" y="{yy+45}" font-family="{MONO}" font-size="9" letter-spacing="1.4" fill="{t["mono"]}">{label}</text>')

    p.append("</svg>")
    return "".join(p)


def main():
    stats = collect()
    for name, theme in THEMES.items():
        path = f"assets/{name}"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render(stats, theme))
        print(f"wrote {path}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
