#!/usr/bin/env python3
"""
Generate a @vascoyaps 7-repo roundup carousel (the "Joshua" format).

Claude (web search enabled) picks a ranked list of candidate GitHub repos for a
theme and writes the job-to-be-done copy. This script then VALIDATES every repo
against the GitHub API and pulls the real numbers (stars, forks, languages,
avatar), so nothing on the card is hallucinated. The first 7 candidates that
resolve become the carousel; slide 2 is the most official/credible entry point.

Writes content.json (for build_carousel.py) with repo cards, downloads avatars
to avatars/, and logs featured repos in posted_repos.md so they are not
re-featured within 60 days.

Env:
  ANTHROPIC_API_KEY  (required)
  CLAUDE_MODEL       (optional)
  REPO_THEME         (optional, default "Claude Code")
  GITHUB_TOKEN       (optional, raises the GitHub API rate limit in CI)
"""
import os, re, json, datetime
import requests

MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"
THEME = os.environ.get("REPO_THEME") or "Claude Code"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "posted_repos.md")
AVATARS = os.path.join(HERE, "avatars")
RECENT_DAYS = 60
N_REPOS = 7

GH_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "vascoyaps-carousel"}
if os.environ.get("GITHUB_TOKEN"):
    GH_HEADERS["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]


def recent_repos():
    if not os.path.exists(LOG):
        return []
    cutoff = datetime.date.today() - datetime.timedelta(days=RECENT_DAYS)
    out = []
    for line in open(LOG, encoding="utf-8"):
        line = line.strip()
        if not line.startswith("- "):
            continue
        try:
            date_str, name = line[2:].split(" | ", 1)
            if datetime.date.fromisoformat(date_str.strip()) >= cutoff:
                out.append(name.strip())
        except ValueError:
            continue
    return list(dict.fromkeys(out))


def fetch_repo(full_name):
    """Real GitHub data for one repo, or None if it does not resolve."""
    r = requests.get(f"https://api.github.com/repos/{full_name}", headers=GH_HEADERS, timeout=20)
    if r.status_code != 200:
        return None
    j = r.json()
    langs = {}
    lr = requests.get(j["languages_url"], headers=GH_HEADERS, timeout=20)
    if lr.status_code == 200:
        langs = lr.json()
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:4]
    os.makedirs(AVATARS, exist_ok=True)
    avatar_rel = os.path.join("avatars", j["owner"]["login"].lower() + ".png")
    avatar_abs = os.path.join(HERE, avatar_rel)
    if not os.path.exists(avatar_abs):
        try:
            sep = "&" if "?" in j["owner"]["avatar_url"] else "?"
            ar = requests.get(j["owner"]["avatar_url"] + sep + "s=200", headers=GH_HEADERS, timeout=20)
            if ar.status_code == 200:
                open(avatar_abs, "wb").write(ar.content)
        except requests.RequestException:
            pass
    # The slide font has no emoji glyphs, so strip anything past basic typography.
    desc = "".join(ch for ch in (j.get("description") or "") if ord(ch) < 0x2500).strip(" -:|")
    if len(desc) > 150:
        desc = desc[:150].rsplit(" ", 1)[0].rstrip(",.;") + " ..."
    return {
        "full_name": j["full_name"], "desc": desc,
        "stars": j.get("stargazers_count", 0), "forks": j.get("forks_count", 0),
        "langs": [[name, round(v/total, 3)] for name, v in top],
        "avatar": avatar_rel,
    }


SCHEMA_EXAMPLE = {
    "cover": {
        "kicker": "REPO ROUNDUP",
        "title_lines": ["7 Claude Code repos", "that work like", "a software team."],
        "subtitle": "One line on the concrete outcome the viewer gets from installing these."
    },
    "candidates": [
        {"full_name": "anthropics/claude-code", "label": "OFFICIAL",
         "headline": "The job this repo does, 4-7 words",
         "use": "One sentence: the job it does for you, concrete, max 110 chars."}
    ],
    "cta": {
        "kicker": "BEFORE YOUR NEXT BUILD", "line1": "Save this", "line2": "install one.",
        "subtitle": "Practical AI, out loud.",
        "question": "Which one are you installing first? Tell me below (1 to 7).",
        "pill": "Follow @vascoyaps"
    },
    "caption": "Instagram caption text (the repo list is appended automatically)."
}

SYSTEM = (
    "You are the content strategist for @vascoyaps, an AI-education brand for non-technical "
    "founders and builders. Tagline: 'Learning AI. Out Loud.' Voice: first-person, practical, "
    "no jargon, no hype, anti-guru.\n"
    "HARD RULE: never use em dashes or en dashes anywhere. Use commas, periods, parentheses, "
    "or 'and'/'but' instead.\n"
    "Repo names must be real, exactly as they appear on GitHub (owner/name). Prefer repos you "
    "actually found in search results. Never invent a repo."
)


