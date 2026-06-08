#!/usr/bin/env python3
"""
Generate a daily @vascoyaps Claude-first micro-tutorial carousel with Claude.
Writes content.json (consumed by build_carousel.py) and appends the chosen
topic to posted_tutorials.md so topics never repeat.

Env:
  ANTHROPIC_API_KEY  (required)
  CLAUDE_MODEL       (optional, defaults to a current model)
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
            out.append(line[2:].split(" — ")[0].strip())
    return out

SCHEMA_EXAMPLE = {
    "topic": "Short internal title of the tutorial, e.g. 'Summarize a long PDF with Claude'",
    "cover": {
        "kicker": "CLAUDE TUTORIAL",
        "title_lines": ["Summarize any", "PDF in", "30 seconds"],
        "subtitle": "One-line promise of what they'll be able to do after these 3 steps."
    },
    "cards": [
        {"label": "STEP 1", "index": 1, "headline": "Short action, 3-6 words",
         "bullets": ["What to do, one short sentence.", "A concrete detail or tip."]}
    ],
    "cta": {"kicker": "SAVE THIS FOR LATER", "line1": "Follow", "handle": "@vascoyaps",
            "pill": "Save this  ·  Try it today"},
    "caption": "Instagram caption with a save-prompt and hashtags."
}

SYSTEM = (
    "You are the content strategist for @vascoyaps, an AI-education brand. You make "
    "dead-simple, genuinely useful Claude tutorials for normal people, not engineers. "
    "Voice: a clever friend showing you a trick. Clear, encouraging, zero jargon.\n"
    "HARD RULE: never use em dashes or en dashes anywhere. Use commas, periods, "
    "parentheses, or 'and'/'but'.\n"
    "Only describe real, current Claude capabilities (claude.ai web/app: chat, file and "
    "image upload, Projects, Artifacts, web search, writing/analysis). Do not invent features."
)

def build_prompt(avoid):
    avoid_block = "\n".join(f"- {t}" for t in avoid) if avoid else "(none yet)"
    return f"""Create ONE beginner-friendly Claude micro-tutorial: a single simple, useful task someone can do in exactly 3 steps.

Pick a fresh topic. Do NOT repeat or closely overlap any of these already-posted tutorials:
{avoid_block}

Good kinds of topics: summarizing a PDF or article, cleaning up messy notes, writing better prompts, drafting emails in your own voice, turning meeting notes into action items, setting up a Project for a recurring task, using Artifacts to build something, extracting data from a screenshot, planning with Claude. Choose simple, high-curiosity, immediately useful tasks.

Output STRICT JSON only, matching exactly this shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}

Rules:
- topic: a short unique title for the log.
- cover.kicker: keep exactly "CLAUDE TUTORIAL".
- cover.title_lines: 3 short lines that read as one punchy promise; the LAST element is the highlighted phrase (<= 4 words, keep each line short).
- Exactly 3 cards (STEP 1, STEP 2, STEP 3), index 1..3.
- headline: the step's action in 3 to 6 words, no period.
- bullets: 2 per card. Each ONE short sentence, max 110 characters. Concrete and do-this-now. Make them genuinely actionable, not vague.
- cta: keep as shown.
- caption: a hook, a one-line summary, a clear "save this and try it" line, then 8-10 relevant hashtags. Sparing emojis ok.
- No em or en dashes anywhere.

Return ONLY the JSON object."""

def extract_json(text):
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("No JSON found in model output")
    return json.loads(text[a:b+1])

def main():
    avoid = past_topics()
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL, max_tokens=2500, system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(avoid)}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    data = extract_json(text)

    data["cards"] = data["cards"][:3]
    for i, c in enumerate(data["cards"], 1):
        c["index"] = i
        c["label"] = f"STEP {i}"
        c["bullets"] = c.get("bullets", [])[:2]

    def clean(s): return s.replace("—", ", ").replace("–", "-") if isinstance(s, str) else s
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
        f.write(f"- {topic} — {today}\n")

    print("Tutorial:", topic)
    print("Caption preview:\n", data.get("caption", "")[:300])

if __name__ == "__main__":
    main()
