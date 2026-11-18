# ShelfSense — Complete Hardware Setup & Cloud Queue Connection Guide

> **Target Audience:** Hardware Engineers, IoT Developers, and Demo Presenters  
> **Goal:** Set up a Raspberry Pi from scratch, connect the camera module, connect it directly to the ShelfSense Cloud Gateway, and push scanned food packaging photos directly into the review queue.

---

## 1. Hardware Checklist

Before beginning, ensure you have the following components:

| Component | Recommendation / Specifications |
| :--- | :--- |
| **Raspberry Pi Board** | Raspberry Pi 4 Model B (2GB/4GB/8GB), Raspberry Pi 5, or Pi 3 Model B+. |
| **Camera** | **Option A (Recommended):** Raspberry Pi Camera Module 2 or 3 (CSI ribbon cable).<br>**Option B:** Any standard USB Webcam (e.g., Logitech C270, C920, or generic plug-and-play UVC camera). |
| **MicroSD Card** | 16 GB or 32 GB Class 10 / UHS-1 MicroSD card. |
| **Power Supply** | Official 5V 3A USB-C Power Supply (or 5.1V 2.5A Micro-USB for Pi 3). |
| **Network** | Wi-Fi (2.4GHz/5GHz) or an Ethernet cable connected to your router/hotspot. |
| **(Optional) Tactile Button** | Standard 2-pin push button + 2 female-to-female jumper wires (for physical snapshot button). |

---

## 2. Step 1: Flashing the OS (Headless Setup — No Monitor Needed)

You do **not** need a monitor or keyboard for the Raspberry Pi. You can configure everything directly when writing the SD card:

1. Download and install **Raspberry Pi Imager** on your computer:  
   👉 [https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/)
2. Insert your MicroSD card into your computer's card reader.
3. Open Raspberry Pi Imager:
   * **Device:** Select your Pi model (e.g., `Raspberry Pi 4` or `Raspberry Pi 5`).
   * **Operating System:** Choose `Raspberry Pi OS (64-bit)` (Debian Bookworm).
   * **Storage:** Select your inserted MicroSD card.
4. When prompted **"Would you like to apply OS customization settings?"**, click **EDIT SETTINGS**:
   * **Hostname:** Set to `shelfsense-pi` (or leave default `raspberrypi`).
   * **Username and password:** Set username to `pi` and choose a secure password (e.g., `shelfsense123`).
   * **Configure wireless LAN:** Enter your Wi-Fi Name (SSID) and Password. Set Wireless LAN country (e.g., `IN`, `US`, `GB`).
   * **SERVICES tab:** Check **"Enable SSH"** and select **"Use password authentication"**.
5. Click **SAVE** and then click **YES** to write and verify the card.

---

## 3. Step 2: Physical Hardware Assembly

### A. Camera Connection:
* **If using a CSI Ribbon Pi Camera:**
  1. Locate the **CAMERA (CSI)** port between the HDMI port and the audio jack (on Pi 4) or dedicated CAM port (on Pi 5).
  2. Gently pull the plastic clip on the port upwards.
  3. Insert the ribbon cable:
     * **On Pi 4/3:** The blue plastic backing faces the **USB/Ethernet ports**; the exposed silver contacts face the **micro-HDMI ports**.
     * **On Pi 5:** Use the official Pi 5 camera adapter ribbon; silver contacts face towards the HDMI connector.
  4. Push the plastic clip down firmly to lock the ribbon in place.
* **If using a USB Webcam:**
  1. Simply plug the webcam into any **USB 3.0 (blue)** port on the Raspberry Pi.

### B. (Optional) Physical Push-to-Scan Button:
To let users press a physical button on your hardware prototype to snap a photo:
* Connect **Terminal 1** of the button to **GPIO 17 (Physical Pin 11)**.
* Connect **Terminal 2** of the button to any **GND (Ground, Physical Pin 9)**.

```
Raspberry Pi GPIO Header:
 Pin 1 (3.3V)   [ . . ]  Pin 2 (5V)
 Pin 3 (SDA)    [ . . ]  Pin 4 (5V)
 Pin 5 (SCL)    [ . . ]  Pin 6 (GND)
 Pin 7 (GPIO 4) [ . . ]  Pin 8 (TXD)
 Pin 9 (GND)    [ . . ]  Pin 10 (RXD)  <-- Connect Button Wire 1 to Pin 9
 Pin 11(GPIO 17)[ . . ]  Pin 12 (GPIO 18) <-- Connect Button Wire 2 to Pin 11
```

