# Current Changes - ShelfSense

## 1. 60fps Native Jetpack Compose Core Animations & Expired Notifications
- **Mechanical Tactility (`Modifier.bounceClick()`)**: Added custom spring scale (`1.0f -> 0.96f`) and shadow compression modifier in `BounceClick.kt` and applied directly to `NeoButton` and `NeoCard` in `NeoComponents.kt`.
- **Heartbeat Expiry Pulse**: Integrated infinite scaling pulse (`1.0f -> 1.07f`) on `NeoBadge` for `URGENT`, `CRITICAL`, and `EXPIRED` food items in `InventoryScreen.kt`.
- **Cyber Laser Scan Viewport & HUD**: Enhanced `WaitingForScanCard` in `ScanScreen.kt` with corner reticle brackets (`┌ ┐ └ ┘`), vertical animated glowing laser beam with `KineticYellow` gradient glow, and a `"NEURAL OCR SCANNING..."` HUD readout.
- **Automatic Expired Items Startup Notification**: Implemented `checkAndNotifyExpiredItems()` in `MainViewModel.kt` that queries inventory on app launch for expired items (`calculateRemainingDays < 0` or status `EXPIRED`), dispatches high-priority Android push alerts via `NotificationHelper.sendExpiredItemNotification()`, inserts unread notification records into the database, and prevents duplicate alerts via an in-memory session cache.
- **Versioned APK**: `apks/app-debug [core_animations_and_expired_alerts].apk`.

## 2. Demo Defense Mode (Zero-Network Safety Net) & Visual Safety Indicator
- **Zero-Network Guarantee**: Implemented `DemoModeRepository.kt` and `DemoModeData.kt` to bypass all outgoing OkHttp requests to Gemini Vision and Recipe AI during live capstone presentations.
- **Theatrical Delay**: Emits mock scans and recipes after a forced `delay(800)` for realistic, ultra-responsive demo interactions.
- **Visual Safety Indicator**: Displays a high-contrast Neo-Brutalist `⚡ DEMO DEFENSE MODE (ZERO-NETWORK)` banner on `ScanScreen.kt`.
- **Developer Settings Toggle**: Added "DEVELOPER & DEFENSE SETTINGS ⚡" in `ProfileSettingsDialog.kt`.
- **Versioned APK**: `apks/app-debug [demo_mode_defense_guardrail].apk`.

## 3. The NoSQL Cloud Sync (The Academic Flex) & Document Inspector
- **Relational-to-Document Serialization Engine**: Created `NoSqlCloudSyncService.kt` to serialize Room SQLite inventory entities into hierarchical JSON/BSON document collections under path `users/default_user/inventory_documents` (Schema v2.0).
- **Interactive NoSQL Inspector UI**: Created `NoSqlInspectorDialog.kt` providing live inspection of serialized documents, statistics (total documents, payload size in bytes, path), 1-tap copy to clipboard, and manual cloud sync.
- **Two Critical Guardrails**:
  1. *Decoupled Cloud Dependencies*: Safe try/catch wrapping around Firestore so missing `google-services.json` never crashes the app on startup.
  2. *Strict 4-space JSON Pretty-Printing*: Formats JSON with `JSONArray(payload).toString(4)` for immediate lab report copy-pasting.
- **Settings Integration**: Added "NOSQL CLOUD SYNCHRONIZATION ☁️" card to `ProfileSettingsDialog.kt` with live sync status badges and direct inspect/sync triggers.
- **Versioned APK**: `apks/app-debug [nosql_cloud_sync_and_inspector].apk`.

