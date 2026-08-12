# ShelfSense Raspberry Pi Setup Guide

This guide provides step-by-step instructions to configure, run, and automate the ShelfSense scan client on a Raspberry Pi. 

The client captures images from a camera, performs local barcode detection and OCR extraction, uploads the images to the Gateway, and registers the scanned item. It also features a resident background queue to store scans during power/network loss and auto-flush them once online.

---

## 1. Hardware Requirements & Setup

1. **Raspberry Pi**: Pi 3, 4, or 5 (running Raspberry Pi OS, preferably 64-bit Bookworm).
2. **Camera**: 
   - **USB Webcam**: Plug-and-play webcam (e.g., Logitech C270). This is the most compatible option with OpenCV's capture interface.
   - **Pi Camera Module**: Official Camera Module (V1, V2, or V3).
3. **Power Supply & MicroSD Card** (16GB+ recommended).
4. **Network**: Ethernet or Wi-Fi connectivity to access the ShelfSense Gateway server.

---

## 2. Install System Dependencies

Before configuration, install the required packages on your Raspberry Pi. Open a terminal (or connect via SSH) and run:

```bash
# Update package repositories
sudo apt update && sudo apt upgrade -y

# Install Tesseract OCR (for text/date extraction)
sudo apt install -y tesseract-ocr

# Install ZBar (for barcode decoding)
sudo apt install -y libzbar0 zbar-tools

# Install OpenCV system dependencies and python tools
sudo apt install -y python3-pip python3-venv python3-opencv

# (Optional) Install fswebcam to verify your camera feed quickly
sudo apt install -y fswebcam
```

### Verify Your Camera Connected/Functioning
Ensure your camera is detected by running:
```bash
ls /dev/video*
```
You should see `/dev/video0`. To verify a webcam captures properly, test writing a file:
```bash
fswebcam --no-banner -r 640x480 /tmp/camera_test.jpg
```
Open `/tmp/camera_test.jpg` (or copy it off the Pi) to verify the image feed.

---

## 3. Directory Layout on the Pi

Create a directory for the client code and database files:

```bash
mkdir -p ~/shelfsense-client/app/services
cd ~/shelfsense-client
```

You must transfer/copy these files from the Gateway codebase onto the Pi at their corresponding paths:
*   `app/raspberry_pi_client.py` -> `/home/pi/shelfsense-client/app/raspberry_pi_client.py`
*   `app/check_pi_dependencies.py` -> `/home/pi/shelfsense-client/app/check_pi_dependencies.py`
*   `app/services/ocr_service.py` -> `/home/pi/shelfsense-client/app/services/ocr_service.py`

*Note: If the user on your Pi is not `pi`, replace `/home/pi/` with your actual home directory path.*

---

## 4. Python Environment & Dependency Checks

Raspberry Pi OS Bookworm utilizes PEP 668 PEP-managed environments. It is recommended to configure a Python virtual environment (`venv`) to run the client. 

Include the system's site-packages when creating the virtual environment so the Python process can reuse the precompiled Debian version of OpenCV (`cv2`) which avoids long compilation times:

```bash
# Create a venv with access to system packages (like cv2)
python3 -m venv --system-site-packages venv

# Activate the virtual environment
source venv/bin/activate

# Install pure-Python dependencies
pip install requests pytesseract pyzbar pillow
```

### Run Dependency Validation
Verify the dependencies are properly installed by running the check script:

```bash
python -m app.check_pi_dependencies
```

If successful, you will see output confirming:
*   `tesseract` and `zbarimg` binaries found.
*   `cv2`, `pytesseract`, `pyzbar`, `PIL`, and `requests` python packages found.

---

## 5. Running the Client Manually

To test the client interface, launch it from the CLI with the core arguments:

```bash
python -m app.raspberry_pi_client \
  --gateway http://<GATEWAY_IP_OR_HOSTNAME>:8000 \
  --device-id pi-kitchen-01 \
  --interval 30
```

### Argument Explanations:
*   `--gateway`: The address under which the FastAPI Gateway is running.
*   `--device-id`: A unique string identifier for this scanner.
*   `--interval`: Cycle wait time between camera scans (in seconds).
*   `--pending-dir`: (Optional) Folder where temporary backup files are stored during network loss (defaults to `/var/lib/raspi_client/pending`).
*   `--image-quality`: (Optional) Slider between 1 and 100 for JPEG compression quality (defaults to `75` to conserve network bandwidth).

Press `Ctrl+C` to terminate the manual run.

---

## 6. Run Continuously using systemd (Production Deploy)

To ensure the client runs automatically when the Pi boots up and restarts if crashes occur, set it up as a systemd service.

### Step 1: Create the systemd Service File

Create write access under `/etc/systemd/system/shelfsense-client.service`:

```bash
sudo nano /etc/systemd/system/shelfsense-client.service
```

Paste the following configurations into the file:

```ini
[Unit]
Description=ShelfSense Gateway Scan Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/shelfsense-client
ExecStart=/home/pi/shelfsense-client/venv/bin/python -m app.raspberry_pi_client \
    --gateway http://your-gateway-ip:8000 \
    --device-id pi-kitchen-01 \
    --interval 20 \
    --image-quality 75
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

*(Verify paths and names match your Pi's configuration: change `User=pi` and `/home/pi/` if your Pi runs under a different username, and replace `your-gateway-ip` with the actual IP address or domain hostname of the Gateway server).*

### Step 2: Enable and Start the Service

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable the service on system startup
sudo systemctl enable shelfsense-client.service

# Start the service immediately
sudo systemctl start shelfsense-client.service
```

### Step 3: Monitoring the Client Logs

Watch the startup logs and runtime outputs:

```bash
sudo journalctl -u shelfsense-client.service -f
```

You will see logs such as:
```text
2026-08-11 23:10:00 [INFO] Background workers started: flush every 10s, health every 30s
2026-08-11 23:10:00 [INFO] Capturing image to /tmp/raspi_capture.jpg
2026-08-11 23:10:02 [INFO] Captured image with OpenCV
2026-08-11 23:10:03 [INFO] Detected barcodes: ['8901058002476']
2026-08-11 23:10:04 [INFO] OCR extracted name=Tomato Sauce expiry=2026-09-01 confidence=0.91
2026-08-11 23:10:04 [INFO] Uploading image /tmp/raspi_capture.jpg to http://192.168.1.50:8000/api/v1/images/upload
2026-08-11 23:10:05 [INFO] Upload successful: 200
2026-08-11 23:10:05 [INFO] Sending scan JSON to http://192.168.1.50:8000/api/v1/scans
2026-08-11 23:10:06 [INFO] Scan JSON sent, status 200
```
