import os
import re
import base64
import requests
import json
import logging

import time
from datetime import datetime

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

DEFAULT_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-1.5-pro"
]

_cached_discovered_models = None
_last_discovery_time = 0.0
_pinned_working_model = None
_model_cooldown_map = {}

def get_model_rank_score(model_name: str) -> int:
    lower = model_name.lower()
    is_exp_or_thinking = any(k in lower for k in ["thinking", "exp", "preview"])
    is_flash = "flash" in lower
    is_lite = "lite" in lower
    is_pro = "pro" in lower

    if is_flash and not is_lite and not is_exp_or_thinking:
        return 1
    if is_flash and is_lite and not is_exp_or_thinking:
        return 2
    if is_pro and not is_exp_or_thinking:
        return 3
    if is_flash and is_exp_or_thinking:
        return 4
    if is_exp_or_thinking:
        return 5
    return 6

def rank_models(models: list) -> list:
    return sorted(models, key=lambda m: (get_model_rank_score(m), [-ord(c) for c in m]))

def discover_available_models(api_key: str = None) -> list:
    global _cached_discovered_models, _last_discovery_time
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        return DEFAULT_FALLBACK_MODELS

    now = time.time()
    if _cached_discovered_models and (now - _last_discovery_time < 1800):
        return _cached_discovered_models

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            models_list = data.get("models", [])
            discovered = []
            for m in models_list:
                raw_name = m.get("name", "")
                clean_name = raw_name.replace("models/", "").strip()
                methods = m.get("supportedGenerationMethods", [])
                if clean_name and "generateContent" in methods:
                    discovered.append(clean_name)

            if discovered:
                ranked = rank_models(discovered)
                _cached_discovered_models = ranked
                _last_discovery_time = now
                logger.info(f"Discovered and ranked {len(ranked)} available Gemini models: {ranked}")
                return ranked
    except Exception as e:
        logger.warning(f"Failed to discover models via Gemini API: {e}; falling back to default list")

    return _cached_discovered_models or DEFAULT_FALLBACK_MODELS

def get_effective_candidates(api_key: str = None) -> list:
    global _pinned_working_model, _model_cooldown_map
    now = time.time()
    raw_pool = discover_available_models(api_key)
    pool = [m for m in raw_pool if _model_cooldown_map.get(m, 0.0) <= now]

    if _pinned_working_model and _pinned_working_model in pool:
        pool.remove(_pinned_working_model)
        pool.insert(0, _pinned_working_model)

    return pool if pool else raw_pool

def on_model_success(model: str):
    global _pinned_working_model
    _pinned_working_model = model
    _model_cooldown_map.pop(model, None)

def on_model_failure(model: str, status_code: int):
    global _pinned_working_model, _model_cooldown_map
    if _pinned_working_model == model:
        _pinned_working_model = None
    if status_code in [429, 503, 404, 500, 502, 504]:
        _model_cooldown_map[model] = time.time() + 60.0
        logger.warning(f"Placed model {model} on 60s cooldown due to HTTP {status_code}")

ALLOWED_CATEGORIES = [
    "Dairy", "Produce", "Meat", "Pantry", "Beverages", "Pharmacy", "Prepared Meals", "Bakery", "Other"
]

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def infer_category(name: str) -> str:
    lower = (name or "").lower()
    if any(k in lower for k in ["milk", "cheese", "yogurt", "butter", "cream", "curd"]):
        return "Dairy"
    if any(k in lower for k in ["apple", "banana", "spinach", "tomato", "salad", "onion", "potato", "fruit", "vegetable"]):
        return "Produce"
    if any(k in lower for k in ["chicken", "beef", "pork", "salmon", "fish", "meat", "egg"]):
        return "Meat"
    if any(k in lower for k in ["bread", "bagel", "croissant", "bun", "toast", "cake"]):
        return "Bakery"
    if any(k in lower for k in ["juice", "soda", "water", "coffee", "tea", "coke", "pepsi", "drink"]):
        return "Beverages"
    if any(k in lower for k in ["medicine", "syrup", "tablet", "capsule", "vitamin"]):
        return "Pharmacy"
    if any(k in lower for k in ["pasta", "pizza", "soup", "curry", "meal"]):
        return "Prepared Meals"
    return "Pantry"

def normalize_category(raw_cat: str, fallback_name: str) -> str:
    if not raw_cat or raw_cat == "null":
        return infer_category(fallback_name)
    for cat in ALLOWED_CATEGORIES:
        if cat.lower() == raw_cat.strip().lower():
            return cat
    return infer_category(fallback_name)

def build_clean_ocr_info(product_name: str, category: str, description: str, ingredients: str) -> str:
    lines = []
    if description and description.strip() and description.strip() != "null":
        lines.append(description.strip())
    else:
        lines.append(f"Identified {product_name} ({category})")
    if ingredients and ingredients.strip() and ingredients.strip() != "null":
        lines.append(f"Ingredients: {ingredients.strip()}")
    return "\n".join(lines)

