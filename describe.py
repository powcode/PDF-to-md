import base64
import hashlib
import json
import re
import time
import requests
import config

INDO_WORDS = {"yang", "dan", "dengan", "untuk", "dari", "ini"}
ENG_WORDS = {"the", "and", "with", "for", "from", "this"}

def detect_language(slide_text: str) -> str:
    words = re.findall(r"\b[a-zA-Z]+\b", slide_text.lower())
    indo_count = sum(1 for w in words if w in INDO_WORDS)
    eng_count = sum(1 for w in words if w in ENG_WORDS)
    if eng_count > indo_count:
        return "English"
    return "Indonesian"

def count_sentences(text: str) -> int:
    # Split on . ! or ? followed by whitespace and an uppercase letter, or end of text.
    # Do not split inside numbers such as 1.500 or 3.14.
    cleaned = text.strip()
    if not cleaned:
        return 0
    # Negative lookbehind for digit followed by period and digit
    # Sentence boundary: [.!?]+ followed by (\s+[A-Z] or end of string)
    pattern = r"(?<!\b\d)[.!?]+(?=\s+[A-Z]|\s*$)"
    parts = [p.strip() for p in re.split(pattern, cleaned) if p.strip()]
    return len(parts)

def build_instruction(language: str, caption: str, context: str) -> str:
    instruction = (
        "You describe one figure from a PowerPoint slide for readers who cannot see it.\n"
        "IMPORTANT: If this figure is purely an institutional/company logo, decorative icon, bullet glyph, page border, watermark, or background ornament with no informational or educational value, respond ONLY with the exact word: DEKORASI_SLIDE\n"
        f"Otherwise, write exactly 2 or 3 sentences in {language}.\n"
        "- Sentence 1: the figure type (photo, chart, diagram, flowchart, table image, or illustration) and its topic.\n"
        "- Sentences 2 and 3: the most important visible content, such as values, trends, labels, categories, or steps.\n"
        "- If a value or label cannot be read, say so. Never guess.\n"
        "- Use only what is visible. The caption and nearby text help you read the figure. Do not copy them.\n"
        "- Output only the description. No title, no bullets, no quotes, no Markdown.\n\n"
        f"Caption: {caption or 'none'}\n"
        f"Nearby text: {context or 'none'}"
    )
    return instruction

def get_cache_key(png_bytes: bytes, model: str, instruction: str) -> str:
    h = hashlib.sha256()
    h.update(png_bytes)
    h.update(model.encode("utf-8"))
    h.update(instruction.encode("utf-8"))
    return h.hexdigest()

def read_cache(cache_key: str) -> dict | None:
    cache_file = config.CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def write_cache(cache_key: str, data: dict):
    if data.get("status") in ("ok", "needs_review"):
        cache_file = config.CACHE_DIR / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def call_gemini_api(png_bytes: bytes, prompt_text: str, model: str, api_key: str) -> tuple[str, int]:
    # Returns (text_response, status_code)
    models_to_try = [model]
    for fb in ("gemini-3-flash-preview", "gemini-flash-lite-latest"):
        if fb != model and fb not in models_to_try:
            models_to_try.append(fb)

    last_code = 200
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": b64_img
                        }
                    },
                    {
                        "text": prompt_text
                    }
                ]
            }
        ]
    }

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=config.REQUEST_TIMEOUT_S)
            last_code = resp.status_code
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return "", 200
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                return text, 200
            elif resp.status_code == 429:
                # Model quota exhausted, attempt fallback to keep processing alive
                continue
            else:
                return "", resp.status_code
        except Exception:
            continue

    return "", last_code

def describe_figure(
    png_bytes: bytes,
    caption: str,
    context: str,
    slide_text: str
) -> tuple[str, str]:
    # Returns (description, status)
    if not config.AI_MODEL:
        raise ValueError("Model AI belum diatur di config.py.")
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY belum diatur di environment variable.")

    lang = detect_language(slide_text)
    instruction = build_instruction(lang, caption, context)
    cache_key = get_cache_key(png_bytes, config.AI_MODEL, instruction)

    # 1. Check Cache
    cached = read_cache(cache_key)
    if cached:
        return cached.get("description", ""), "cached"

    # 2. Make API call with retry for timeout, 429, or 5xx
    def fetch_with_retry(prompt: str) -> tuple[str, str]:
        for attempt in range(2):
            try:
                text, status_code = call_gemini_api(png_bytes, prompt, config.AI_MODEL, config.GEMINI_API_KEY)
                if status_code == 200:
                    return text, "ok"
                elif status_code in (429, 500, 502, 503, 504) and attempt == 0:
                    time.sleep(5)
                    continue
                else:
                    return "", "failed"
            except (requests.Timeout, requests.RequestException):
                if attempt == 0:
                    time.sleep(5)
                    continue
                return "", "failed"
        return "", "failed"

    raw_text, fetch_status = fetch_with_retry(instruction)
    if fetch_status == "failed" or not raw_text:
        return "Deskripsi gambar gagal dibuat, perlu ditinjau.", "failed"

    if "DEKORASI_SLIDE" in raw_text.strip():
        return "DEKORASI_SLIDE", "skipped"

    # 3. Validate sentence count
    sentence_count = count_sentences(raw_text)
    final_status = "ok"

    if sentence_count in (2, 3):
        final_status = "ok"
    else:
        # Retry once
        retry_prompt = f"{instruction}\n\nYour previous answer had {sentence_count} sentences. Rewrite it as exactly 2 or 3 sentences with the same facts."
        retry_text, retry_status = fetch_with_retry(retry_prompt)
        if retry_status == "ok" and retry_text:
            retry_count = count_sentences(retry_text)
            if retry_count in (2, 3):
                raw_text = retry_text
                final_status = "ok"
            else:
                raw_text = retry_text
                final_status = "needs_review"
        else:
            final_status = "needs_review"

    # Save to cache if ok or needs_review
    write_cache(cache_key, {
        "description": raw_text,
        "status": final_status,
        "model": config.AI_MODEL
    })

    return raw_text, final_status
