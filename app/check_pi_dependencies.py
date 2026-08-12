"""
Simple dependency checker for Raspberry Pi client.
Checks for:
- system binaries: tesseract, zbar (zbarimg)
- Python packages: opencv-python (cv2), pytesseract, pyzbar, pillow, requests

Usage:
  python app/check_pi_dependencies.py

This script exits with code 0 if all required items are present, non-zero otherwise.
"""
import shutil
import sys
import importlib

required_bins = ["tesseract", "zbarimg"]
required_pkgs = ["cv2", "pytesseract", "pyzbar", "PIL", "requests"]

missing = False

print("Checking system binaries:")
for b in required_bins:
    path = shutil.which(b)
    if path:
        print(f"  OK: {b} -> {path}")
    else:
        print(f"  MISSING: {b}")
        missing = True

print("\nChecking Python packages:")
for pkg in required_pkgs:
    try:
        importlib.import_module(pkg)
        print(f"  OK: {pkg}")
    except Exception:
        print(f"  MISSING: {pkg}")
        missing = True

print("\nNotes:")
print(" - Install tesseract on Debian/Ubuntu: sudo apt install tesseract-ocr")
print(" - Install zbar on Debian/Ubuntu: sudo apt install zbar-tools")
print(" - Python packages: pip install opencv-python pytesseract pyzbar pillow requests")

if missing:
    print("\nSome dependencies are missing. Please install the missing items and re-run this script.")
    sys.exit(2)
else:
    print("\nAll dependencies appear to be installed.")
    sys.exit(0)
