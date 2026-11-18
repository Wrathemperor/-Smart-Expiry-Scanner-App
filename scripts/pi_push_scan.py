#!/usr/bin/env python3
"""
ShelfSense — Raspberry Pi Direct Cloud Queue Pusher
====================================================
Designed for hardware developers and test benches.
This standalone script captures an image from a Raspberry Pi Camera
(or USB webcam) and immediately uploads it directly to the ShelfSense
Cloud Gateway, placing it into the review queue.

Usage:
    # 1. Single snapshot & push to cloud:
    python pi_push_scan.py --gateway http://<YOUR_GATEWAY_IP_OR_DOMAIN>:8000

    # 2. Continuous mode (captures every 10 seconds):
    python pi_push_scan.py --gateway http://<YOUR_GATEWAY_IP_OR_DOMAIN>:8000 --loop --interval 10

    # 3. Physical hardware button mode (triggers on GPIO 17 button press):
    python pi_push_scan.py --gateway http://<YOUR_GATEWAY_IP_OR_DOMAIN>:8000 --gpio-button 17
"""

import os
import sys
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import requests

def capture_photo(output_path: str) -> bool:
    """
    Captures a photo using the best available camera backend:
    1. rpicam-still (Raspberry Pi OS Bookworm / Pi Camera Module)
    2. libcamera-still (Raspberry Pi OS Bullseye)
    3. fswebcam (USB Webcam fallback)
    4. OpenCV (cv2)
    """
    # 1. Try modern Raspberry Pi Camera (Bookworm)
    try:
        res = subprocess.run(
            ["rpicam-still", "-t", "1000", "-o", output_path, "--width", "1280", "--height", "960", "-n"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print("[+] Captured via rpicam-still")
            return True
    except FileNotFoundError:
        pass

    # 2. Try legacy libcamera (Bullseye)
    try:
        res = subprocess.run(
            ["libcamera-still", "-t", "1000", "-o", output_path, "--width", "1280", "--height", "960", "-n"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print("[+] Captured via libcamera-still")
            return True
    except FileNotFoundError:
        pass

    # 3. Try fswebcam (Standard USB Webcam)
    try:
        res = subprocess.run(
            ["fswebcam", "-r", "1280x720", "--no-banner", output_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print("[+] Captured via fswebcam (USB webcam)")
            return True
    except FileNotFoundError:
        pass

    # 4. Try OpenCV (cv2)
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        # Warmup sensor
        for _ in range(5):
            cap.read()
        ret, frame = cap.read()
        if ret and frame is not None:
            cv2.imwrite(output_path, frame)
            cap.release()
            print("[+] Captured via OpenCV /dev/video0")
            return True
        cap.release()
    except Exception as e:
        print(f"[-] OpenCV capture failed: {e}")

    print("[-] ERROR: No working camera detected! Ensure Pi Camera ribbon or USB webcam is plugged in.")
    return False

def push_image_to_cloud_queue(gateway_url: str, image_path: str, device_id: str) -> dict:
    """
    Directly posts the captured image into the ShelfSense Cloud Gateway.
    The server runs multi-modal OCR (Gemini/Bedrock) and stores the image
    and scan directly into the Pending Review Queue.
    """
    clean_gateway = gateway_url.rstrip("/")
    endpoint = f"{clean_gateway}/api/v1/scans/from-image"
    
    print(f"[*] Uploading {image_path} ({os.path.getsize(image_path)/1024:.1f} KB) to {endpoint}...")

    with open(image_path, "rb") as img_file:
        files = {
            "front_image": (os.path.basename(image_path), img_file, "image/jpeg")
        }
        data = {
            "device_id": device_id
        }
        
        try:
            resp = requests.post(endpoint, files=files, data=data, timeout=30)
            if resp.status_code in [200, 201]:
                res_data = resp.json()
                print("="*60)
                print("[SUCCESS] IMAGE SUCCESSFULLY PLACED IN SCAN QUEUE!")
                print(f" > Scan ID:        #{res_data.get('id')}")
                print(f" > Product Name:   {res_data.get('product_name') or 'Pending Review'}")
                print(f" > Expiry Date:    {res_data.get('expiry_date_iso') or 'Unspecified'}")
                print(f" > Confidence:     {res_data.get('ocr_confidence', 0.0) * 100:.1f}%")
                print(f" > Queue Status:   {res_data.get('status')}")
                print(f" > View in Admin:  {clean_gateway}/admin")
                print("="*60)
                return res_data
            else:
                print(f"[-] Server returned error {resp.status_code}: {resp.text}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"[-] Connection failed: {e}")
            print("    Check that the Raspberry Pi has internet access and can reach the Gateway URL.")
            return {}

def trigger_single_scan(gateway_url: str, device_id: str, temp_file: str = "/tmp/shelfsense_scan.jpg"):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Triggering capture on {device_id}...")
    if capture_photo(temp_file):
        push_image_to_cloud_queue(gateway_url, temp_file, device_id)

def main():
    parser = argparse.ArgumentParser(description="ShelfSense Raspberry Pi Direct Cloud Queue Pusher")
    parser.add_argument("--gateway", type=str, required=True, help="Cloud Gateway URL (e.g. http://192.168.1.50:8000 or https://gateway.yourdomain.com)")
    parser.add_argument("--device-id", type=str, default="pi-hardware-01", help="Device identifier string")
    parser.add_argument("--loop", action="store_true", help="Run continuously in a loop")
    parser.add_argument("--interval", type=int, default=10, help="Interval between scans in seconds (if --loop is active)")
    parser.add_argument("--gpio-button", type=int, default=None, help="Optional GPIO pin number for physical push button trigger")

    args = parser.parse_args()

    print("==========================================================")
    print("      ShelfSense — Raspberry Pi Cloud Queue Pusher        ")
    print("==========================================================")
    print(f"Target Gateway: {args.gateway}")
    print(f"Device ID:      {args.device_id}")

    # Optional GPIO button trigger
    if args.gpio_button is not None:
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(args.gpio_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            print(f"[*] Listening for button press on GPIO {args.gpio_button} (Connect pin to GND via push button)...")
            while True:
                button_state = GPIO.input(args.gpio_button)
                if button_state == False: # Button pressed
                    print("[!] Physical button pressed!")
                    trigger_single_scan(args.gateway, args.device_id)
                    time.sleep(2) # Debounce
                time.sleep(0.1)
        except ImportError:
            print("[-] RPi.GPIO not installed. Install via: sudo apt install python3-rpi.gpio")
            sys.exit(1)

    # Continuous loop mode
    if args.loop:
        print(f"[*] Running in continuous mode (scanning every {args.interval}s)... Press Ctrl+C to stop.")
        while True:
            trigger_single_scan(args.gateway, args.device_id)
            time.sleep(args.interval)

    # Default: single trigger
    trigger_single_scan(args.gateway, args.device_id)

if __name__ == "__main__":
    main()
