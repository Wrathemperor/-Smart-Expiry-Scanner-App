# Current Changes - ShelfSense

## 1. The NoSQL Cloud Sync (The Academic Flex) & Document Inspector
- **Relational-to-Document Serialization Engine**: Created `NoSqlCloudSyncService.kt` to serialize Room SQLite inventory entities into hierarchical JSON/BSON document collections under path `users/default_user/inventory_documents` (Schema v2.0).
- **Interactive NoSQL Inspector UI**: Created `NoSqlInspectorDialog.kt` providing live inspection of serialized documents, statistics (total documents, payload size in bytes, path), 1-tap copy to clipboard, and manual cloud sync.
- **Two Critical Guardrails**:
  1. *Decoupled Cloud Dependencies*: Safe try/catch wrapping around Firestore so missing `google-services.json` never crashes the app on startup.
  2. *Strict 4-space JSON Pretty-Printing*: Formats JSON with `JSONArray(payload).toString(4)` for immediate lab report copy-pasting.
- **Settings Integration**: Added "NOSQL CLOUD SYNCHRONIZATION ☁️" card to `ProfileSettingsDialog.kt` with live sync status badges and direct inspect/sync triggers.
- **Versioned APK**: `apks/app-debug [nosql_cloud_sync_and_inspector].apk`.

## 2. Dual Queue System & Complete Data Persistence
- **Outbound Offline Queue (`scan_queue`)**: Captures photos and metadata locally when offline; automatically enqueues when network fails; sequential FIFO processing via "SYNC ALL".
- **Inbound AI Response Queue (`pending_scan_reviews`)**: Stores incoming AI responses chronologically by arrival time (`Item X of Y` review carousel); supports detailed editing and individual approval/rejection.
- **The "Zombie State" Recovery Guardrail**: Automatic reset of any scan stuck in `PROCESSING` back to `PENDING` on `ScanViewModel` startup.
- **Non-Destructive Room Migrations**: Version 5 database with `NOT NULL DEFAULT ''` and `NOT NULL DEFAULT 0` constraints ensuring existing inventory products, history, notifications, and custom locations are 100% preserved across APK overwrites.
- **Versioned APK**: `apks/app-debug [dual_queue_and_data_retention].apk`.

## 3. Inventory Card Delete Button Fix & Smooth Deletion Animation
- Decoupled touch targets in `InventoryProductCard` to eliminate event collisions.
- Added Neo-Brutalist `DeleteProductConfirmationDialog` and Compose `AnimatedVisibility` slide/shrink/fade deletion transition.
- **Versioned APK**: `apks/app-debug [inventory_card_delete_and_animation].apk`.

## 4. Product Category Catalog & Clean AI Description
- Constrained Gemini AI prompt to standard category catalog (`Dairy`, `Produce`, `Meat`, `Pantry`, `Beverages`, `Pharmacy`, `Prepared Meals`, `Bakery`, `Other`).
- Clean 1-line product summary and ingredients extraction.
- **Versioned APK**: `apks/app-debug [category_catalog_and_clean_ocr_description].apk`.

## 5. Per-Item Custom Notification Timings & Demo-Day Guardrail
- Room DB v4, `NotificationHelper.kt`, `ProductDetailDialog` chips & long-press trigger, `InventoryProductCard` badges.

## 6. Waste Prevention & Financial ROI Analytics Dashboard
- Rescued monetary value ($3.50/item), CO2e, H2O, native Compose Canvas donut chart.

## 7. History Page Filtering, Editing & Deletion
- Search & action filters, card hamburger menus, edit/delete dialogs.

## 8. Floating AI Recipe Generator
- Main screen FAB, fallback offline generator, 1.8s theatrical delay.
