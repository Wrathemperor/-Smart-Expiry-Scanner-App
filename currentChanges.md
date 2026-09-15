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
