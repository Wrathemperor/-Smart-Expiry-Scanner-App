"""OCR service wrapper for the Gateway.

This module exposes OCRService which provides a single entrypoint `analyze_image`
accepting a filesystem image path and returning a structured result.

It reuses preprocessing and OCR helpers from app.raspberry_pi_client when available
so that desktop and Raspberry Pi code shares a single implementation.

Return structure (dict):
- raw_text: str | None  -- full OCR text (may be empty)
- ocr_confidence: float -- 0.0 .. 1.0
- expiry_date: str | None -- ISO date string YYYY-MM-DD when found
- expiry_confidence: float -- 0.0 .. 1.0 (heuristic)
- metadata: dict -- extra info (which implementation was used)

The implementation tries to be robust to missing optional dependencies and will
fail gracefully by returning confidence=0.0 if OCR cannot run.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
import logging
import json
import re
import statistics
from datetime import date, datetime
import os
import shutil
import platform
from pathlib import Path

logger = logging.getLogger("gateway.ocr")
logger.setLevel(logging.DEBUG)

# Log to stdout for testing
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None  # type: ignore
    np = None

try:
    import pytesseract
except Exception:
    pytesseract = None  # type: ignore

try:
    from PIL import Image as PILImage, ImageOps
except Exception:
    PILImage = None  # type: ignore
    ImageOps = None

TESSERACT_AVAILABLE = False

def _configure_tesseract() -> bool:
    global pytesseract, TESSERACT_AVAILABLE
    if pytesseract is None:
        logger.error("pytesseract Python package is not installed.")
        return False

    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd:
        env_path = Path(env_cmd)
        if env_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(env_path)
            return True

    try:
        if platform.system().lower().startswith("windows"):
            repo_root = Path(__file__).resolve().parents[2]
            local = repo_root / "tesseract.exe"
            if local.exists():
                pytesseract.pytesseract.tesseract_cmd = str(local)
                return True
    except Exception:
        pass

    if shutil.which("tesseract"):
        return True

    return False

try:
    TESSERACT_AVAILABLE = _configure_tesseract()
except Exception as e:
    logger.exception("Error while configuring tesseract: %s", e)
    TESSERACT_AVAILABLE = False

PADDLE_AVAILABLE = False
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except Exception as e:
    logger.warning(f"PaddleOCR python package not available: {e}")
    PaddleOCR = None

_paddle_ocr_instance = None

def _get_paddle_ocr():
    global _paddle_ocr_instance
    if not PADDLE_AVAILABLE or PaddleOCR is None:
        return None
    if _paddle_ocr_instance is None:
        try:
            logger.info("Initializing PaddleOCR engine...")
            _paddle_ocr_instance = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                engine='paddle'
            )
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR engine: {e}")
            _paddle_ocr_instance = None
    return _paddle_ocr_instance


def _normalize_text_for_dates(s: str) -> str:
    s = s.strip()
    s = s.replace('\u00b0', '.')
    s = s.replace('\u00b7', '.')
    s = s.replace('\u2022', '.')
    s = s.replace('\u00a0', ' ')
    s = re.sub(r"[\s]+", " ", s)
    return s


def _try_parse_date(s: str) -> Optional[str]:
    """Try to parse a date string into YYYY-MM-DD. Returns ISO date or None."""
    s = s.strip()
    s = re.sub(r"(?i)(exp|expiry|expiration|best before|best-before|bb|use by|use-by)[:\s]*", "", s)
    s = _normalize_text_for_dates(s)
    s = re.sub(r"[\u00b0\u00b7\u2022]+", ".", s)
    s = re.sub(r"[\./\-]+", ".", s)
    s = re.sub(r"[^0-9A-Za-z\s\.]", "", s)
    s = s.strip(' .,-')
    
    # Check for Month/Year first like 09.2026 or 12.2026
    m = re.fullmatch(r"(\d{1,2})\.(\d{4})", s)
    if m:
        month, year = m.groups()
        try:
            dt = datetime(year=int(year), month=int(month), day=1)
            return dt.date().isoformat()
        except Exception:
            pass

    formats = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%b %d %Y", "%d %b %Y", "%B %Y", "%m.%d.%Y", "%m/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat()
        except Exception:
            continue

    # Removed dateutil fallback to prevent fuzzy parsing of random numbers
    return None

def normalize_orientation(image_path: str):
    """Load image with PIL and fix EXIF orientation, then convert to OpenCV format."""
    try:
        pil_img = PILImage.open(image_path)
        pil_img = ImageOps.exif_transpose(pil_img)
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.warning(f"Failed EXIF transpose: {e}")
        return cv2.imread(str(image_path))


def generate_preprocessing_variants(image_path: str) -> dict:
    """Generate multiple image variants for OCR."""
    orig = normalize_orientation(image_path)
    if orig is None:
        raise RuntimeError(f"Failed to read image for OCR: {image_path}")
        
    h, w = orig.shape[:2]
    logger.debug(f"Original image dimensions: {w}x{h}")
    
    max_w = 1600
    if w > max_w:
        scale = max_w / float(w)
        img = cv2.resize(orig, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    else:
        img = orig.copy()
        
    ph, pw = img.shape[:2]
    logger.debug(f"Preprocessing image dimensions: {pw}x{ph}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    contrast = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    adaptive = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 31, 10)
    _, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    variants = {
        "original": img,
        "grayscale": gray,
        "contrast": contrast,
        "upscaled": upscaled,
        "adaptive": adaptive,
        "otsu": otsu
    }
    
    debug_dir = Path("debug_ocr")
    debug_dir.mkdir(exist_ok=True)
    for name, v_img in variants.items():
        out_path = str(debug_dir / f"{name}.png")
        cv2.imwrite(out_path, v_img)
        
    return variants


def extract_expiry_from_lines(line_items: list) -> tuple:
    date_regex = re.compile(r"(\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[\s]\w{3,9}[\s]\d{4}\b|\b\w{3,9}[\s]\d{1,2}[\s]\d{4}\b|\b\d{2}[\/\-\.]\d{4}\b)")
    expiry_keywords = re.compile(r"(?i)(exp|expiry|expiration|use by|use-by|best before|best-before|bb)")
    mfd_keywords = re.compile(r"(?i)\b(mfd|mfg|manufacture|manufactured|manufacturing date|pkd|packed|packaging date)\b")

    # Pass 1: Expiry keyword context (same line or adjacent lines, and no MFD keyword context)
    for idx, (ln, text, conf) in enumerate(line_items):
        if len(text) < 3: continue
        normalized_text = _normalize_text_for_dates(text)
        
        m = date_regex.search(normalized_text)
        if not m: continue
        
        parsed = _try_parse_date(m.group(0))
        if not parsed: continue
        
        prev_text = _normalize_text_for_dates(line_items[idx-1][1]) if idx > 0 else ""
        next_text = _normalize_text_for_dates(line_items[idx+1][1]) if idx < len(line_items) - 1 else ""
        
        if (mfd_keywords.search(normalized_text) or 
            mfd_keywords.search(prev_text) or 
            mfd_keywords.search(next_text)):
            logger.debug(f"Rejected EXP candidate due to MFD in context: {text} (context: {prev_text} | {next_text})")
            continue
            
        has_exp_keyword = (expiry_keywords.search(normalized_text) or
                           expiry_keywords.search(prev_text) or
                           expiry_keywords.search(next_text))
                           
        if has_exp_keyword:
            logger.debug(f"Found high-confidence EXP date: {parsed} (line: {text}, context: {prev_text} | {next_text})")
            return parsed, conf

    # Pass 2: Backup/Fallback to any date with no manufacturing keyword context
    for idx, (ln, text, conf) in enumerate(line_items):
        if len(text) < 3: continue
        normalized_text = _normalize_text_for_dates(text)
        
        m = date_regex.search(normalized_text)
        if not m: continue
        
        parsed = _try_parse_date(m.group(0))
        if not parsed: continue
        
        prev_text = _normalize_text_for_dates(line_items[idx-1][1]) if idx > 0 else ""
        next_text = _normalize_text_for_dates(line_items[idx+1][1]) if idx < len(line_items) - 1 else ""
        
        if (mfd_keywords.search(normalized_text) or 
            mfd_keywords.search(prev_text) or 
            mfd_keywords.search(next_text)):
            continue
            
        logger.debug(f"Fallback to generic date: {parsed} (line: {text}, context: {prev_text} | {next_text})")
        return parsed, conf

    return None, 0.0


def run_ocr_extract(image_path: str) -> dict:
    # 1. Try PaddleOCR first
    ocr_engine = _get_paddle_ocr()
    if ocr_engine is not None:
        try:
            logger.info(f"Attempting OCR using PaddleOCR for {image_path}...")
            img = normalize_orientation(image_path)
            if img is not None:
                h, w = img.shape[:2]
                max_side = 1200
                if max(h, w) > max_side:
                    scale = max_side / float(max(h, w))
                    img_small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                else:
                    img_small = img.copy()
                
                result = ocr_engine.predict(img_small)
                if result and len(result) > 0:
                    res = result[0]
                    texts = res.get('rec_texts', [])
                    scores = res.get('rec_scores', [])
                    
                    paddle_raw_text = "\n".join(texts)
                    line_items = [(i, text, float(score)) for i, (text, score) in enumerate(zip(texts, scores))]
                    
                    paddle_expiry, exp_conf = extract_expiry_from_lines(line_items)
                    paddle_conf = float(statistics.mean([float(s) for s in scores])) if scores else 0.0
                    
                    # Extract name candidate
                    name_candidate = None
                    name_scores = []
                    for ln, text, conf in line_items:
                        if paddle_expiry and paddle_expiry in text: continue
                        if re.fullmatch(r"[\d\s-]{4,}", text): continue
                        if len(text) < 3: continue
                        score = conf * (len(text) / 50.0)
                        name_scores.append((score, text, conf))
                    
                    if name_scores:
                        _, name_candidate, _ = max(name_scores, key=lambda x: x[0])
                    elif line_items:
                        name_candidate = line_items[0][1]
                    paddle_name = name_candidate
                    
                    logger.info(f"PaddleOCR scan results - Expiry: {paddle_expiry}, Conf: {paddle_conf:.4f}")
                    
                    # Return immediately only if we found an expiry date
                    if paddle_expiry:
                        return {
                            "name": paddle_name,
                            "expiry_date": paddle_expiry,
                            "confidence": round(paddle_conf * 100.0, 2),
                            "raw_text": paddle_raw_text
                        }
                    else:
                        logger.info("PaddleOCR found no expiry date. Falling back to multi-variant Tesseract ensemble...")
        except Exception as ex:
            logger.error(f"PaddleOCR process failed: {ex}")

    # 2. Fall back to existing Tesseract pipeline
    if not TESSERACT_AVAILABLE or pytesseract is None or PILImage is None:
        logger.error("Tesseract runtime unavailable (fallback failed).")
        return {"name": None, "expiry_date": None, "confidence": 0.0}

    try:
        variants = generate_preprocessing_variants(image_path)
    except Exception as e:
        logger.warning("OCR preprocessing failed: %s", e)
        return {"name": None, "expiry_date": None, "confidence": 0.0}

    psm_modes = [6, 11, 12]
    
    best_expiry = None
    best_overall_conf = 0.0
    best_name = None
    best_variant = None
    best_psm = None
    best_raw_text = ""
    
    all_results = []

    for variant_name, v_img in variants.items():
        if len(v_img.shape) == 2:
            pil_img = PILImage.fromarray(cv2.cvtColor(v_img, cv2.COLOR_GRAY2RGB))
        else:
            pil_img = PILImage.fromarray(cv2.cvtColor(v_img, cv2.COLOR_BGR2RGB))
            
        for psm in psm_modes:
            config = f'--psm {psm}'
            try:
                ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config=config)
                raw_text = pytesseract.image_to_string(pil_img, config=config)
            except Exception as e:
                logger.debug(f"pytesseract failed for {variant_name} psm {psm}: {e}")
                continue

            n_boxes = len(ocr_data.get('level', []))
            lines = {}
            confidences = []
            for i in range(n_boxes):
                text = (ocr_data.get('text', [])[i] or '').strip()
                conf = ocr_data.get('conf', [])[i]
                line_num = ocr_data.get('line_num', [])[i]
                if not text:
                    continue
                try:
                    conf_val = float(conf)
                except Exception:
                    conf_val = -1.0
                if conf_val >= 0:
                    confidences.append(conf_val)
                lines.setdefault(line_num, []).append((text, conf_val))

            line_items = []
            for ln, tokens in lines.items():
                texts = [t for t, _ in tokens]
                confs = [c for _, c in tokens if c >= 0]
                line_text = ' '.join(texts)
                avg_conf = float(statistics.mean(confs)) if confs else 0.0
                line_items.append((ln, line_text, avg_conf))

            line_items.sort(key=lambda x: x[0])
            overall_conf = float(statistics.mean(confidences)) if confidences else 0.0
            
            expiry, exp_conf = extract_expiry_from_lines(line_items)
            
            name_candidate = None
            name_scores = []
            for ln, text, conf in line_items:
                if expiry and expiry in text: continue
                if re.fullmatch(r"[\d\s-]{4,}", text): continue
                if len(text) < 3: continue
                score = conf * (len(text) / 50.0)
                name_scores.append((score, text, conf))
            
            if name_scores:
                _, name_candidate, _ = max(name_scores, key=lambda x: x[0])
            elif line_items:
                name_candidate = line_items[0][1]

            all_results.append({
                "variant": variant_name,
                "psm": psm,
                "expiry": expiry,
                "conf": overall_conf,
                "name": name_candidate,
                "raw": raw_text
            })
            
            if expiry:
                if best_expiry is None or overall_conf > best_overall_conf:
                    best_expiry = expiry
                    best_overall_conf = overall_conf
                    best_name = name_candidate
                    best_variant = variant_name
                    best_psm = psm
                    best_raw_text = raw_text
                    
    if best_expiry is None and all_results:
        best_res = max(all_results, key=lambda x: x["conf"])
        best_overall_conf = best_res["conf"]
        best_name = best_res["name"]
        best_variant = best_res["variant"]
        best_psm = best_res["psm"]
        best_raw_text = best_res["raw"]
        
    logger.info(f"Selected Best: Variant={best_variant}, PSM={best_psm}, Expiry={best_expiry}, Conf={best_overall_conf}")
    logger.info(f"Raw text:\n{best_raw_text}")

    return {
        "name": best_name, 
        "expiry_date": best_expiry, 
        "confidence": round(best_overall_conf, 2),
        "raw_text": best_raw_text
    }


class OCRService:
    def __init__(self) -> None:
        self.implementation = "ocr_service.self_contained"

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "raw_text": None,
            "ocr_confidence": 0.0,
            "expiry_date": None,
            "expiry_confidence": 0.0,
            "metadata": {"implementation": self.implementation},
        }

        try:
            r = run_ocr_extract(image_path)
            
            if isinstance(r, dict):
                expiry = r.get("expiry_date")
                ocr_conf = float(r.get("confidence") or 0.0)
                raw_text = r.get("raw_text")

                result.update({
                    "raw_text": raw_text,
                    "ocr_confidence": max(0.0, min(1.0, ocr_conf if ocr_conf <= 1.0 else ocr_conf / 100.0)),
                    "expiry_date": expiry,
                    "expiry_confidence": max(0.0, min(1.0, (ocr_conf if ocr_conf <= 1.0 else ocr_conf / 100.0))) if expiry else 0.0,
                })
        except Exception as e:
            logger.exception("OCRService analyze_image failed: %s", e)

        return result


_service = OCRService()

def analyze_image(image_path: str) -> Dict[str, Any]:
    return _service.analyze_image(image_path)
