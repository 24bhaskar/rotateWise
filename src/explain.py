"""B13 optional explainer: Gemini rewrites a strategy card in plain language, grounded only on its JSON.

Validation: every number in the output must appear in the input JSON; otherwise the output is discarded and
the template is used. The template is also used when no key is set or the API fails. Not part of the ML claim.
"""
import json
import os
import re

from src.rotations import SUPPORT_LINE

PROMPT = """Rewrite this crop-rotation strategy card for an Iowa farmer in 4-5 short plain-language sentences.
Rules: use ONLY facts and numbers present in the JSON; do not add any number that is not in the JSON;
no new facts, advice or sources; avoid jargon. End with exactly this sentence: "{line}"
JSON:
{card}"""
NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def _numbers(text):
    out = set()
    for n in NUM.findall(text):
        n = n.replace(",", "")
        try:
            out.add(round(abs(float(n)), 2))
        except ValueError:
            pass
    return out


def grounded(output, card):
    """True when every number in `output` appears in the card JSON (percent forms included)."""
    allowed = _numbers(json.dumps(card))
    allowed |= {round(v * 100, 2) for v in allowed if v <= 1} | {round(v * 100) for v in allowed if v <= 1}
    allowed |= {round(v) for v in allowed}
    return all(n in allowed for n in _numbers(output))


def template(card):
    first_benefit = card["benefits"][0] if card["benefits"] else ""
    first_risk = card["risks_needing_local_review"][0] if card["risks_needing_local_review"] else ""
    return (f"{card['name']} ranks {card['rank']} of 3 for the priorities you set. {card['why_suggested']} "
            f"Main benefit: {first_benefit} Main risk to review: {first_risk} {SUPPORT_LINE}")


def explain(card, client=None):
    """Returns (text, source) where source is 'gemini' or 'template'."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key and client is None:
        return template(card), "template"
    try:
        if client is None:
            from google import genai
            client = genai.Client(api_key=key)
        r = client.models.generate_content(model="gemini-2.5-flash",
                                           contents=PROMPT.format(line=SUPPORT_LINE, card=json.dumps(card)))
        text = (r.text or "").strip()
        if not text or not grounded(text, card):
            return template(card), "template"
        if SUPPORT_LINE not in text:
            text = f"{text} {SUPPORT_LINE}"
        return text, "gemini"
    except Exception:
        return template(card), "template"
