"""Send evidence to Gemini and read its structured explanation.

Flash-Lite is a small model suited to short classroom explanations. The model
never changes the solver's result; the shared validator checks its answer.
"""

import json
from urllib.parse import quote
from urllib.request import Request, urlopen

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
DEFAULT_MODEL = "gemini-3.5-flash-lite"


def output_token_limit(context):
    """Native-language scripts need more tokens than the same English wording."""
    languages = len(context.get("requested_languages", ["en"]))
    crops = max(1, len(context.get("candidates", [])))
    return max(3500 * languages, min(22000, 1800 * crops * languages))


def call_gemini(context, api_key, model, instructions, schema):
    """Make one bounded request. The private key goes in a header, not the URL."""
    payload = {
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": [
            {
                "role": "user",
                "parts": [{"text": json.dumps(context, ensure_ascii=False, allow_nan=False)}],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "maxOutputTokens": output_token_limit(context),
        },
    }
    body = json.dumps(payload).encode("utf-8")
    if len(body) > 100_000:
        raise ValueError("The explanation context is too large.")
    url = API_URL + quote(model, safe="") + ":generateContent"
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read(500_001)
    if len(raw) > 500_000:
        raise ValueError("The explanation response is too large.")
    result = json.loads(raw)
    candidates = result.get("candidates", [])
    if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
        raise ValueError("Gemini did not complete an explanation.")
    # Read the final answer only. Never display internal thought parts.
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part["text"] for part in parts if "text" in part and not part.get("thought"))
    return json.loads(text)