def build_prompt(avoid):
    avoid_block = "\n".join(f"- {s}" for s in avoid) if avoid else "(nothing yet)"
    return f"""Use web search to find GitHub repos that are currently popular, rising, or genuinely useful for this theme: "{THEME}".
The audience is founders and builders using AI tools (many non-technical). Think "repos that do a job for you", not obscure libraries.

Already featured recently, do NOT include any of these:
{avoid_block}

Return a ranked list of 12 candidate repos (best first). Rank the OFFICIAL or most credible entry-point repo for the theme FIRST, then order by how much momentum and practical value each has. Some candidates may fail validation, so 12 gives slack; only the first 7 that resolve get used.

Output STRICT JSON only, matching exactly this shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}

Rules:
- cover.title_lines: 3 short lines, pattern "7 [specific repos] that [specific outcome]" or a warning ("Your Claude Code setup is missing these"). The LAST element is the highlighted phrase (<= 4 words). Say 7, not another number.
- cover.kicker: 1-3 uppercase words for the theme (e.g. "REPO ROUNDUP", "CLAUDE CODE").
- candidates: exactly 12, ranked. full_name must be the exact owner/name on GitHub.
- label: a 1-2 word uppercase category for the slide (OFFICIAL, AGENTS, WORKFLOWS, GUARDRAILS, DISCOVERY...). Vary them.
- headline: the JOB the repo does for the viewer, 4 to 7 words, no repo name, no period (e.g. "Delegate work to specialist agents").
- use: ONE sentence, max 110 characters, the concrete job-to-be-done in "you" terms. Not a feature list.
- cta: keep line1/line2/subtitle/pill as shown. question: one short question inviting a choice, like the example.
- caption: a proof or contrast line about the list, one save instruction ("save this before your next build"), the same question as the cta, a follow CTA for @vascoyaps, then 6 to 10 hashtags. Do NOT list the repos, that is appended automatically.
- No em or en dashes anywhere.

Return ONLY the JSON object."""


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("No JSON found in model output")
    chunk = t[a:b + 1]
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        return json.loads(re.sub(r",(\s*[}\]])", r"\1", chunk))


def generate(avoid, tries=3):
    import anthropic
    client = anthropic.Anthropic()
    last = None
    for _ in range(tries):
        resp = client.messages.create(
            model=MODEL, max_tokens=5000, system=SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
            messages=[{"role": "user", "content": build_prompt(avoid)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            return extract_json(text)
        except (ValueError, json.JSONDecodeError) as e:
            last = e
    raise SystemExit(f"Model returned unparseable JSON {tries}x: {last}")


def assemble(data, avoid):
    """Validate candidates against GitHub in ranked order; keep the first 7 real ones."""
    cards, seen = [], set(s.lower() for s in avoid)
    for cand in data.get("candidates", []):
        if len(cards) == N_REPOS:
            break
        full = cand.get("full_name", "").strip().strip("/")
        if not re.fullmatch(r"[\w.\-]+/[\w.\-]+", full) or full.lower() in seen:
            continue
        repo = fetch_repo(full)
        if repo is None:
            print(f"[repos] skipped (not on GitHub): {full}")
            continue
        seen.add(repo["full_name"].lower())
        cards.append({
            "label": (cand.get("label") or "REPO").upper()[:18],
            "index": len(cards) + 1,
            "headline": cand.get("headline", repo["full_name"]),
            "use": cand.get("use", ""),
            "repo": repo,
        })
    if len(cards) < N_REPOS:
        raise SystemExit(f"Only {len(cards)}/{N_REPOS} candidates resolved on GitHub; not posting a thin list.")
    return cards


def main():
    avoid = recent_repos()
    data = generate(avoid)
    cards = assemble(data, avoid)

    def clean(s):
        return s.replace("—", ", ").replace("–", "-") if isinstance(s, str) else s
    def walk(o):
        if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list): return [walk(v) for v in o]
        return clean(o)

    content = walk({
        "cover": data["cover"],
        "cards": cards,
        "cta": data["cta"],
        "caption": data.get("caption", ""),
    })
    content["caption"] = content["caption"].rstrip() + "\n\nThe repos:\n" + "\n".join(
        f"{c['index']}. {c['repo']['full_name']}" for c in content["cards"])

    json.dump(content, open(os.path.join(HERE, "content.json"), "w"), indent=2, ensure_ascii=False)

    today = datetime.date.today().isoformat()
    header_needed = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("# Featured repos (do not repeat within 60 days)\n\n")
        for c in content["cards"]:
            f.write(f"- {today} | {c['repo']['full_name']}\n")

    print(f"Theme: {THEME}")
    for c in content["cards"]:
        print(f"  {c['index']}. {c['repo']['full_name']}  ({fmt(c['repo']['stars'])} stars)")
    print("Caption preview:\n", content["caption"][:300])


def fmt(n):
    return f"{n/1000:.1f}K".replace(".0", "") if n >= 1000 else str(n)


if __name__ == "__main__":
    main()
