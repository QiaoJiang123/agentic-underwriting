import json
import urllib.error
import urllib.request


def call_openai_responses(api_key, model, messages, guide_instructions):
    payload = {
        "model": model,
        "instructions": build_model_instructions(guide_instructions),
        "input": messages,
        "max_output_tokens": 900,
    }
    response = post_json("https://api.openai.com/v1/responses", payload, api_key)
    return {
        "reply": extract_output_text(response),
        "id": response.get("id"),
    }


def build_model_instructions(guide_instructions):
    base_instructions = [
        "You are an underwriting copilot for cyber insurance workflows.",
        "Help evaluate submissions, ask for missing information, summarize risks, and explain your reasoning.",
        "Do not make binding coverage or pricing decisions. Flag uncertainty and recommend human review for high-impact decisions.",
        "Keep answers concise, practical, and structured for a cyber underwriter.",
    ]
    guides = [
        str(guide).strip()
        for guide in guide_instructions or []
        if str(guide or "").strip()
    ]

    if not guides:
        return " ".join(base_instructions)

    return "\n".join(
        [
            " ".join(base_instructions),
            "",
            "Additional underwriting guide instructions. Treat these as higher-priority operating guidance for this request:",
            *[f"{index + 1}. {guide}" for index, guide in enumerate(guides)],
        ]
    )


def post_json(url, payload, api_key):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}

        api_message = parsed.get("error", {}).get("message") if isinstance(parsed, dict) else None
        raise RuntimeError(api_message or raw or f"OpenAI request failed with {error.code}.") from error


def extract_output_text(response):
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    chunks = []
    for item in response.get("output", []) if isinstance(response.get("output"), list) else []:
        for part in item.get("content", []) if isinstance(item.get("content"), list) else []:
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)

    return "\n".join(chunks).strip() or "I could not produce a response."

