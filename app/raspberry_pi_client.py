"""
Raspberry Pi client for Phase 1
- Capture image (picamera, fallback to OpenCV)
- Upload image to gateway (/images endpoint)
- Send scan JSON (/scans endpoint)
- Handle retries with exponential backoff
- Auto reconnect on network errors

Usage:
  python app/raspberry_pi_client.py --gateway http://<gateway-host>:8000 --device-id pi-01

Notes:
- Requires requests. Optional: picamera or opencv-python for capture.
"""

import argparse
import io
import json
import logging
import os
import sys
import time
import threading

# Event to notify background flush worker an item was enqueued and should be retried immediately
FLUSH_EVENT = threading.Event()
from typing import Optional, List
from datetime import date, timedelta, datetime
from pathlib import Path
import shutil
import uuid

import requests
import re
import statistics

# Optional: pytesseract may not be installed on the Pi image build; handle gracefully
try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

# Optional barcode library
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except Exception:
    pyzbar_decode = None

# Try to import picamera (Raspberry Pi). If not available, fallback to OpenCV.
USE_PICAMERA = False
try:
    import picamera
    USE_PICAMERA = True
except Exception:
    try:
        import cv2  # type: ignore
        HAVE_OPENCV = True
    except Exception:
        HAVE_OPENCV = False
    else:
        HAVE_OPENCV = True

from logging.handlers import RotatingFileHandler

# Configure logging: console + rotating file handler
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    # best-effort, continue without failing
    pass

logger = logging.getLogger("raspberry-pi-client")
logger.setLevel(logging.INFO)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# Rotating file handler
fh = RotatingFileHandler(LOGS_DIR / "client.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
fh.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# Avoid duplicate handlers if module reloaded
if not logger.handlers:
    logger.addHandler(ch)
    logger.addHandler(fh)


def capture_image(output_path: str, width: int = 640, height: int = 480, timeout: float = 2.0) -> str:
    """Capture an image and save it to output_path. Returns the path."""
    logger.info("Capturing image to %s", output_path)
    # Picamera path
    if USE_PICAMERA:
        try:
            with picamera.PiCamera() as camera:
                camera.resolution = (width, height)
                # allow camera to warm up
                time.sleep(timeout)
                camera.capture(output_path, format="jpeg")
                logger.info("Captured image with picamera")
                return output_path
        except Exception as e:
            logger.warning("Picamera capture failed: %s", e)
            # fallthrough to OpenCV if available

    if 'HAVE_OPENCV' in globals() and HAVE_OPENCV:
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise RuntimeError("Cannot open camera device")
            ret, frame = cap.read()
            cap.release()
            if not ret:
                raise RuntimeError("Failed to read frame from camera")
            # cv2 writes in BGR format; ensure jpeg
            # default write here; compression applied later
            cv2.imwrite(output_path, frame)
            logger.info("Captured image with OpenCV")
            return output_path
        except Exception as e:
            logger.error("OpenCV capture failed: %s", e)
            raise

    raise RuntimeError("No camera capture method available. Install picamera or opencv-python.")


def compress_image(image_path: str, quality: int = 75) -> None:
    """Re-encode the image as JPEG with given quality to reduce upload size."""
    try:
        if Image is not None:
            img = Image.open(image_path).convert("RGB")
            img.save(image_path, format="JPEG", quality=quality, optimize=True)
        else:
            # fallback to OpenCV
            import cv2
            img = cv2.imread(image_path)
            if img is None:
                return
            # cv2.imwrite supports quality param
            cv2.imwrite(image_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
        logger.debug("Compressed image %s to quality=%d", image_path, quality)
    except Exception as e:
        logger.warning("Could not compress image %s: %s", image_path, e)


# Minimal preprocess fallback since ocr_service is removed
def preprocess_image_for_ocr(image_path: str):
    try:
        import cv2
    except Exception as e:
        logger.error("OpenCV not available for OCR preprocessing fallback: %s", e)
        raise
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f"Failed to read image for OCR: {image_path}")
    return img

def run_ocr_extract(image_path: str) -> dict:
    logger.warning("run_ocr_extract not available (ocr_service missing); skipping OCR")
    return {"name": None, "expiry_date": None, "confidence": 0.0}


def post_with_retries(session: requests.Session, url: str, files=None, json_data=None, headers=None,
                      max_attempts: int = 5, backoff_factor: float = 2.0, timeout: float = 30.0) -> requests.Response:
    """POST with exponential backoff retries for network resiliency."""
    attempt = 0
    while True:
        attempt += 1
        try:
            if files is not None:
                resp = session.post(url, files=files, headers=headers, timeout=timeout)
            else:
                resp = session.post(url, json=json_data, headers=headers, timeout=timeout)
            # treat 5xx as retryable
            if resp.status_code >= 500:
                raise requests.HTTPError(f"Server error: {resp.status_code}")
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            logger.warning("POST attempt %d to %s failed: %s", attempt, url, e)
            if attempt >= max_attempts:
                logger.error("Exceeded max attempts (%d) to %s", max_attempts, url)
                raise
            sleep_for = backoff_factor ** (attempt - 1)
            logger.info("Sleeping for %.1f seconds before retrying...", sleep_for)
            time.sleep(sleep_for)


def upload_image(session: requests.Session, gateway: str, image_path: str, device_id: str) -> dict:
    """Upload image to gateway and return parsed JSON response."""
    url = gateway.rstrip("/") + "/api/v1/images/upload"
    logger.info("Uploading image %s to %s", image_path, url)
    headers = {"X-Device-ID": device_id}
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
        resp = post_with_retries(session, url, files=files, headers=headers)
    resp.raise_for_status()
    logger.info("Upload successful: %s", resp.status_code)
    return resp.json()


def get_with_retries(session: requests.Session, url: str, headers=None, max_attempts: int = 5, backoff_factor: float = 2.0, timeout: float = 10.0) -> requests.Response:
    """GET with exponential backoff retries."""
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"Server error: {resp.status_code}")
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            logger.warning("GET attempt %d to %s failed: %s", attempt, url, e)
            if attempt >= max_attempts:
                logger.error("Exceeded max attempts (%d) to %s", max_attempts, url)
                raise
            sleep_for = backoff_factor ** (attempt - 1)
            logger.info("Sleeping for %.1f seconds before retrying GET...", sleep_for)
            time.sleep(sleep_for)