## 4. Dual Queue System & Complete Data Persistence
- **Outbound Offline Queue (`scan_queue`)**: Captures photos and metadata locally when offline; sequential FIFO processing via "SYNC ALL".
- **Inbound AI Response Queue (`pending_scan_reviews`)**: Stores incoming AI responses chronologically by arrival time (`Item X of Y` review carousel); supports detailed editing and individual approval/rejection.
- **The "Zombie State" Recovery Guardrail**: Automatic reset of any scan stuck in `PROCESSING` back to `PENDING` on `ScanViewModel` startup.
- **Non-Destructive Room Migrations**: Version 5 database with `NOT NULL DEFAULT ''` and `NOT NULL DEFAULT 0` constraints ensuring existing inventory products, history, notifications, and custom locations are 100% preserved across APK overwrites.
- **Versioned APK**: `apks/app-debug [dual_queue_and_data_retention].apk`.

## 5. Inventory Card Delete Button Fix & Smooth Deletion Animation
- Decoupled touch targets in `InventoryProductCard` to eliminate event collisions.
- Added Neo-Brutalist `DeleteProductConfirmationDialog` and Compose `AnimatedVisibility` slide/shrink/fade deletion transition.
- **Versioned APK**: `apks/app-debug [inventory_card_delete_and_animation].apk`.

## 6. Product Category Catalog & Clean AI Description
- Constrained Gemini AI prompt to standard category catalog (`Dairy`, `Produce`, `Meat`, `Pantry`, `Beverages`, `Pharmacy`, `Prepared Meals`, `Bakery`, `Other`).
- Clean 1-line product summary and ingredients extraction.
- **Versioned APK**: `apks/app-debug [category_catalog_and_clean_ocr_description].apk`.

## 7. Per-Item Custom Notification Timings & Demo-Day Guardrail
- Room DB v4, `NotificationHelper.kt`, `ProductDetailDialog` chips & long-press trigger, `InventoryProductCard` badges.

## 8. Waste Prevention & Financial ROI Analytics Dashboard
- Rescued monetary value ($3.50/item), CO2e, H2O, native Compose Canvas donut chart.

## 9. History Page Filtering, Editing & Deletion
- Search & action filters, card hamburger menus, edit/delete dialogs.

## 10. Floating AI Recipe Generator
- Main screen FAB, fallback offline generator, 1.8s theatrical delay.

## 11. Dynamic Real-Time Analytics Dashboard & Indian Rupee (₹) Financial ROI
- **Strict Indian Rupee (₹) Pricing**: Standardized all food valuations to ₹250 average value per item, completely removing dollar signs (`$`) and formatting all financial metrics in clean Indian currency style (e.g. `₹14,500`, `₹750` food loss, `₹1,250` at risk).
- **Interactive Multi-Timeframe Filtering**: Added interactive Neo-Brutalist filter chips (`ALL TIME`, `THIS MONTH`, `30 DAYS`, `7 DAYS`) that dynamically recalculate all cards, charts, and metrics in real time.
- **Background Threading (`.flowOn(Dispatchers.Default)`)**: All Room database flow combinations, calendar date groupings, category calculations, and financial arithmetic execute off the main thread to ensure 60fps stutter-free UI scrolling as inventory scales.
- **Dynamic Category Waste & Rescue Breakdown**: Real-time Room aggregations across 8+ product categories with dynamic rescue progress bars, item counts, and status badges (`100% ZERO-WASTE`, `HIGH RESCUE RATE`, `ATTENTION NEEDED`).
- **Interactive Activity Bar Chart**: Dynamic periodic consumption/loss activity chart with peak detection and tap-to-inspect bar breakdown.
- **Zero-Waste AI Insights**: Added dynamic intelligent cards highlighting items at risk in the next 48–72h, top rescued categories, and eco milestones.
- **Versioned APK**: `apks/app-debug [dynamic_analytics_and_rupee_pricing].apk`.

