#!/usr/bin/env python3
"""
LLM call helper for the game-gen pipeline.
Calls OpenRouter chat completions API. Reads OPENROUTER_API_KEY from ~/.hermes/.env.

Usage:
  llm.py chat <model> <system_prompt> <user_prompt> [--max-tokens N]
  llm.py vision <model> <image_path> <prompt> [--max-tokens N]

Models used by the pipeline:
  z-ai/glm-5.3        — text/code brain (design + review)
  z-ai/glm-5.3-flash  — multimodal "eyes" (screenshot critique)

Output: the assistant's text content, printed to stdout.
"""
import sys
import os
import json
import base64
import urllib.request


def load_key():
    env = os.path.expanduser("~/.hermes/.env")
    try:
        with open(env) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    raise SystemExit("OPENROUTER_API_KEY not found in ~/.hermes/.env")


def call(model, messages, max_tokens=2048, include_reasoning=False):
    key = load_key()
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if not include_reasoning:
        body["include_reasoning"] = False
        body["reasoning"] = {"effort": "low"}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    if "error" in data:
        raise SystemExit(f"API error: {data['error']}")
    choice = data["choices"][0]
    msg = choice["message"]
    content = msg.get("content")
    if not content:
        reason = msg.get("reasoning") or ""
        if not reason and msg.get("reasoning_details"):
            reason = "".join(d.get("text", "") for d in msg["reasoning_details"])
        print(f"[llm.py: empty content] finish_reason={choice.get('finish_reason')} "
              f"reasoning_chars={len(reason)}", file=sys.stderr)
        content = reason
    return content


def image_to_data_url(path):
    mime = "image/png"
    lp = path.lower()
    if lp.endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    elif lp.endswith(".webp"):
        mime = "image/webp"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def main():
    args = sys.argv[1:]
    max_tokens = 2048
    while "--max-tokens" in args:
        i = args.index("--max-tokens")
        max_tokens = int(args[i + 1])
        del args[i:i + 2]

    include_reasoning = False
    if "--reasoning" in args:
        args.remove("--reasoning")
        include_reasoning = True

    if not args:
        raise SystemExit(__doc__)

    mode = args[0]
    if mode == "chat":
        model, system, user = args[1], args[2], args[3]
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    elif mode == "vision":
        model, image, prompt = args[1], args[2], args[3]
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_to_data_url(image)}},
            ],
        }]
    else:
        raise SystemExit(__doc__)

    out = call(model, messages, max_tokens, include_reasoning)
    if "--strip-fences" in sys.argv:
        import re
        m = re.search(r"```[a-zA-Z]*\s*\n(.*?)```", out, re.S)
        out = m.group(1) if m else out
    print(out)


if __name__ == "__main__":
    main()
