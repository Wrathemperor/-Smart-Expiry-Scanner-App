import os
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.core.config import settings
from app.core.enums import ScanStatus
from app.models.pending_scan import PendingScan
from app.models.products import Product
from app.repositories.pending_scan_repository import PendingScanRepository
from app.repositories.product_repository import ProductRepository
from app.services.image_service import ImageService
from app.services.scan_service import ScanService
from app.services.ocr_service import analyze_image

router = APIRouter(tags=["Admin Management Dashboard"])

def generate_admin_token(username: str) -> str:
    msg = f"{username}:{settings.SECRET_KEY}:{datetime.utcnow().strftime('%Y-%m-%d')}"
    return hashlib.sha256(msg.encode()).hexdigest()

def verify_admin_auth(request: Request) -> bool:
    token = request.headers.get("X-Admin-Token") or request.cookies.get("admin_token")
    expected = generate_admin_token(settings.ADMIN_USERNAME)
    return token == expected

@router.post("/api/v1/admin/login")
def admin_login(payload: dict, response: Response):
    username = payload.get("username", "")
    password = payload.get("password", "")

    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        token = generate_admin_token(username)
        response.set_cookie(
            key="admin_token",
            value=token,
            httponly=False,
            max_age=86400,
            samesite="lax"
        )
        return {
            "success": True,
            "token": token,
            "username": username,
            "message": "Authentication successful"
        }
    raise HTTPException(status_code=401, detail="Invalid admin credentials")

