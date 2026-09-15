import os
import base64
import requests
import json
import logging

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(front_image_path: str, back_image_path: str = None) -> dict:
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return {"name": None, "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": None, "ocr_confidence": 0.0}

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
    
    # Text prompt / system instruction context
    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": "Analyze this food packaging. Return ONLY a JSON object with keys: 'product_name' (string), 'expiry_date' (YYYY-MM-DD), 'manufacture_date' (YYYY-MM-DD), and 'confidence_score' (float). If a date is missing, return null."
                }
            ]
        },
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.0
        }
    }

    try:
        response = requests.post(URL, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        result = response.json()
        
        # Get the first candidate text
        candidates = result.get("candidates", [])
        if not candidates:
            return {"name": None, "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": "No candidates", "ocr_confidence": 0.0}
            
        content_text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
        
        try:
            parsed = json.loads(content_text)
            return {
                "name": parsed.get("product_name"),
                "expiry_date": parsed.get("expiry_date"),
                "manufacture_date": parsed.get("manufacture_date"),
                "confidence_score": parsed.get("confidence_score", 0.0),
                "ocr_confidence": parsed.get("confidence_score", 0.0),
                "raw_text": content_text
            }
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {content_text}")
            return {"name": None, "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": content_text, "ocr_confidence": 0.0}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed: {e}")
        if e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return {"name": None, "expiry_date": None, "manufacture_date": None, "confidence_score": 0.0, "raw_text": str(e), "ocr_confidence": 0.0}