def detect_barcodes(image_path: str) -> List[str]:
    """Detect barcodes in the image using pyzbar if available; otherwise try OpenCV's barcode detector as fallback."""
    results: List[str] = []
    # Try pyzbar first (most reliable)
    try:
        if pyzbar_decode is not None:
            if Image is not None:
                img = Image.open(image_path).convert("RGB")
            else:
                import cv2
                arr = cv2.imread(image_path)
                from PIL import Image as PILImage
                img = PILImage.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
            decoded = pyzbar_decode(img)
            for d in decoded:
                try:
                    data = d.data.decode('utf-8')
                except Exception:
                    data = str(d.data)
                results.append(data)
            if results:
                return results
    except Exception as e:
        logger.debug("pyzbar barcode detection failed: %s", e)

    # Fallback: try OpenCV's barcode detector if available
    try:
        import cv2
        # OpenCV has a BarcodeDetector from contrib in newer versions
        if hasattr(cv2, 'barcode') or hasattr(cv2, 'QRCodeDetector'):
            img = cv2.imread(image_path)
            # Try barcode detection via cv2.barcode if available
            try:
                if hasattr(cv2, 'barcode'):
                    detector = cv2.barcode_BarcodeDetector()
                    ok, decoded_info, decoded_type, corners = detector.detectAndDecode(img)
                    if ok and decoded_info:
                        for d in decoded_info:
                            if d:
                                results.append(d)
                        return results
            except Exception as e:
                logger.debug("OpenCV barcode detector (barcode module) failed: %s", e)
            # Fallback to QR/1D detection via detectAndDecode
            try:
                qr = cv2.QRCodeDetector()
                data, points, _ = qr.detectAndDecode(img)
                if data:
                    results.append(data)
                    return results
            except Exception as e:
                logger.debug("OpenCV QRCodeDetector failed: %s", e)
    except Exception as e:
        logger.debug("OpenCV fallback for barcode detection not available: %s", e)

    return results


# -- Persistent pending queue utilities --

def ensure_pending_dir(pending_dir: str):
    p = Path(pending_dir)
    (p / "images").mkdir(parents=True, exist_ok=True)
    (p / "entries").mkdir(parents=True, exist_ok=True)