def extract_fallback_json(raw_text: str) -> dict:
    data = {}
    try:
        name_m = re.search(r'"product_name"\s*:\s*"([^"]+)"', raw_text)
        cat_m = re.search(r'"category"\s*:\s*"([^"]+)"', raw_text)
        desc_m = re.search(r'"description"\s*:\s*"([^"]+)"', raw_text)
        ing_m = re.search(r'"ingredients"\s*:\s*"([^"]+)"', raw_text)
        exp_m = re.search(r'"expiry_date"\s*:\s*"([^"]+)"', raw_text)
        if name_m: data["product_name"] = name_m.group(1)
        if cat_m: data["category"] = cat_m.group(1)
        if desc_m: data["description"] = desc_m.group(1)
        if ing_m: data["ingredients"] = ing_m.group(1)
        if exp_m: data["expiry_date"] = exp_m.group(1)
    except Exception:
        pass
    return data

def analyze_image(front_image_path: str, back_image_path: str = None) -> dict:
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return {"name": None, "category": "Pantry", "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": None, "ocr_confidence": 0.0}

    parts = []
    
    if front_image_path and os.path.exists(front_image_path):
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": encode_image(front_image_path)
            }
        })
    
    if back_image_path and os.path.exists(back_image_path):
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": encode_image(back_image_path)
            }
        })
    
    allowed_categories_str = ", ".join(f'"{c}"' for c in ALLOWED_CATEGORIES)
    today_iso = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year

    system_instruction_text = (
        "Analyze this food packaging with strict temporal grounding. "
        f"TEMPORAL RULES: Today is {today_iso} (Year: {current_year}). Use today's date as reference anchor. "
        f"If only day/month are printed, infer the year relative to {today_iso} (food expiry is in {current_year} or upcoming years). "
        "If a 2-digit year is printed (e.g. '26', '27'), map to '2026', '2027'. Do NOT hallucinate 2024 or 2025 unless clearly printed. "
        "Return ONLY a valid JSON object with keys: "
        f"'product_name' (string), 'category' (string, MUST BE EXACTLY ONE OF: [{allowed_categories_str}]), "
        "'expiry_date' (YYYY-MM-DD or null), 'manufacture_date' (YYYY-MM-DD or null), "
        "'confidence_score' (float between 0.0 and 1.0), "
        "'description' (string, concise 1-line summary describing the product), "
        "'ingredients' (string, visible label ingredients or general typical ingredients for this product)."
    )

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": system_instruction_text
                }
            ]
        },
        "contents": [
            {
                "parts": parts + [{"text": f"Extract product name, category ({allowed_categories_str}), expiry date (anchor today: {today_iso}), description, and ingredients."}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }

    last_error_message = None
    candidates_list = get_effective_candidates(GEMINI_API_KEY)

    for idx, model in enumerate(candidates_list):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            if response.status_code == 200:
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    content_text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                    try:
                        parsed = json.loads(content_text)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON from response on model {model}, attempting regex parsing")
                        parsed = extract_fallback_json(content_text)
                        
                    product_name = parsed.get("product_name") or "Scanned Food Item"
                    category = normalize_category(parsed.get("category"), product_name)
                    description = parsed.get("description", "")
                    ingredients = parsed.get("ingredients", "")
                    clean_ocr_text = build_clean_ocr_info(product_name, category, description, ingredients)

                    raw_expiry = parsed.get("expiry_date")
                    norm_expiry = raw_expiry
                    if raw_expiry and isinstance(raw_expiry, str) and raw_expiry != "null":
                        try:
                            dt = datetime.strptime(raw_expiry.strip(), "%Y-%m-%d")
                            if dt.year < current_year:
                                norm_expiry = dt.replace(year=current_year).strftime("%Y-%m-%d")
                                logger.info(f"Corrected year {dt.year} -> {current_year} for expiry: {raw_expiry}")
                        except Exception:
                            pass

                    on_model_success(model)
                    logger.info(f"Successfully analyzed image using model: {model}")
                    return {
                        "name": product_name,
                        "category": category,
                        "description": description,
                        "ingredients": ingredients,
                        "expiry_date": norm_expiry,
                        "manufacture_date": parsed.get("manufacture_date"),
                        "confidence_score": parsed.get("confidence_score", 0.95),
                        "ocr_confidence": parsed.get("confidence_score", 0.95),
                        "raw_text": clean_ocr_text
                    }
                else:
                    on_model_failure(model, 204)
                    logger.warning(f"Model {model} returned no candidates, falling back...")
                    last_error_message = f"Model {model} returned no candidates"
            else:
                on_model_failure(model, response.status_code)
                is_transient = response.status_code in [503, 429, 404, 500, 502, 504]
                logger.warning(
                    f"Model {model} failed with status {response.status_code} ({'TRANSIENT/OVERLOAD' if is_transient else 'ERROR'}): {response.text[:200]}. "
                    f"{'Falling back to next model...' if idx < len(candidates_list) - 1 else 'All models exhausted.'}"
                )
                last_error_message = f"HTTP {response.status_code}: {response.text[:100]}"
        except requests.exceptions.RequestException as e:
            on_model_failure(model, -1)
            logger.warning(
                f"Model {model} encountered request exception: {e}. "
                f"{'Falling back to next model...' if idx < len(candidates_list) - 1 else 'All models exhausted.'}"
            )
            last_error_message = str(e)

    logger.error(f"All {len(candidates_list)} Gemini models failed for OCR analysis. Last error: {last_error_message}")
    return {"name": None, "category": "Pantry", "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": f"All models failed: {last_error_message}", "ocr_confidence": 0.0}