## 12. Multi-Model Automatic Fallback on HTTP 503 & API Overload (Gemini 3.8 Flash & 3.7 Flash)
- **2-Model Fallback Hierarchy**: Constrained candidate list strictly to `gemini-3.8-flash` (Primary) -> `gemini-3.7-flash` (Secondary).
- **Silent 503 & Transient Error Auto-Failover**: When an API request encounters HTTP 503 (Service Unavailable / Overloaded), 429 (Rate-limited), 5xx, or network timeouts, the system automatically logs a diagnostic warning and retries with the next model without displaying error popups.
- **Synchronized Full-Stack Coverage**: Applied across both Android client (`GeminiCloudService.kt` for OCR vision and recipe generation) and Python Gateway Server (`app/services/ocr_service.py`).
- **Last-Model Error Isolation**: Error messages or offline fallback states are triggered only when all candidate models have been exhausted.
- **Versioned APK**: `apks/app-debug [gemini_multi_model_503_fallback].apk`.

## 13. Dynamic Gemini API Key Configuration & Presentation Masking
- **Secure Password Masking**: API Key input in `ProfileSettingsDialog.kt` defaults to `PasswordVisualTransformation()` (`••••••••••••`) for secure demonstration in live presentations.
- **One-Touch Paste**: Integrated `LocalClipboardManager.current` with `Icons.Default.ContentPaste` for instant key updates.
- **Persistent DataStore & Header Injection**: Persisted in `GatewaySettingsRepository` and hot-injected into outgoing requests (`AuthInterceptor`) and runtime vision calls (`GeminiCloudService`).
- **Versioned APK**: `apks/app-debug [dynamic_gemini_api_key_settings].apk`.

## 14. Automatic Model Auto-Discovery Engine & Guardrails
- **Live Google API Model Auto-Discovery (`GET /v1beta/models`)**: Dynamically queries Google's model catalog to discover which models are enabled on the active API key with `supportedGenerationMethods.contains("generateContent")`.
- **Asynchronous Pre-fetching (Zero First-Scan Latency)**: Model discovery executes in the background on app launch in `MainViewModel` and upon saving settings, pre-warming the model cache before the user reaches the scan screen.
- **Smart Flash Priority Ranking Heuristic**: Automatically sorts candidates: Clean Flash models (`2.5-flash`, `2.0-flash`, `1.5-flash`, `3.8-flash`, etc.) > Flash-Lite > Pro > Deprioritizes thinking/preview/experimental models.
- **Strict Prefix Hygiene**: Strips `models/` prefix early to ensure clean endpoint construction (`models/$modelName:generateContent`).
- **Dynamic Pin Invalidation on 429/503 + 60s Cooldown**: When a pinned model encounters HTTP 429 (quota exhausted), 503 (overloaded), 404, or transient error, the pin is immediately cleared, the model is placed on a 60-second cooldown, and the engine rotates smoothly to the next candidate.
- **UI Hardening in ScanScreen**: Error messages in queued scan cards and offline alert cards enforce `Modifier.weight(1f)`, `maxLines = 2/3`, and `overflow = TextOverflow.Ellipsis`.
- **Versioned APK**: `apks/app-debug [automatic_model_discovery_and_guardrails].apk`.

## 15. Real-World Temporal Grounding & Expiry Year Normalizer
- **Dynamic Real-World Temporal Prompting**: Injected today's dynamic date (`todayIso`) and current year (`currentYear`) into the Gemini Vision system instruction across Android (`GeminiCloudService.kt`) and Python Gateway (`ocr_service.py`), eliminating 2025 hallucinations.
- **2-Digit & Missing Year Disambiguation**: Explicit prompt heuristics instruct Gemini to expand 2-digit years (`'26'` -> `'2026'`) and infer missing-year dates (`'18 OCT'`, `'25/11'`) relative to the current anchor date.
- **Smart Temporal Post-Processing Normalizer**: If an extracted expiry date has a past year (e.g. 2025) without explicit historical packaging context, `parseDateString` and Python normalizer automatically promote the year to the active calendar cycle (2026/2027), ensuring newly scanned food items are never erroneously marked as expired.
- **Versioned APK**: `apks/app-debug [scan_year_temporal_grounding_fix].apk`.