---

## 4. Step 3: Boot Up & Connect via SSH

1. Insert the flashed MicroSD card into the Pi.
2. Plug in the power supply. Wait ~60 seconds for the first boot.
3. Open a terminal (macOS/Linux) or PowerShell (Windows) on your PC (connected to the same Wi-Fi/network):
   ```bash
   ssh pi@shelfsense-pi.local
   ```
   *(If `shelfsense-pi.local` is not found, check your router's client list or hotspot connected devices to find the Pi's IP address, e.g., `ssh pi@192.168.1.105`).*
4. Enter the password you configured in Step 1. You are now logged in!

### Verify Camera Detection:
Run the diagnostic command:
```bash
# For Pi Camera Module (Bookworm):
rpicam-hello -t 2000

# For USB Webcams:
ls -l /dev/video*
```
If `/dev/video0` is listed, your camera is detected and ready.

---

## 5. Step 4: Install System Dependencies on the Pi

Run the following commands on the Raspberry Pi terminal:

```bash
# 1. Update package repositories
sudo apt update && sudo apt upgrade -y

# 2. Install barcode and imaging system libraries
sudo apt install -y python3-pip python3-venv libzbar0 zbar-tools fswebcam python3-rpi.gpio

# 3. Create project working directory
mkdir -p ~/shelfsense-client
cd ~/shelfsense-client

# 4. Set up an isolated Python virtual environment (allowing system packages)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# 5. Install Python client dependencies
pip install requests pillow opencv-python-headless
```

---

## 6. Step 5: Connecting to the Cloud Gateway

The Raspberry Pi needs to know the URL where the ShelfSense Gateway server is running. Depending on your environment, pick one of the options below:

### Option A: Local Network / Presentation Demo (Easiest)
If your Gateway server is running on your laptop/PC on the same Wi-Fi as the Pi:
1. Find your laptop's local IP address:
   * **Windows:** Open Command Prompt -> `ipconfig` (look for *IPv4 Address*, e.g., `192.168.1.45`).
   * **Mac/Linux:** `ifconfig` or `ip a` (e.g., `192.168.1.45`).
2. Gateway URL: `http://192.168.1.45:8000`

### Option B: Cloud Deployment (AWS EC2 / VPS / Railway)
If your Gateway is deployed on a cloud virtual machine:
* Gateway URL: `http://<EC2_PUBLIC_IP>:8000` or `https://gateway.yourdomain.com`

### Option C: Free Instant Public URL (ngrok Tunnel)
To securely expose your local Gateway to the internet so the Pi can reach it from any cellular hotspot or network:
1. On your PC running the Gateway:
   ```bash
   ngrok http 8000
   ```
2. Copy the public forwarding URL (e.g., `https://abc-123.ngrok-free.app`).
3. Gateway URL: `https://abc-123.ngrok-free.app`

### Test Connectivity from the Pi:
Run this on your Raspberry Pi terminal to confirm the connection:
```bash
curl -X GET http://<YOUR_GATEWAY_URL>/api/v1/system/status
```
You should get a JSON response: `{"gatewayOnline":true,"status":"healthy",...}`.

---

## 7. Step 6: Pushing Images Directly into the Scan Queue

We have provided two dedicated methods to push images into the queue:

### Method 1: The Direct Pusher Script (`pi_push_scan.py`) — Recommended for Demos
This script captures a photo and immediately pushes it into the Gateway's multi-modal OCR queue.

1. Copy `scripts/pi_push_scan.py` to your Raspberry Pi:
   ```bash
   # From your PC:
   scp scripts/pi_push_scan.py pi@shelfsense-pi.local:~/shelfsense-client/
   ```
2. On the Pi, run:
   ```bash
   cd ~/shelfsense-client
   source venv/bin/activate
   ```