@router.get("/api/v1/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    all_scans = db.query(PendingScan).all()
    all_products = db.query(Product).all()

    pending_count = sum(1 for s in all_scans if s.status == ScanStatus.PENDING)
    approved_count = len(all_products) + sum(1 for s in all_scans if s.status == ScanStatus.APPROVED)
    rejected_count = sum(1 for s in all_scans if s.status == ScanStatus.REJECTED)
    total_scans = len(all_scans)

    avg_conf = 0.0
    if all_scans:
        confidences = [s.ocr_confidence for s in all_scans if s.ocr_confidence is not None]
        if confidences:
            avg_conf = round(sum(confidences) / len(confidences), 1)

    return {
        "total_scans": total_scans,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "avg_confidence": avg_conf,
        "active_devices": ["pi-01", "pi-02", "android-mobile"],
        "gateway_status": "ONLINE"
    }

@router.get("/api/v1/admin/scans")
def get_admin_scans(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(PendingScan).order_by(PendingScan.scanned_at.desc())
    if status and status.upper() in [s.value for s in ScanStatus]:
        query = query.filter(PendingScan.status == ScanStatus(status.upper()))
    
    scans = query.all()
    result = []
    base_url = str(request.base_url).rstrip("/")

    for s in scans:
        img_url = ImageService.get_image_url(request, s.image_id) if s.image_id else None
        result.append({
            "id": s.id,
            "image_id": s.image_id,
            "image_url": img_url,
            "name": s.name or "Unknown Item",
            "barcode": s.barcode or "N/A",
            "category": s.category or "General",
            "expiry_date": s.expiry_date.strftime("%Y-%m-%d") if s.expiry_date else "Not Detected",
            "location": s.location or "Pantry",
            "ocr_confidence": round((s.ocr_confidence or 0.0) * 100, 1) if (s.ocr_confidence or 0.0) <= 1.0 else round(s.ocr_confidence or 0.0, 1),
            "ocr_text": s.ocr_text or "",
            "pi_id": s.pi_id or "pi-client",
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "scanned_at": s.scanned_at.strftime("%Y-%m-%d %H:%M:%S") if s.scanned_at else ""
        })
    return result

@router.post("/api/v1/admin/scans/{scan_id}/approve")
def admin_approve_scan(scan_id: int, db: Session = Depends(get_db)):
    result = ScanService.approve_scan(db, scan_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "message": f"Scan #{scan_id} approved into active inventory"}

@router.post("/api/v1/admin/scans/{scan_id}/reject")
def admin_reject_scan(scan_id: int, db: Session = Depends(get_db)):
    result = ScanService.reject_scan(db, scan_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "message": f"Scan #{scan_id} rejected and removed from review"}

@router.post("/api/v1/admin/upload-test")
def admin_upload_test_scan(
    request: Request,
    image: UploadFile = File(...),
    device_id: str = Form("admin-dashboard-demo"),
    db: Session = Depends(get_db)
):
    """Allows uploading a test image directly from the dashboard to demo live OCR and queue ingestion to reviewers."""
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    saved_img = ImageService.save_image(request, image)
    image_id = saved_img["image_id"]
    local_path = saved_img["local_path"]

    # Run OCR analysis
    ocr_result = {}
    try:
        ocr_result = analyze_image(local_path)
    except Exception as e:
        ocr_result = {
            "name": "Scanned Product",
            "category": "Pantry",
            "expiry_date": None,
            "ocr_confidence": 0.85,
            "raw_text": f"Processed via Gateway: {e}"
        }

    expiry_dt = None
    if ocr_result.get("expiry_date"):
        try:
            expiry_dt = datetime.fromisoformat(ocr_result["expiry_date"])
        except Exception:
            pass

    pending = PendingScan(
        name=ocr_result.get("name") or "Test Food Item",
        category=ocr_result.get("category") or "Pantry",
        barcode=ocr_result.get("barcode") or "TEST-890123",
        expiry_date=expiry_dt,
        location="Kitchen Shelf A",
        image_id=image_id,
        ocr_confidence=ocr_result.get("ocr_confidence", 0.90),
        ocr_text=ocr_result.get("raw_text") or "DEMO TEST SCAN",
        pi_id=device_id,
        status=ScanStatus.PENDING,
        scanned_at=datetime.utcnow()
    )
    created = PendingScanRepository.create(db, pending)

    return {
        "success": True,
        "scan_id": created.id,
        "image_url": saved_img["image_url"],
        "product_name": created.name,
        "status": created.status.value
    }

@router.get("/admin", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard_page():
    return HTMLResponse(content=DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ShelfSense — Admin Image & Scan Management Dashboard</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Phosphor Icons -->
  <script src="https://unpkg.com/@phosphor-icons/web"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              50: '#ecfdf5',
              500: '#10b981',
              600: '#059669',
              700: '#047857',
            },
            amber: {
              400: '#fbbf24',
              500: '#f59e0b',
            }
          }
        }
      }
    }
  </script>
  <style>
    .glass {
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .laser-glow {
      box-shadow: 0 0 20px -3px rgba(16, 185, 129, 0.35);
    }
  </style>
</head>
<body class="min-h-full font-sans antialiased selection:bg-emerald-500 selection:text-white">

  <!-- AUTH MODAL (Shown if not logged in) -->
  <div id="login-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 transition-all">
    <div class="glass w-full max-w-md rounded-2xl p-8 border border-slate-800 shadow-2xl relative overflow-hidden">
      <div class="absolute -top-24 -right-24 w-48 h-48 bg-emerald-500/20 rounded-full blur-3xl pointer-events-none"></div>
      
      <div class="flex items-center gap-3 mb-6">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center text-white text-2xl shadow-lg shadow-emerald-500/20">
          <i class="ph-bold ph-scan"></i>
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            ShelfSense <span class="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">ADMIN</span>
          </h1>
          <p class="text-xs text-slate-400">Reviewer & Hardware Gateway Inspector</p>
        </div>
      </div>

      <div class="mb-5 bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 text-xs text-slate-400">
        <div class="flex items-center gap-2 text-emerald-400 font-semibold mb-1">
          <i class="ph-bold ph-info"></i> Presentation Credentials
        </div>
        Username: <code class="text-white bg-slate-800 px-1.5 py-0.5 rounded">admin</code> &nbsp;|&nbsp;
        Password: <code class="text-white bg-slate-800 px-1.5 py-0.5 rounded">admin123</code>
      </div>

      <form id="login-form" onsubmit="handleLogin(event)" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5">Username</label>
          <input id="login-username" type="text" value="admin" required
            class="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors">
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5">Password</label>
          <input id="login-password" type="password" value="admin123" required
            class="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors">
        </div>

        <div id="login-error" class="hidden text-xs text-rose-400 font-medium bg-rose-950/40 border border-rose-800/50 p-2.5 rounded-lg flex items-center gap-2">
          <i class="ph-bold ph-warning-circle"></i> <span id="login-error-text">Invalid credentials</span>
        </div>

        <button type="submit"
          class="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-medium py-2.5 px-4 rounded-xl shadow-lg shadow-emerald-500/25 transition-all flex items-center justify-center gap-2 text-sm mt-2">
          <i class="ph-bold ph-sign-in"></i> Sign In to Dashboard
        </button>
      </form>
    </div>
  </div>

  <!-- MAIN DASHBOARD CONTENT -->
  <div id="app" class="min-h-screen flex flex-col">
    <!-- TOP NAVIGATION -->
    <header class="glass sticky top-0 z-40 border-b border-slate-800">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        <!-- Brand -->
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-white text-xl shadow-md shadow-emerald-500/20">
            <i class="ph-bold ph-scan"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-base tracking-tight text-white">ShelfSense</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">GATEWAY</span>
            </div>
            <p class="text-[11px] text-slate-400 hidden sm:block">Real-time Vision OCR & Scan Queue Monitor</p>
          </div>
        </div>

        <!-- System Badges & Controls -->
        <div class="flex items-center gap-3">
          <!-- Gateway Live Status -->
          <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800 text-xs">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span class="text-slate-300 font-mono text-[11px]">GATEWAY LIVE</span>
          </div>

          <!-- Quick Upload Test Button -->
          <button onclick="openUploadModal()"
            class="bg-emerald-600/90 hover:bg-emerald-500 text-white text-xs font-medium px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow transition-all">
            <i class="ph-bold ph-plus-circle text-sm"></i> Upload Test Scan
          </button>

          <!-- Auto-Refresh Toggle -->
          <button id="refresh-btn" onclick="fetchData()"
            class="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm transition-colors" title="Refresh Live Data">
            <i class="ph-bold ph-arrows-clockwise" id="refresh-icon"></i>
          </button>

          <!-- Logout -->
          <button onclick="handleLogout()"
            class="p-2 rounded-lg bg-slate-800 hover:bg-rose-900/40 text-slate-400 hover:text-rose-300 text-sm transition-colors" title="Sign Out">
            <i class="ph-bold ph-sign-out"></i>
          </button>
        </div>

      </div>
    </header>

    <!-- CONTENT WRAPPER -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      <!-- HERO METRICS -->
      <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <!-- Metric 1: Total Scans -->
        <div class="glass rounded-xl p-5 border border-slate-800 hover:border-slate-700 transition-all">
          <div class="flex items-center justify-between text-slate-400 mb-2">
            <span class="text-xs font-semibold tracking-wider uppercase">Total Uploads</span>
            <i class="ph-bold ph-image text-emerald-400 text-lg"></i>
          </div>
          <div id="stat-total" class="text-2xl sm:text-3xl font-extrabold text-white">0</div>
          <div class="text-[11px] text-slate-400 mt-1">Processed by Gateway</div>
        </div>

        <!-- Metric 2: Pending Reviews -->
        <div class="glass rounded-xl p-5 border border-slate-800 hover:border-amber-500/40 transition-all">
          <div class="flex items-center justify-between text-slate-400 mb-2">
            <span class="text-xs font-semibold tracking-wider uppercase">Pending Queue</span>
            <i class="ph-bold ph-clock text-amber-400 text-lg"></i>
          </div>
          <div id="stat-pending" class="text-2xl sm:text-3xl font-extrabold text-amber-400">0</div>
          <div class="text-[11px] text-slate-400 mt-1">Awaiting Reviewer Approval</div>
        </div>

        <!-- Metric 3: Approved Inventory -->
        <div class="glass rounded-xl p-5 border border-slate-800 hover:border-emerald-500/40 transition-all">
          <div class="flex items-center justify-between text-slate-400 mb-2">
            <span class="text-xs font-semibold tracking-wider uppercase">Approved Items</span>
            <i class="ph-bold ph-check-circle text-emerald-400 text-lg"></i>
          </div>
          <div id="stat-approved" class="text-2xl sm:text-3xl font-extrabold text-emerald-400">0</div>
          <div class="text-[11px] text-slate-400 mt-1">In Active Store Inventory</div>
        </div>

        <!-- Metric 4: AI OCR Confidence -->
        <div class="glass rounded-xl p-5 border border-slate-800 hover:border-teal-500/40 transition-all">
          <div class="flex items-center justify-between text-slate-400 mb-2">
            <span class="text-xs font-semibold tracking-wider uppercase">AI OCR Engine</span>
            <i class="ph-bold ph-brain text-teal-400 text-lg"></i>
          </div>
          <div id="stat-confidence" class="text-2xl sm:text-3xl font-extrabold text-teal-300">92%</div>
          <div class="text-[11px] text-slate-400 mt-1">Gemini Vision / Bedrock</div>
        </div>
      </section>

      <!-- FILTER & SEARCH BAR -->
      <section class="glass rounded-xl p-4 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        
        <!-- Filter Tabs -->
        <div class="flex items-center p-1 rounded-lg bg-slate-900 border border-slate-800 w-full md:w-auto overflow-x-auto text-xs">
          <button onclick="setFilter('ALL')" id="tab-ALL" class="tab-btn px-3.5 py-1.5 rounded-md font-medium transition-all bg-emerald-500 text-white shadow">
            All Scans (<span id="count-all">0</span>)
          </button>
          <button onclick="setFilter('PENDING')" id="tab-PENDING" class="tab-btn px-3.5 py-1.5 rounded-md font-medium text-slate-400 hover:text-white transition-all">
            Pending Queue (<span id="count-pending">0</span>)
          </button>
          <button onclick="setFilter('APPROVED')" id="tab-APPROVED" class="tab-btn px-3.5 py-1.5 rounded-md font-medium text-slate-400 hover:text-white transition-all">
            Approved (<span id="count-approved">0</span>)
          </button>
          <button onclick="setFilter('REJECTED')" id="tab-REJECTED" class="tab-btn px-3.5 py-1.5 rounded-md font-medium text-slate-400 hover:text-white transition-all">
            Rejected (<span id="count-rejected">0</span>)
          </button>
        </div>

        <!-- Search Bar -->
        <div class="relative w-full md:w-80">
          <i class="ph-bold ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm"></i>
          <input id="search-input" oninput="renderScans()" type="text" placeholder="Search by name, barcode, device..."
            class="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors">
        </div>

      </section>

      <!-- SCAN & IMAGE GALLERY GRID -->
      <section>
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <i class="ph-bold ph-images text-emerald-400"></i> User & Edge Uploaded Images
            </h2>
            <p class="text-xs text-slate-400">Live feed of product packaging photos received from Raspberry Pi and mobile clients</p>
          </div>
          <div class="text-xs text-slate-400 font-mono">
            Showing: <span id="filtered-count" class="text-white font-bold">0</span> items
          </div>
        </div>

        <!-- Cards Container -->
        <div id="gallery-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <!-- Dynamic cards injected here -->
        </div>

        <!-- Empty State -->
        <div id="empty-state" class="hidden glass rounded-2xl p-12 text-center border border-slate-800">
          <div class="w-16 h-16 mx-auto rounded-full bg-slate-900 flex items-center justify-center text-slate-500 text-2xl mb-4">
            <i class="ph-bold ph-camera-slash"></i>
          </div>
          <h3 class="text-base font-semibold text-white">No scans match your criteria</h3>
          <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto">Upload a test photo using the button above or initiate a scan from the connected Raspberry Pi.</p>
        </div>
      </section>

    </main>
  </div>

  <!-- INSPECTION & DETAIL MODAL -->
  <div id="inspect-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 transition-all">
    <div class="glass w-full max-w-3xl rounded-2xl p-6 border border-slate-800 shadow-2xl relative max-h-[90vh] overflow-y-auto">
      <button onclick="closeInspectModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-lg bg-slate-900/60 transition-colors">
        <i class="ph-bold ph-x text-base"></i>
      </button>

      <div class="flex items-center gap-2 mb-4">
        <span id="modal-status-badge" class="px-2.5 py-0.5 rounded text-xs font-semibold tracking-wider uppercase"></span>
        <span class="text-xs text-slate-400 font-mono" id="modal-scan-id"></span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Image Preview -->
        <div class="relative bg-slate-900/80 rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center min-h-[260px]">
          <img id="modal-image" src="" alt="Scan preview" class="w-full h-auto object-contain max-h-[360px] rounded-lg">
          <a id="modal-image-link" href="#" target="_blank" class="absolute bottom-2 right-2 text-[11px] bg-slate-900/90 hover:bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-700 flex items-center gap-1">
            <i class="ph-bold ph-arrow-square-out"></i> Open Full Image
          </a>
        </div>

        <!-- Metadata & OCR Fields -->
        <div class="space-y-4">
          <div>
            <h3 id="modal-product-name" class="text-xl font-bold text-white"></h3>
            <p id="modal-category" class="text-xs text-emerald-400 font-medium"></p>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">Barcode</span>
              <span id="modal-barcode" class="font-mono text-white text-xs"></span>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">Expiry Date</span>
              <span id="modal-expiry" class="font-bold text-amber-400 text-xs"></span>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">OCR Confidence</span>
              <span id="modal-conf" class="font-semibold text-emerald-400 text-xs"></span>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">Edge Device ID</span>
              <span id="modal-device" class="font-mono text-slate-300 text-xs"></span>
            </div>
          </div>

          <!-- Raw OCR Dump -->
          <div>
            <label class="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Extracted OCR Text / Vision Tokens</label>
            <pre id="modal-ocr-text" class="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-300 max-h-32 overflow-y-auto whitespace-pre-wrap"></pre>
          </div>

          <!-- Action Buttons in Modal -->
          <div id="modal-actions" class="pt-2 flex gap-3">
            <button id="modal-approve-btn" onclick="" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all shadow-lg shadow-emerald-600/20">
              <i class="ph-bold ph-check"></i> Approve Scan
            </button>
            <button id="modal-reject-btn" onclick="" class="px-4 bg-slate-800 hover:bg-rose-950/60 text-rose-400 hover:text-rose-300 border border-slate-700 hover:border-rose-800 py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all">
              <i class="ph-bold ph-trash"></i> Reject
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- UPLOAD TEST SCAN MODAL -->
  <div id="upload-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 transition-all">
    <div class="glass w-full max-w-md rounded-2xl p-6 border border-slate-800 shadow-2xl relative">
      <button onclick="closeUploadModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-lg bg-slate-900/60 transition-colors">
        <i class="ph-bold ph-x text-base"></i>
      </button>

      <div class="flex items-center gap-2 mb-4">
        <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-lg">
          <i class="ph-bold ph-upload-simple"></i>
        </div>
        <div>
          <h3 class="text-base font-bold text-white">Upload Test Scan</h3>
          <p class="text-xs text-slate-400">Simulate a client/camera image push</p>
        </div>
      </div>

      <form id="upload-form" onsubmit="handleUploadTest(event)" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5">Select Food Packaging Image</label>
          <input id="test-image-input" type="file" accept="image/*" required
            class="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-emerald-600 file:text-white hover:file:bg-emerald-500">
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5">Device Identifier</label>
          <input id="test-device-id" type="text" value="pi-camera-01" required
            class="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
        </div>

        <div id="upload-spinner" class="hidden text-xs text-emerald-400 flex items-center gap-2">
          <i class="ph-bold ph-spinner animate-spin"></i> Running Vision OCR and queueing scan...
        </div>

        <button type="submit" id="upload-submit-btn"
          class="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-medium py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all">
          <i class="ph-bold ph-paper-plane-right"></i> Process & Put into Queue
        </button>
      </form>
    </div>
  </div>

  <!-- DASHBOARD JAVASCRIPT LOGIC -->
  <script>
    let allScans = [];
    let currentFilter = 'ALL';
    let adminToken = localStorage.getItem('shelf_admin_token') || '';

    // Check if token in cookie or storage
    function checkAuth() {
      const modal = document.getElementById('login-modal');
      if (!adminToken) {
        modal.classList.remove('hidden');
      } else {
        modal.classList.add('hidden');
        fetchData();
        // Start live polling every 6 seconds
        setInterval(fetchData, 6000);
      }
    }

    async function handleLogin(e) {
      e.preventDefault();
      const u = document.getElementById('login-username').value;
      const p = document.getElementById('login-password').value;
      const errBox = document.getElementById('login-error');
      
      try {
        const res = await fetch('/api/v1/admin/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({username: u, password: p})
        });
        const data = await res.json();
        if (res.ok && data.success) {
          adminToken = data.token;
          localStorage.setItem('shelf_admin_token', adminToken);
          document.getElementById('login-modal').classList.add('hidden');
          fetchData();
          setInterval(fetchData, 6000);
        } else {
          errBox.classList.remove('hidden');
          document.getElementById('login-error-text').innerText = data.detail || 'Authentication failed';
        }
      } catch (err) {
        errBox.classList.remove('hidden');
        document.getElementById('login-error-text').innerText = 'Network error during login';
      }
    }

    function handleLogout() {
      localStorage.removeItem('shelf_admin_token');
      adminToken = '';
      document.getElementById('login-modal').classList.remove('hidden');
    }

    async function fetchData() {
      const refreshIcon = document.getElementById('refresh-icon');
      if (refreshIcon) refreshIcon.classList.add('animate-spin');

      try {
        // Fetch stats
        const statsRes = await fetch('/api/v1/admin/stats');
        if (statsRes.ok) {
          const stats = await statsRes.json();
          document.getElementById('stat-total').innerText = stats.total_scans;
          document.getElementById('stat-pending').innerText = stats.pending_count;
          document.getElementById('stat-approved').innerText = stats.approved_count;
          if (stats.avg_confidence) {
            document.getElementById('stat-confidence').innerText = stats.avg_confidence + '%';
          }
        }

        // Fetch scans
        const scansRes = await fetch('/api/v1/admin/scans');
        if (scansRes.ok) {
          allScans = await scansRes.json();
          updateTabCounts();
          renderScans();
        }
      } catch (e) {
        console.error("Failed to load dashboard data:", e);
      } finally {
        if (refreshIcon) refreshIcon.classList.remove('animate-spin');
      }
    }

    function updateTabCounts() {
      const total = allScans.length;
      const pending = allScans.filter(s => s.status === 'PENDING').length;
      const approved = allScans.filter(s => s.status === 'APPROVED').length;
      const rejected = allScans.filter(s => s.status === 'REJECTED').length;

      document.getElementById('count-all').innerText = total;
      document.getElementById('count-pending').innerText = pending;
      document.getElementById('count-approved').innerText = approved;
      document.getElementById('count-rejected').innerText = rejected;
    }

    function setFilter(filter) {
      currentFilter = filter;
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-emerald-500', 'text-white', 'shadow');
        btn.classList.add('text-slate-400');
      });
      const activeBtn = document.getElementById('tab-' + filter);
      if (activeBtn) {
        activeBtn.classList.add('bg-emerald-500', 'text-white', 'shadow');
        activeBtn.classList.remove('text-slate-400');
      }
      renderScans();
    }

    function renderScans() {
      const search = (document.getElementById('search-input').value || '').toLowerCase();
      const container = document.getElementById('gallery-container');
      const emptyState = document.getElementById('empty-state');

      let filtered = allScans.filter(s => {
        const matchesFilter = (currentFilter === 'ALL') || (s.status === currentFilter);
        const matchesSearch = !search ||
          (s.name && s.name.toLowerCase().includes(search)) ||
          (s.barcode && s.barcode.toLowerCase().includes(search)) ||
          (s.category && s.category.toLowerCase().includes(search)) ||
          (s.pi_id && s.pi_id.toLowerCase().includes(search));
        return matchesFilter && matchesSearch;
      });

      document.getElementById('filtered-count').innerText = filtered.length;

      if (filtered.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
      }

      emptyState.classList.add('hidden');
      container.innerHTML = filtered.map(scan => {
        const isPending = scan.status === 'PENDING';
        const isApproved = scan.status === 'APPROVED';

        let badgeBg = isPending ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                      isApproved ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      'bg-rose-500/10 text-rose-400 border-rose-500/20';

        let imgHtml = scan.image_url ?
          `<img src="${scan.image_url}" alt="${scan.name}" class="w-full h-44 object-cover group-hover:scale-105 transition-transform duration-300" onerror="this.src='https://placehold.co/400x300/1e293b/94a3b8?text=Image+Preserved'">` :
          `<div class="w-full h-44 bg-slate-900 flex flex-col items-center justify-center text-slate-500 gap-2">
             <i class="ph-bold ph-image-broken text-3xl"></i>
             <span class="text-[11px] font-mono">No Image</span>
           </div>`;

        return `
          <div class="glass group rounded-2xl overflow-hidden border border-slate-800 hover:border-slate-700 transition-all flex flex-col">
            <!-- Card Image -->
            <div class="relative overflow-hidden cursor-pointer bg-slate-900" onclick="openInspectModal(${scan.id})">
              ${imgHtml}
              <!-- Status Badge -->
              <span class="absolute top-2.5 left-2.5 text-[10px] font-bold px-2 py-0.5 rounded-md border ${badgeBg} backdrop-blur-md uppercase tracking-wider">
                ${scan.status}
              </span>
              <!-- Confidence Tag -->
              <span class="absolute top-2.5 right-2.5 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-slate-950/80 text-emerald-400 border border-slate-800 backdrop-blur-md">
                ${scan.ocr_confidence}% OCR
              </span>
            </div>

            <!-- Card Content -->
            <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
              <div>
                <div class="flex items-center justify-between gap-2">
                  <span class="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">${scan.category}</span>
                  <span class="text-[10px] font-mono text-slate-500">${scan.pi_id}</span>
                </div>
                <h4 class="text-sm font-bold text-white line-clamp-1 mt-0.5 cursor-pointer hover:text-emerald-400 transition-colors" onclick="openInspectModal(${scan.id})">
                  ${scan.name}
                </h4>
              </div>

              <!-- Metadata info -->
              <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80 text-[11px] space-y-1">
                <div class="flex items-center justify-between text-slate-400">
                  <span>Expiry:</span>
                  <span class="font-bold text-amber-400">${scan.expiry_date}</span>
                </div>
                <div class="flex items-center justify-between text-slate-400">
                  <span>Barcode:</span>
                  <span class="font-mono text-slate-300">${scan.barcode}</span>
                </div>
              </div>

              <!-- Actions -->
              <div class="pt-1 flex items-center gap-2">
                ${isPending ? `
                  <button onclick="approveScan(${scan.id})" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-1.5 px-3 rounded-lg text-xs flex items-center justify-center gap-1 transition-colors">
                    <i class="ph-bold ph-check"></i> Approve
                  </button>
                  <button onclick="rejectScan(${scan.id})" class="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 border border-slate-700 hover:border-rose-800 text-xs transition-colors" title="Reject">
                    <i class="ph-bold ph-trash"></i>
                  </button>
                ` : `
                  <button onclick="openInspectModal(${scan.id})" class="w-full bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium py-1.5 px-3 rounded-lg text-xs flex items-center justify-center gap-1 border border-slate-800 transition-colors">
                    <i class="ph-bold ph-eye"></i> View Details
                  </button>
                `}
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    async function approveScan(id) {
      try {
        const res = await fetch(`/api/v1/admin/scans/${id}/approve`, {method: 'POST'});
        if (res.ok) {
          fetchData();
        } else {
          const err = await res.json();
          alert("Approval error: " + (err.detail || "Could not approve"));
        }
      } catch (e) {
        alert("Failed to connect to gateway");
      }
    }

    async function rejectScan(id) {
      if (!confirm("Are you sure you want to reject and discard this scan?")) return;
      try {
        const res = await fetch(`/api/v1/admin/scans/${id}/reject`, {method: 'POST'});
        if (res.ok) {
          fetchData();
        } else {
          const err = await res.json();
          alert("Rejection error: " + (err.detail || "Could not reject"));
        }
      } catch (e) {
        alert("Failed to connect to gateway");
      }
    }

    function openInspectModal(id) {
      const scan = allScans.find(s => s.id === id);
      if (!scan) return;

      document.getElementById('modal-scan-id').innerText = '#' + scan.id + ' • ' + scan.scanned_at;
      document.getElementById('modal-product-name').innerText = scan.name;
      document.getElementById('modal-category').innerText = scan.category;
      document.getElementById('modal-barcode').innerText = scan.barcode;
      document.getElementById('modal-expiry').innerText = scan.expiry_date;
      document.getElementById('modal-conf').innerText = scan.ocr_confidence + '% Confidence';
      document.getElementById('modal-device').innerText = scan.pi_id;
      document.getElementById('modal-ocr-text').innerText = scan.ocr_text || '(No raw OCR dump stored)';

      const badge = document.getElementById('modal-status-badge');
      badge.innerText = scan.status;
      badge.className = 'px-2.5 py-0.5 rounded text-xs font-semibold tracking-wider uppercase ' +
        (scan.status === 'PENDING' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
         scan.status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
         'bg-rose-500/20 text-rose-400 border border-rose-500/30');

      const imgEl = document.getElementById('modal-image');
      const imgLink = document.getElementById('modal-image-link');
      if (scan.image_url) {
        imgEl.src = scan.image_url;
        imgEl.classList.remove('hidden');
        imgLink.href = scan.image_url;
        imgLink.classList.remove('hidden');
      } else {
        imgEl.classList.add('hidden');
        imgLink.classList.add('hidden');
      }

      const actionsEl = document.getElementById('modal-actions');
      if (scan.status === 'PENDING') {
        actionsEl.classList.remove('hidden');
        document.getElementById('modal-approve-btn').onclick = () => { approveScan(scan.id); closeInspectModal(); };
        document.getElementById('modal-reject-btn').onclick = () => { rejectScan(scan.id); closeInspectModal(); };
      } else {
        actionsEl.classList.add('hidden');
      }

      document.getElementById('inspect-modal').classList.remove('hidden');
    }

    function closeInspectModal() {
      document.getElementById('inspect-modal').classList.add('hidden');
    }

    function openUploadModal() {
      document.getElementById('upload-modal').classList.remove('hidden');
    }

    function closeUploadModal() {
      document.getElementById('upload-modal').classList.add('hidden');
    }

    async function handleUploadTest(e) {
      e.preventDefault();
      const fileInput = document.getElementById('test-image-input');
      const devInput = document.getElementById('test-device-id');
      const spinner = document.getElementById('upload-spinner');
      const submitBtn = document.getElementById('upload-submit-btn');

      if (!fileInput.files || fileInput.files.length === 0) return;

      const formData = new FormData();
      formData.append('image', fileInput.files[0]);
      formData.append('device_id', devInput.value);

      spinner.classList.remove('hidden');
      submitBtn.disabled = true;

      try {
        const res = await fetch('/api/v1/admin/upload-test', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (res.ok && data.success) {
          closeUploadModal();
          fileInput.value = '';
          fetchData();
        } else {
          alert('Upload failed: ' + (data.detail || 'Server error'));
        }
      } catch (err) {
        alert('Upload failed: Network error');
      } finally {
        spinner.classList.add('hidden');
        submitBtn.disabled = false;
      }
    }

    // Initialize
    window.addEventListener('DOMContentLoaded', checkAuth);
  </script>
</body>
</html>
"""
