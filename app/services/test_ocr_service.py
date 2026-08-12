"""Small test script to exercise the OCR service.

Usage:
    python -m app.services.test_ocr_service --image PATH/TO/IMAGE

Prints a JSON blob with the OCR result.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.services.ocr_service import analyze_image


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="test_ocr_service")
    parser.add_argument("--image", required=True, help="Path to image file to OCR")
    args = parser.parse_args(argv)

    res = analyze_image(args.image)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
