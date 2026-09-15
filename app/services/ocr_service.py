import os
import re
import base64
import requests
import json
import logging

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

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
    system_instruction_text = (
        "Analyze this food packaging. Return ONLY a valid JSON object with keys: "
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
                "parts": parts + [{"text": f"Extract product name, category ({allowed_categories_str}), expiry date, description, and ingredients."}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(URL, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        result = response.json()
        
        candidates = result.get("candidates", [])
        if not candidates:
            return {"name": None, "category": "Pantry", "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": "No candidates", "ocr_confidence": 0.0}
            
        content_text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
        
        try:
            parsed = json.loads(content_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from response: {content_text}, attempting fallback regex parser")
            parsed = extract_fallback_json(content_text)
            
        product_name = parsed.get("product_name") or "Scanned Food Item"
        category = normalize_category(parsed.get("category"), product_name)
        description = parsed.get("description", "")
        ingredients = parsed.get("ingredients", "")
        clean_ocr_text = build_clean_ocr_info(product_name, category, description, ingredients)

        return {
            "name": product_name,
            "category": category,
            "description": description,
            "ingredients": ingredients,
            "expiry_date": parsed.get("expiry_date"),
            "manufacture_date": parsed.get("manufacture_date"),
            "confidence_score": parsed.get("confidence_score", 0.95),
            "ocr_confidence": parsed.get("confidence_score", 0.95),
            "raw_text": clean_ocr_text
        }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed: {e}")
        return {"name": None, "category": "Pantry", "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": str(e), "ocr_confidence": 0.0}
