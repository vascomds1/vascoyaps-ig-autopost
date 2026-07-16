#!/usr/bin/env python3
"""
Generate the daily @vascoyaps AI-news carousel copy with Claude (web search enabled).
Writes content.json consumed by build_carousel.py.

Keeps a rolling log (posted_news.md) of stories already covered so the same
story is not re-featured day after day unless there is a NEW development.

Env:
  ANTHROPIC_API_KEY  (required)
  CLAUDE_MODEL       (optional, default below)
"""
import os, sys, json, datetime, re
import anthropic

MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date.today().strftime("%a %b %-d, %Y").upper()
LOG = os.path.join(HERE, "posted_news.md")
RECENT_DAYS = 14  # how far back to treat a story as "already covered"

def recent_slugs():
    """Return story slugs covered in the last RECENT_DAYS days."""
    if not os.path.exists(LOG):
        return []
    cutoff = datetime.date.today() - datetime.timedelta(days=RECENT_DAYS)
    out = []
    for line in open(LOG, encoding="utf-8"):
        line = line.strip()
        if not line.startswith("- "):
            continue
        try:
            date_str, slug = line[2:].split(" | ", 1)
            if datetime.date.fromisoformat(date_str.strip()) >= cutoff:
                out.append(slug.strip())
        except ValueError:
            continue
    # de-dup, keep order
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s); uniq.append(s)
    return uniq

SCHEMA_EXAMPLE = {
    "cover": {
        "kicker": "AI NEWS  \u00b7  " + TODAY,
        "title_lines": ["6 AI moves", "that change", "how you work."],
        "subtitle": "One-sentence promise of what the 6 stories mean for the reader. Concrete and specific."
    },
    "cards": [
        {"label": "APPLE", "index": 1, "slug": "apple-wwdc-siri",
         "headline": "Punchy claim, 4-7 words",
         "bullets": ["First supporting fact.", "Second fact with a number.", "What this means for you, in one line."]}
    ],
    "cta": {
        "kicker": "THAT'S TODAY IN AI", "line1": "Save this", "line2": "for later.",
        "subtitle": "AI news, decoded daily.",
        "question": "Which story changes your work the most? Tell me below (1 to 6).",
        "pill": "Follow @vascoyaps"
    },
    "caption": "Instagram caption text with hashtags."
}

SYSTEM = (
    "You are the content strategist for @vascoyaps, an AI-news brand. You write tight, "
    "punchy, credible social copy. Voice: smart friend who cuts the hype and tells you "
    "what actually matters. No buzzwords, no fluff.\n"
    "HARD RULE: never use em dashes or en dashes anywhere. Use commas, periods, "
    "parentheses, or 'and'/'but' instead.\n"
    "Numbers and named entities must be accurate to what you found in search. Do not invent stats."
)

def build_prompt(avoid):
    avoid_block = "\n".join(f"- {s}" for s in avoid) if avoid else "(nothing yet)"
    return f"""Today is {TODAY}. Use web search to find the most important AI news from today (and the last 24 hours).
Pick the 6 strongest, most distinct stories (model launches, big company moves, funding/IPOs, regulation, research, product news). Rank by significance.

ANTI-REPEAT RULE (important): you have already covered these stories in the last two weeks:
{avoid_block}

Do NOT feature any already-covered story again UNLESS there is a genuinely NEW, material development today (a new number, an actual launch or release, a ruling, a reversal, a price, a date confirmed). If you do revisit one, the headline and bullets MUST lead with the new development and not restate the old news. Otherwise, prefer fresh stories the brand has not posted. Aim for a carousel that feels new versus the last two weeks.

Then output a single Instagram carousel as STRICT JSON, no prose, matching exactly this shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}

Rules:
- cover.title_lines: 3 to 4 short lines that make ONE specific promise or consequence for the viewer. Lead with the outcome ("what you get") or the tension ("what changes for you / what you are missing"). Patterns that work: "6 AI moves that change how you work", "You will pay more for AI after today", "The AI rules just changed for your business". NEVER a generic status line like "AI just had a big day". The LAST element is the phrase that gets highlighted (punchy, <= 4 words). Keep each line short enough to fit a big headline.
- cover.kicker: keep exactly "AI NEWS  \u00b7  {TODAY}".
- Exactly 6 cards. index 1..6. label = 1-2 word uppercase category (e.g. APPLE, FUNDING, REGULATION).
- slug: a short stable lowercase-kebab id for the story (e.g. "anthropic-ipo", "gemini-3-5-pro", "eu-ai-act"). Reuse the SAME slug if you are revisiting a story with a new development, so the log stays consistent.
- headline: 4 to 6 words, concrete and specific, no period needed. Keep it short so it never wraps past 2 lines.
- bullets: exactly 3 per card. Each ONE short sentence, max 110 characters (hard limit, aim for ~90). No semicolons. Include at least one real number/stat per card where possible. The LAST bullet must speak to the reader directly ("you"/"your"): a concrete consequence or action, never a restatement of the news.
- cta: keep line1/line2/pill as shown. cta.question: ONE short question that invites a choice or an answer in the comments (like the example). Vary it day to day.
- caption: a proof or contrast line first (a real number or stakes from today's stories), a 1-2 sentence summary, a "save this" instruction naming what they will come back for, the same question from the cta, a follow CTA for @vascoyaps, then 8-10 relevant hashtags. Emojis ok but sparing.
- Absolutely no em or en dashes anywhere.

Return ONLY the JSON object."""

def extract_json(text):
    t = text.strip()
    if "```" in t:
        import re as _re
        m = _re.search(r"```(?:json)?\s*(.*?)```", t, _re.S)
        if m:
            t = m.group(1).strip()
    a, b = t.find("{"), t.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("No JSON found in model output")
    chunk = t[a:b+1]
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        import re as _re
        return json.loads(_re.sub(r",(\s*[}\]])", r"\1", chunk))

def main():
    avoid = recent_slugs()
    client = anthropic.Anthropic()
    data = None
    for _attempt in range(3):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
            messages=[{"role": "user", "content": build_prompt(avoid)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            data = extract_json(text); break
        except (ValueError, json.JSONDecodeError) as _e:
            print(f"[generate] JSON parse failed (attempt {_attempt+1}/3): {_e}")
            if _attempt == 2:
                raise

    # ---- validate / sanitize ----
    assert "cover" in data and "cards" in data and "cta" in data and "caption" in data, "missing top-level keys"
    data["cards"] = data["cards"][:6]
    for i, c in enumerate(data["cards"], 1):
        c["index"] = i
        c["bullets"] = c.get("bullets", [])[:3]
    def clean(s): return s.replace("\u2014", ", ").replace("\u2013", "-") if isinstance(s, str) else s
    def walk(o):
        if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list): return [walk(v) for v in o]
        return clean(o)
    data = walk(data)

    out = os.path.join(HERE, "content.json")
    json.dump(data, open(out, "w"), indent=2, ensure_ascii=False)

    # ---- log today's story slugs so future runs avoid repeats ----
    today_iso = datetime.date.today().isoformat()
    def slugify(c):
        s = c.get("slug") or c.get("headline", "")
        s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
        return s or "story"
    header_needed = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("# Posted news stories (slug log; avoid repeats within 2 weeks)\n\n")
        for c in data["cards"]:
            f.write(f"- {today_iso} | {slugify(c)}\n")

    print("Wrote", out)
    print("Avoided slugs:", ", ".join(avoid) or "(none)")
    print("Caption preview:\n", data["caption"][:300])

if __name__ == "__main__":
    main()
