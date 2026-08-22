"""
Optional: turn the computed readiness numbers into a short, plain-language
note, the same job Google Health Coach does, using your own Claude API key.

Requires: pip install anthropic
Requires: export ANTHROPIC_API_KEY="sk-ant-..."
Get a key at https://console.anthropic.com
"""

import os

SYSTEM_PROMPT = (
    "You are a terse, no-nonsense training coach. Given a day's recovery "
    "metrics and how they compare to the person's personal baseline, write "
    "a 2-3 sentence note: what today's numbers suggest about training "
    "intensity, and one concrete thing to watch (sleep, hydration, easy day, "
    "etc). No hedging, no disclaimers, no generic wellness platitudes. "
    "If data is missing, say so briefly and work with what's there."
)


def generate_note(readiness_result, model="claude-haiku-4-5-20251001"):
    try:
        from anthropic import Anthropic
    except ImportError:
        return "(install the 'anthropic' package to enable coaching notes)"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "(set ANTHROPIC_API_KEY to enable coaching notes)"

    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Today's readiness data:\n{readiness_result}",
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text")