def get_pending_size_bytes(pending_dir: str) -> int:
    p = Path(pending_dir)
    total = 0
    images_dir = p / "images"
    entries_dir = p / "entries"
    if images_dir.exists():
        for f in images_dir.iterdir():
            try:
                total += f.stat().st_size
            except Exception:
                continue
    if entries_dir.exists():
        for f in entries_dir.iterdir():
            try:
                total += f.stat().st_size
            except Exception:
                continue
    return total


def enforce_pending_limits(pending_dir: str, max_entries: int, max_age_days: int, max_bytes: int):
    """Enforce limits on pending queue: count, age, and total size. Remove oldest first."""
    p = Path(pending_dir)
    entries_dir = p / "entries"
    images_dir = p / "images"
    if not entries_dir.exists():
        return
    # load entries and their created_at
    entries = []
    for ef in entries_dir.glob("*.json"):
        try:
            with open(ef, "r", encoding="utf-8") as f:
                data = json.load(f)
            created = data.get("created_at") or int(ef.stat().st_mtime)
        except Exception:
            created = int(ef.stat().st_mtime)
        entries.append((created, ef))
    # sort by oldest first
    entries.sort(key=lambda x: x[0])

    # remove by age
    now = int(time.time())
    age_limit = max_age_days * 24 * 3600
    for created, ef in list(entries):
        if now - created > age_limit:
            # remove this entry and its image
            try:
                with open(ef, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    img = d.get("image")
                    if img:
                        imgp = images_dir / img
                        if imgp.exists():
                            imgp.unlink()
                ef.unlink()
                logger.info("Removed pending entry older than %d days: %s", max_age_days, ef)
            except Exception as e:
                logger.warning("Failed to remove old pending entry %s: %s", ef, e)
            entries.remove((created, ef))

    # enforce max entries
    while max_entries is not None and len(entries) > max_entries:
        created, ef = entries.pop(0)
        try:
            with open(ef, "r", encoding="utf-8") as f:
                d = json.load(f)
                img = d.get("image")
                if img:
                    imgp = images_dir / img
                    if imgp.exists():
                        imgp.unlink()
            ef.unlink()
            logger.info("Removed pending entry to enforce max entries: %s", ef)
        except Exception as e:
            logger.warning("Failed to remove pending entry %s: %s", ef, e)

    # enforce max bytes
    total = get_pending_size_bytes(pending_dir)
    while max_bytes is not None and total > max_bytes and entries:
        created, ef = entries.pop(0)
        try:
            with open(ef, "r", encoding="utf-8") as f:
                d = json.load(f)
                img = d.get("image")
                if img:
                    imgp = images_dir / img
                    if imgp.exists():
                        try:
                            total -= imgp.stat().st_size
                        except Exception:
                            pass
                        imgp.unlink()
            try:
                total -= ef.stat().st_size
            except Exception:
                pass
            ef.unlink()
            logger.info("Removed pending entry to enforce max size: %s", ef)
        except Exception as e:
            logger.warning("Failed to remove pending entry %s during size enforcement: %s", ef, e)


def enqueue_pending_item(pending_dir: str, image_src_path: str, scan_payload: dict, pi_id: str, firmware_version: str,
                         max_pending: int, max_pending_age_days: int, max_pending_bytes: int) -> str:
    """Copy the image into pending_dir/images and write a JSON entry with the scan payload.
    Returns the entry id.
    Also enforces pending queue limits before writing."""
    ensure_pending_dir(pending_dir)

    # enforce limits first
    try:
        enforce_pending_limits(pending_dir, max_pending, max_pending_age_days, max_pending_bytes)
    except Exception as e:
        logger.warning("Failed to enforce pending limits: %s", e)

    entry_id = uuid.uuid4().hex
    images_dir = Path(pending_dir) / "images"
    entries_dir = Path(pending_dir) / "entries"
    dest_image_name = f"{entry_id}.jpg"
    dest_image_path = images_dir / dest_image_name
    try:
        shutil.copy2(image_src_path, dest_image_path)
    except Exception as e:
        logger.error("Failed to copy image to pending queue: %s", e)
        raise
    entry = {
        "id": entry_id,
        "image": dest_image_name,
        "scan_payload": scan_payload,
        "created_at": int(time.time()),
        "retry_count": 0,
        "last_error": None,
        "last_attempt": None,
        "pi_id": pi_id,
        "firmware_version": firmware_version,
    }
    entry_path = entries_dir / f"{entry_id}.json"
    try:
        with open(entry_path, "w", encoding="utf-8") as ef:
            json.dump(entry, ef)
    except Exception as e:
        logger.error("Failed to write pending entry: %s", e)
        # attempt to clean up copied image
        try:
            dest_image_path.unlink()
        except Exception:
            pass
        raise
    logger.info("Enqueued pending item %s", entry_id)
    # Signal the background flush worker to attempt retry immediately
    try:
        FLUSH_EVENT.set()
    except Exception:
        pass
    return entry_id


def flush_pending(session: requests.Session, gateway: str, pending_dir: str, device_id: str, max_attempts: int, backoff: float):
    """Attempt to flush all pending entries. Items that succeed are removed."""
    pending = Path(pending_dir)
    entries_dir = pending / "entries"
    images_dir = pending / "images"
    if not entries_dir.exists():
        return
    for entry_file in sorted(entries_dir.glob("*.json")):
        try:
            with open(entry_file, "r", encoding="utf-8") as f:
                entry = json.load(f)
        except Exception as e:
            logger.error("Failed to load pending entry %s: %s", entry_file, e)
            continue
        entry_id = entry.get("id")
        image_name = entry.get("image")
        scan_payload = entry.get("scan_payload")
        image_path = images_dir / image_name
        if not image_path.exists():
            logger.warning("Pending image missing for entry %s, removing entry", entry_id)
            try:
                entry_file.unlink()
            except Exception:
                pass
            continue

        logger.info("Flushing pending entry %s", entry_id)
        try:
            # Upload image
            url_img = gateway.rstrip("/") + "/api/v1/images/upload"
            with open(image_path, "rb") as imgf:
                files = {"file": (image_name, imgf, "image/jpeg")}
                resp = post_with_retries(session, url_img, files=files, headers={"X-Device-ID": device_id}, max_attempts=max_attempts, backoff_factor=backoff)
            resp.raise_for_status()
            upload_resp = resp.json()
            image_id = upload_resp.get("id") or upload_resp.get("image_id") or upload_resp.get("file_id")
            image_ref = image_id if image_id is not None else upload_resp.get("url") or upload_resp.get("path") or upload_resp

            # Attach image ref to scan payload
            if isinstance(scan_payload, dict):
                scan_payload["image_id"] = image_id if image_id is not None else None

            # Send scan
            url_scan = gateway.rstrip("/") + "/api/v1/scans"
            resp2 = post_with_retries(session, url_scan, json_data=scan_payload, headers={"X-Device-ID": device_id}, max_attempts=max_attempts, backoff_factor=backoff)
            resp2.raise_for_status()

            # On success, remove files
            try:
                image_path.unlink()
            except Exception:
                logger.warning("Could not remove pending image %s", image_path)
            try:
                entry_file.unlink()
            except Exception:
                logger.warning("Could not remove pending entry %s", entry_file)
            logger.info("Flushed pending entry %s successfully", entry_id)
        except Exception as e:
            logger.warning("Failed to flush pending entry %s: %s", entry_id, e)
            # leave the entry for future retry
            continue


def send_scan_json(session: requests.Session, gateway: str, scan_payload: dict, headers: dict | None = None) -> dict:
    url = gateway.rstrip("/") + "/api/v1/scans"
    logger.info("Sending scan JSON to %s", url)
    resp = post_with_retries(session, url, json_data=scan_payload, headers=headers)
    resp.raise_for_status()
    logger.info("Scan JSON sent, status %s", resp.status_code)
    return resp.json()


def _flush_worker(session: requests.Session, gateway: str, pending_dir: str, device_id: str, max_attempts: int, backoff: float, interval_sec: int = 10):
    """Background flush worker: periodically attempts to flush pending queue."""
    logger.info("Flush worker started (interval=%ds)", interval_sec)
    while True:
        # Wait until either the interval passes or FLUSH_EVENT is set (immediate flush request)
        try:
            # If event is set, wait returns immediately; otherwise waits up to interval_sec
            FLUSH_EVENT.wait(interval_sec)
            # Clear the event so future waits block until set again
            if FLUSH_EVENT.is_set():
                FLUSH_EVENT.clear()
        except Exception:
            pass
        try:
            flush_pending(session, gateway, pending_dir, device_id, max_attempts, backoff)
        except Exception as e:
            logger.debug("Flush worker error: %s", e)


def _health_worker(session: requests.Session, gateway: str, headers: dict, interval_sec: int = 30):
    """Background health monitor: periodically checks gateway health."""
    health_url = gateway.rstrip("/") + "/api/v1/system/status"
    logger.info("Health worker started (interval=%ds)", interval_sec)
    while True:
        try:
            # use a short single attempt check to avoid long blocking
            get_with_retries(session, health_url, headers=headers, max_attempts=1, backoff_factor=1.0, timeout=5.0)
            logger.debug("Health check OK")
        except Exception:
            logger.debug("Health check failed")
        time.sleep(interval_sec)


def start_background_workers(session: requests.Session, gateway: str, pending_dir: str, device_id: str, max_attempts: int, backoff: float, flush_interval: int = 10, health_interval: int = 30):
    """Start background daemon threads for flushing pending queue and health monitoring."""
    headers = {"X-Device-ID": device_id}
    t_flush = threading.Thread(target=_flush_worker, args=(session, gateway, pending_dir, device_id, max_attempts, backoff, flush_interval), daemon=True)
    t_health = threading.Thread(target=_health_worker, args=(session, gateway, headers, health_interval), daemon=True)
    t_flush.start()
    t_health.start()
    logger.info("Background workers started: flush every %ds, health every %ds", flush_interval, health_interval)


def main_loop(gateway: str, device_id: str, interval: int, temp_image: str, max_attempts: int, backoff: float, pending_dir: str,
              product_name: str, product_category: str, product_barcode: str, product_expiry: str, product_location: str,
              image_quality: int, firmware_version: str, max_pending: int, max_pending_age_days: int, max_pending_bytes: int):
    session = requests.Session()
    # optional headers
    headers = {"X-Device-ID": device_id}

    # ensure pending dir exists
    ensure_pending_dir(pending_dir)

    # start background workers to flush queue and monitor health
    start_background_workers(session, gateway, pending_dir, device_id, max_attempts, backoff, flush_interval=10, health_interval=30)

    while True:
        try:
            # ensure gateway is reachable with a simple GET; use retries to auto-reconnect
            health_url = gateway.rstrip("/") + "/api/v1/system/status"
            logger.debug("Checking gateway health at %s", health_url)
            try:
                _ = get_with_retries(session, health_url, headers=headers, max_attempts=max_attempts, backoff_factor=backoff)
            except Exception:
                logger.warning("Gateway health check failed, will continue and attempt ops; error will be handled by retries")

            # Flush any pending queued items before capturing new image
            try:
                flush_pending(session, gateway, pending_dir, device_id, max_attempts, backoff)
            except Exception as e:
                logger.warning("Error flushing pending queue: %s", e)

            # Capture image
            capture_image(temp_image)

            # Compress to reduce upload size
            try:
                compress_image(temp_image, quality=image_quality)
            except Exception as e:
                logger.warning("Image compression failed: %s", e)

            # Barcode detection (prefer barcode over OCR for product id)
            try:
                barcodes = detect_barcodes(temp_image)
                if barcodes:
                    logger.info("Detected barcodes: %s", barcodes)
                    product_barcode = barcodes[0]
            except Exception as e:
                logger.warning("Barcode detection failed: %s", e)

            # Run OCR to extract product name, expiry date and confidence. If OCR unavailable, fall back to provided CLI values
            try:
                ocr_res = run_ocr_extract(temp_image)
                o_name = ocr_res.get("name") or product_name
                o_expiry = ocr_res.get("expiry_date") or product_expiry
                o_conf = ocr_res.get("confidence") or 0.0
                logger.info("OCR extracted name=%s expiry=%s confidence=%.2f", o_name, o_expiry, o_conf)
            except Exception as e:
                logger.warning("OCR failed: %s", e)
                o_name = product_name
                o_expiry = product_expiry
                o_conf = 0.0

            # Build scan JSON matching ScanRequest schema (image_id to be filled after upload)
            scan_payload = {
                "name": o_name,
                "category": product_category,
                "barcode": product_barcode,
                "expiry_date": o_expiry,
                "location": product_location,
                "image_id": None,
                "ocr_confidence": o_conf,
            }

            # Upload image
            try:
                upload_resp = upload_image(session, gateway, temp_image, device_id)
                # Expect some kind of identifier in response, e.g., {'id': 123, 'path': ...}
                image_id = upload_resp.get("id") or upload_resp.get("image_id") or upload_resp.get("file_id")
                if image_id is None:
                    # If API returns image URL, include that
                    image_ref = upload_resp.get("url") or upload_resp.get("path") or upload_resp
                    scan_payload["image_id"] = None
                else:
                    scan_payload["image_id"] = image_id
            except Exception as e:
                logger.warning("Image upload failed, enqueuing for retry: %s", e)
                # enqueue the temp image and scan payload for later retry
                try:
                    enqueue_pending_item(pending_dir, temp_image, scan_payload, device_id, firmware_version, max_pending, max_pending_age_days, max_pending_bytes)
                except Exception as ee:
                    logger.error("Failed to enqueue pending item: %s", ee)
                # skip sending scan now
                time.sleep(backoff)
                continue

            # Send scan JSON
            try:
                send_scan_json(session, gateway, scan_payload, headers=headers)
            except Exception as e:
                logger.warning("Sending scan JSON failed, enqueuing for retry: %s", e)
                try:
                    enqueue_pending_item(pending_dir, temp_image, scan_payload, device_id, firmware_version, max_pending, max_pending_age_days, max_pending_bytes)
                except Exception as ee:
                    logger.error("Failed to enqueue pending item: %s", ee)
                time.sleep(backoff)
                continue

            logger.info("Scan cycle complete, sleeping for %d seconds", interval)
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Interrupted by user, exiting")
            break
        except Exception as e:
            logger.error("Error during scan cycle: %s", e)
            # On error, wait and then attempt auto-reconnect via retry loop
            logger.info("Waiting before retrying connection...")
            time.sleep(backoff)


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Raspberry Pi client to capture and upload images to gateway")
    p.add_argument("--gateway", required=True, help="Gateway base URL, e.g. http://gateway.local:8000")
    p.add_argument("--device-id", required=True, help="Unique device id for this Pi")
    p.add_argument("--interval", type=int, default=30, help="Seconds between scans (default 30)")
    p.add_argument("--temp-image", default="/tmp/raspi_capture.jpg" if os.name != 'nt' else "C:\\Windows\\Temp\\raspi_capture.jpg",
                   help="Temporary path to save captured images")
    p.add_argument("--max-attempts", type=int, default=5, help="Max attempts for network retries")
    p.add_argument("--backoff", type=float, default=2.0, help="Backoff factor for retries")
    p.add_argument("--pending-dir", default=("/var/lib/raspi_client/pending" if os.name != 'nt' else os.path.join(os.getenv('TEMP', 'C:\\Temp'), 'raspi_pending')), help="Directory to store pending uploads")
    p.add_argument("--image-quality", type=int, default=75, help="JPEG quality for compressed uploads (default 75)")
    p.add_argument("--firmware-version", default="0.0.0", help="Firmware/version string to include in queue metadata")
    p.add_argument("--max-pending", type=int, default=1000, help="Maximum pending entries to keep (default 1000)")
    p.add_argument("--max-pending-age", type=int, default=7, help="Maximum age (days) to keep pending entries (default 7)")
    p.add_argument("--max-pending-bytes", type=int, default=500*1024*1024, help="Maximum total size (bytes) of pending queue (default 500MB)")

    # Product / scan fields (match ScanRequest schema)
    p.add_argument("--name", default="unknown", help="Product name to include in scan payload")
    p.add_argument("--category", default="unknown", help="Product category for the scan payload")
    p.add_argument("--barcode", default="", help="Product barcode string")
    p.add_argument("--expiry-date", dest="expiry_date", default=None, help="Expiry date (YYYY-MM-DD). Defaults to today + 365 days")
    p.add_argument("--location", default="unknown", help="Location string for the scan payload (e.g., shelf id)")

    return p


if __name__ == "__main__":
    args = build_argparser().parse_args()

    # Normalize expiry_date: if not provided, set to one year from today
    if args.expiry_date is None:
        args.expiry_date = (date.today() + timedelta(days=365)).isoformat()

    try:
        main_loop(
            args.gateway,
            args.device_id,
            args.interval,
            args.temp_image,
            args.max_attempts,
            args.backoff,
            args.pending_dir,
            args.name,
            args.category,
            args.barcode,
            args.expiry_date,
            args.location,
            args.image_quality,
            args.firmware_version,
            args.max_pending,
            args.max_pending_age,
            args.max_pending_bytes,
        )
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)