#### A. Trigger a Single Test Scan:
```bash
python pi_push_scan.py --gateway http://192.168.1.45:8000 --device-id pi-01
```
*Output will display:*
```text
[*] Capturing photo...
[+] Captured via rpicam-still (or fswebcam)
[*] Uploading /tmp/shelfsense_scan.jpg (142.4 KB) to http://192.168.1.45:8000/api/v1/scans/from-image...
============================================================
[SUCCESS] IMAGE SUCCESSFULLY PLACED IN SCAN QUEUE!
 > Scan ID:        #14
 > Product Name:   Organic Whole Milk
 > Expiry Date:    2026-11-28
 > Confidence:     94.5%
 > Queue Status:   PENDING
 > View in Admin:  http://192.168.1.45:8000/admin
============================================================
```

#### B. Continuous Scanning Loop (e.g., Every 10 Seconds):
```bash
python pi_push_scan.py --gateway http://192.168.1.45:8000 --device-id pi-01 --loop --interval 10
```

#### C. Physical Hardware Push Button Mode:
If you wired a tactile button to GPIO 17:
```bash
python pi_push_scan.py --gateway http://192.168.1.45:8000 --device-id pi-01 --gpio-button 17
```
*Every time you physically press the button on the breadboard/case, it snaps a picture and injects it into the cloud queue!*

---

### Method 2: The Production Background Daemon (`app/raspberry_pi_client.py`)
If you want the full production client with **offline queueing** (saves photos locally to disk when offline and flushes them automatically when Wi-Fi reconnects):

```bash
python app/raspberry_pi_client.py --gateway http://192.168.1.45:8000 --device-id pi-01 --interval 5
```

---

## 8. Step 7: Showing Reviewers on the Admin Dashboard

Now that the Raspberry Pi is pushing scans:

1. Open your browser to:
   ```
   http://<YOUR_GATEWAY_URL>/admin
   ```
2. Sign in with the presentation credentials:
   * **Username:** `admin`
   * **Password:** `admin123`
3. **What Reviewers Will See Live:**
   * Under **"Pending Queue"**, the image just captured by the Raspberry Pi appears in real time!
   * The camera thumbnail shows the exact packaging captured.
   * AI OCR displays the extracted product name (e.g., `Organic Whole Milk`), barcode, and extracted expiry date.
   * The **OCR Confidence percentage** and device badge (`pi-01`) confirm hardware origin.
   * Reviewers can click **"View Details"** to see full vision tokens or click **"Approve"** to accept the product into active store inventory.

---

## 9. Step 8: Auto-Start on Boot (Demo-Ready Systemd Service)

To make your hardware prototype automatically start running as soon as you plug it into power (so you don't need any laptop or terminal during live demonstrations):

1. Create a systemd service file on the Raspberry Pi:
   ```bash
   sudo nano /etc/systemd/system/shelfsense-hardware.service
   ```
2. Paste the following configuration (replace `192.168.1.45:8000` with your gateway address):
   ```ini
   [Unit]
   Description=ShelfSense Hardware Camera Client
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/shelfsense-client
   ExecStart=/home/pi/shelfsense-client/venv/bin/python /home/pi/shelfsense-client/pi_push_scan.py --gateway http://192.168.1.45:8000 --device-id pi-01 --gpio-button 17
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable shelfsense-hardware.service
   sudo systemctl start shelfsense-hardware.service
   ```
4. Now, the Raspberry Pi will automatically boot, connect to Wi-Fi, and monitor for button presses or scans without any user interaction!

---

## 10. Hardware Troubleshooting Cheatsheet

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **`Camera not detected`** | Ribbon cable inverted or loose. | Ensure the blue plastic tab faces the USB ports on Pi 4. Reseat ribbon with power off. If using USB webcam, run `ls /dev/video*`. |
| **`Connection refused (errno 111)`** | Gateway server is not running or blocked by firewall. | Make sure `uvicorn app.main:app --host 0.0.0.0 --port 8000` is running on the host machine. Ensure host Windows firewall allows incoming connections on port 8000. |
| **`Cannot resolve host`** | Pi is on a different Wi-Fi network. | Connect both the laptop and Pi to the same mobile hotspot or Wi-Fi router, or use an `ngrok` HTTPS tunnel. |
| **`Image too dark / blurry`** | Insufficient ambient lighting or fixed-focus lens. | Provide adequate lighting over the product barcode/expiry date, or adjust distance (standard Pi cam fixed focus is ~15-20 cm). |
