#!/usr/bin/env python3
"""
Generate a @vascoyaps tutorial/tip carousel from the curated idea bank.

Source of truth is ideas.json (a parsed batch of short-form content ideas,
each with a hook + a step-by-step script + an optional publisher link/prompt).
This script picks the next UNUSED idea and asks Claude to reformat that one
idea into the carousel content.json schema (cover / step cards / cta /
caption). It does NOT invent tips and does NOT web-search: the idea is
already written and curated, so the model's only job is faithful
restructuring into the slide format.

Selection is RANDOM among unused ideas, so near-duplicate tools do not
land back to back. A failed run logs nothing, so a re-run simply draws
another unused idea.

Writes content.json (for build_carousel.py) and logs the idea id in
posted_tutorials.md so it never repeats.

Env:
  ANTHROPIC_API_KEY   (required)
  CLAUDE_MODEL        (optional)
  CAROUSEL_KICKER     (optional, cover kicker text; default "TRY THIS")
  IDEAS_FILE          (optional, path to the idea bank; default ideas.json)
"""
import os, re, json, random, datetime
import anthropic

MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"
KICKER = os.environ.get("CAROUSEL_KICKER") or "TRY THIS"
HERE = os.path.dirname(os.path.abspath(__file__))
IDEAS_FILE = os.environ.get("IDEAS_FILE") or os.path.join(HERE, "ideas.json")
LOG = os.path.join(HERE, "posted_tutorials.md")


def used_ids():
    """Idea ids already turned into carousels, parsed from posted_tutorials.md."""
    if not os.path.exists(LOG):
        return set()
    ids = set()
    for line in open(LOG, encoding="utf-8"):
        m = re.match(r"\s*-\s*#(\d+)\b", line)
        if m:
            ids.add(int(m.group(1)))
    return ids


def pick_idea():
    bank = json.load(open(IDEAS_FILE, encoding="utf-8"))
    ideas = bank["ideas"] if isinstance(bank, dict) else bank
    done = used_ids()
    remaining = [i for i in ideas if i["id"] not in done]
    if not remaining:
        raise SystemExit(
            f"All {len(ideas)} ideas in {os.path.basename(IDEAS_FILE)} have been "
            "posted. Add the next batch (Part 4) or reset posted_tutorials.md."
        )
    return random.choice(remaining), len(remaining), len(ideas)


SCHEMA_EXAMPLE = {
    "topic": "Short internal title (the tool or tip name)",
    "cover": {
        "kicker": KICKER,
        "title_lines": ["Turn any photo", "into a moving", "video for free"],
        "subtitle": "One short line naming the concrete payoff the viewer gets."
    },
    "cards": [
        {"label": "STEP 1", "index": 1, "headline": "Short action, 3-6 words",
         "bullets": ["What to do, one short sentence.", "A concrete detail or tip."]}
    ],
    "cta": {"kicker": "SAVE THIS FOR LATER", "line1": "Follow", "handle": "@vascoyaps",
            "pill": "Save this  \u00b7  Build it today"},
    "caption": "Instagram caption with a save-prompt and hashtags."
}

SYSTEM = (
    "You are the content strategist for @vascoyaps, an AI-education brand for non-technical "
    "founders. Tagline: 'Learning AI. Out Loud.' Voice: first-person, practical, no jargon, "
    "no hype, anti-guru, an excited friend showing you something useful.\n"
    "You are given ONE pre-written, curated content idea (a hook plus a step-by-step script). "
    "Your ONLY job is to reformat THAT idea faithfully into a carousel. Do NOT invent new "
    "tools, steps, features, URLs, or claims. Do NOT swap the tool for another. Stay true to "
    "the script: the steps you write must come from it. You may tighten wording and split the "
    "script into clean steps, but never add capabilities the script does not state.\n"
    "HARD RULE: never use em dashes or en dashes. Use commas, periods, parentheses, or 'and'/'but'."
)


def build_prompt(idea):
    pub = idea.get("publisher") or ""
    pub_line = f'\nPublisher reference (link or prompt to surface in the caption): {pub}' if pub else ""
    return f"""Reformat this ONE curated idea into a @vascoyaps carousel.

IDEA #{idea['id']}: {idea['title']}
Hook: {idea['hook']}
Script: {idea['script']}{pub_line}

Output STRICT JSON only, matching exactly this shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}

Rules:
- topic: a short title for the log (the tool or tip name). No id number.
- cover.kicker: keep exactly "{KICKER}".
- cover.title_lines: turn the hook into a punchy headline of 3 short lines. The LAST element is the highlighted phrase (<= 4 words). Keep each line short.
- cover.subtitle: one line naming the concrete payoff from the hook/script. No invention.
- cards: 3 to 6 steps taken DIRECTLY from the script, in order. No filler, no invented steps. index 1..N, labelled STEP 1, STEP 2, and so on. Make the final step the payoff ("now you have X").
- headline: the step's action in 3 to 6 words, no period.
- bullets: 1 to 2 per card. Each ONE short sentence, max 110 characters. Concrete and faithful to the script.
- cta: keep as shown.
- caption: a hook line, a one-line summary of what they get, a clear "save this and try it" line{', then the publisher link/prompt on its own line' if pub else ''}, then 6 to 10 relevant hashtags. Sparing emojis ok.
- No em or en dashes anywhere.

Return ONLY the JSON object."""


def extract_json(text):
    """Tolerant: strips code fences and trailing commas before parsing."""
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
        chunk = re.sub(r",(\s*[}\]])", r"\1", chunk)  # kill trailing commas
        return json.loads(chunk)


def generate(idea, tries=3):
    client = anthropic.Anthropic()
    last = None
    for _ in range(tries):
        resp = client.messages.create(
            model=MODEL, max_tokens=3500, system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(idea)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            return extract_json(text)
        except (ValueError, json.JSONDecodeError) as e:
            last = e
    raise SystemExit(f"Model returned unparseable JSON {tries}x: {last}")


def main():
    idea, remaining, total = pick_idea()
    data = generate(idea)

    data["cards"] = data["cards"][:6]
    for i, c in enumerate(data["cards"], 1):
        c["index"] = i
        c["label"] = f"STEP {i}"
        c["bullets"] = c.get("bullets", [])[:2]

    def clean(s):
        return s.replace("\u2014", ", ").replace("\u2013", "-") if isinstance(s, str) else s

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v) for v in o]
        return clean(o)

    data = walk(data)

    json.dump(data, open(os.path.join(HERE, "content.json"), "w"), indent=2, ensure_ascii=False)

    topic = data.get("topic", idea["title"])
    today = datetime.date.today().isoformat()
    header_needed = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("# Posted tutorials (idea ids, do not repeat)\n\n")
        f.write(f"- #{idea['id']} {topic} - {today}\n")

    print(f"Idea #{idea['id']}: {topic}  ({remaining - 1}/{total} ideas left after this)")
    print("Caption preview:\n", data.get("caption", "")[:300])


if __name__ == "__main__":
    main()
