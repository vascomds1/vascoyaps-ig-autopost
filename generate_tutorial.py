#!/usr/bin/env python3
"""
Generate a @vascoyaps "Build with Claude" tutorial carousel.
Every tutorial showcases one of Claude's customization/power features
(skills, plugins, connectors/MCP, Projects, Artifacts) with a concrete
example you build. Grounded in current Claude docs via web search.

Writes content.json (for build_carousel.py) and logs the topic so it
never repeats.

Env:
  ANTHROPIC_API_KEY  (required)
  CLAUDE_MODEL       (optional)
"""
import os, json, datetime
import anthropic

MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "posted_tutorials.md")

def past_topics():
    if not os.path.exists(LOG):
        return []
    out = []
    for line in open(LOG, encoding="utf-8"):
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].split(" \u2014 ")[0].strip())
    return out

SCHEMA_EXAMPLE = {
    "topic": "Short internal title, e.g. 'Gmail connector daily digest'",
    "cover": {
        "kicker": "BUILD WITH CLAUDE",
        "title_lines": ["How to turn your", "inbox into a", "6am digest"],
        "subtitle": "Connect Gmail to Claude and have it summarize your morning email for you."
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
    "You are the content strategist for @vascoyaps, an AI-education brand that shows "
    "people the powerful, lesser-known things Claude can do and what they can build with it. "
    "Voice: an excited friend going 'wait, you can MAKE Claude do this?'. Clear, concrete, zero jargon.\n"
    "ACCURACY IS CRITICAL. Claude's features (skills, plugins, connectors, Projects, Artifacts) "
    "change often. Use web search to confirm how the feature currently works and what it is called "
    "from official sources (support.claude.com, docs.claude.com, anthropic.com) before writing the steps. "
    "Only describe features and integrations that genuinely exist today. Never invent a connector, "
    "menu name, or capability. If unsure of a detail, keep the step at the level you can verify.\n"
    "HARD RULE: never use em dashes or en dashes. Use commas, periods, parentheses, or 'and'/'but'."
)

def build_prompt(avoid):
    avoid_block = "\n".join(f"- {t}" for t in avoid) if avoid else "(none yet)"
    return f"""Create ONE "Build with Claude" tutorial that showcases a Claude customization or power feature and walks through building a concrete, useful example with it.

Feature areas to draw from (pick ONE per tutorial):
- Connectors / MCP: connecting Claude to apps like Gmail, Google Calendar, Drive, Slack, Notion, GitHub, Linear, and what to build with them (a daily email digest, auto meeting prep, a task triage, a notes-to-Notion flow).
- Custom skills: teaching Claude a repeatable task once (your brand voice, a report format, a checklist) so it does it consistently.
- Plugins / plugin marketplaces: installing a bundle of skills and tools for a role or workflow.
- Projects: a reusable workspace with files and instructions so Claude remembers your context.
- Artifacts: having Claude build a small working thing (a calculator, a tracker, a one-page tool, a mini web app).

Each tutorial must center on a SPECIFIC, tangible example the viewer ends up with (name it in the cover subtitle and pay it off in the last step), not a vague overview.

Use web search first to verify the current, real way this feature works (names, where it lives, what is and is not possible). Do not invent anything.

Pick a fresh topic. Do NOT repeat or closely overlap any already-posted tutorial:
{avoid_block}

Output STRICT JSON only, matching exactly this shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}

Rules:
- topic: a short unique title for the log.
- cover.kicker: keep exactly "BUILD WITH CLAUDE".
- cover.title_lines: MUST begin with "How to" and read as one headline of what they build (e.g. "How to build a habit tracker with Claude"). 3 short lines, the LAST element is the highlighted phrase (<= 4 words, keep each line short).
- cover.subtitle: name the concrete example they will have built by the end.
- Use 3 to 6 cards (steps), whatever the build genuinely needs. No filler steps. index 1..N, labelled STEP 1, STEP 2, and so on. Make the final step the payoff ("now you have X").
- headline: the step's action in 3 to 6 words, no period.
- bullets: 2 per card. Each ONE short sentence, max 110 characters. Concrete and accurate. No vague fluff.
- cta: keep as shown.
- caption: a hook, a one-line summary of what they can build, a clear "save this and build it" line, then 8-10 relevant hashtags. Sparing emojis ok.
- No em or en dashes anywhere.

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
    avoid = past_topics()
    client = anthropic.Anthropic()
    data = None
    for _attempt in range(3):
        resp = client.messages.create(
            model=MODEL, max_tokens=3500, system=SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": build_prompt(avoid)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            data = extract_json(text); break
        except (ValueError, json.JSONDecodeError) as _e:
            print(f"[generate] JSON parse failed (attempt {_attempt+1}/3): {_e}")
            if _attempt == 2:
                raise

    data["cards"] = data["cards"][:6]
    for i, c in enumerate(data["cards"], 1):
        c["index"] = i
        c["label"] = f"STEP {i}"
        c["bullets"] = c.get("bullets", [])[:2]

    def clean(s): return s.replace("\u2014", ", ").replace("\u2013", "-") if isinstance(s, str) else s
    def walk(o):
        if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list): return [walk(v) for v in o]
        return clean(o)
    data = walk(data)

    json.dump(data, open(os.path.join(HERE, "content.json"), "w"), indent=2, ensure_ascii=False)

    topic = data.get("topic", "Untitled tutorial")
    today = datetime.date.today().isoformat()
    header_needed = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("# Posted tutorials (do not repeat)\n\n")
        f.write(f"- {topic} \u2014 {today}\n")

    print("Tutorial:", topic)
    print("Caption preview:\n", data.get("caption", "")[:300])

if __name__ == "__main__":
    main()
