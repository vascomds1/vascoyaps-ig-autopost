#!/usr/bin/env python3
"""
Generate the daily @vascoyaps AI-news carousel copy with Claude (web search enabled).
Writes content.json consumed by build_carousel.py.

Env:
  ANTHROPIC_API_KEY  (required)
  CLAUDE_MODEL       (optional, default below; set to a current model string)
"""
import os, sys, json, datetime, re
import anthropic

MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date.today().strftime("%a %b %-d, %Y").upper()

SCHEMA_EXAMPLE = {
    "cover": {
        "kicker": "AI NEWS  ·  " + TODAY,
        "title_lines": ["AI just had", "its biggest", "day", "of the year."],
        "subtitle": "One-sentence promise of what the 6 stories cover. Concrete and specific."
    },
    "cards": [
        {"label": "APPLE", "index": 1, "headline": "Punchy claim, 4-7 words",
         "bullets": ["First supporting fact.", "Second fact with a number.", "Why it matters in one line."]}
    ],
    "cta": {
        "kicker": "THAT'S TODAY IN AI", "line1": "Follow", "handle": "@vascoyaps",
        "subtitle": "AI news, decoded daily. No hype, just what matters.",
        "pill": "Save this  ·  Send it to a friend"
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

PROMPT = f"""Today is {TODAY}. Use web search to find the most important AI news from today (and the last 24 hours).
Pick the 6 strongest, most distinct stories (model launches, big company moves, funding/IPOs, regulation, research, product news). Rank by significance.

Then output a single Instagram carousel as STRICT JSON, no prose, matching exactly this shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}

Rules:
- cover.title_lines: 3 to 4 short lines that read as one bold statement; the LAST element is the phrase that gets highlighted (keep it punchy, <= 4 words). Keep each line short enough to fit a big headline.
- cover.kicker: keep exactly "AI NEWS  ·  {TODAY}".
- Exactly 6 cards. index 1..6. label = 1-2 word uppercase category (e.g. APPLE, FUNDING, REGULATION).
- headline: 4 to 6 words, concrete and specific, no period needed. Keep it short so it never wraps past 2 lines.
- bullets: exactly 3 per card. Each ONE short sentence, max 110 characters (hard limit, aim for ~90). No semicolons, no multi-clause run-ons. Include at least one real number/stat per card where possible. Last bullet says why it matters.
- caption: a strong hook line, a 1-2 sentence summary, a follow CTA for @vascoyaps, then 8-10 relevant hashtags. Emojis ok but sparing.
- Absolutely no em or en dashes anywhere.

Return ONLY the JSON object."""

def extract_json(text):
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("No JSON found in model output")
    return json.loads(text[a:b+1])

def main():
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": PROMPT}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    data = extract_json(text)

    # ---- validate / sanitize ----
    assert "cover" in data and "cards" in data and "cta" in data and "caption" in data, "missing top-level keys"
    data["cards"] = data["cards"][:6]
    for i, c in enumerate(data["cards"], 1):
        c["index"] = i
        c["bullets"] = c.get("bullets", [])[:3]
    # strip any stray dashes per brand rule
    def clean(s): return s.replace("—", ", ").replace("–", "-") if isinstance(s, str) else s
    def walk(o):
        if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list): return [walk(v) for v in o]
        return clean(o)
    data = walk(data)

    out = os.path.join(HERE, "content.json")
    json.dump(data, open(out, "w"), indent=2, ensure_ascii=False)
    print("Wrote", out)
    print("Caption preview:\n", data["caption"][:300])

if __name__ == "__main__":
    main()
